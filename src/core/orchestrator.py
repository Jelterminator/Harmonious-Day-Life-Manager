# File: src/core/orchestrator.py
"""
Main orchestrator module for Harmonious Day.
Coordinates all components to generate daily schedules.

This module follows the Single Responsibility Principle by delegating
specific tasks to focused service classes.
"""

import datetime
from typing import Dict, Any, List

from src.core.config_manager import Config
from src.utils.logger import setup_logger
from src.auth.google_auth import get_google_services
from src.services.service_factory import ServiceFactory
from src.services.data_collector import DataCollector
from src.processors.task_processor import TaskProcessor
from src.processors.schedule_processor import ScheduleProcessor
from src.processors.habit_processor import filter_habits
from src.llm.prompt_builder import PromptBuilder
from src.llm.client import (
    get_groq_api_key, 
    load_system_prompt, 
    call_groq_llm,
    pretty_print_schedule
)
# New imports for type safety
from src.models.models import ScheduleEntry, CalendarEvent, Task, Habit, task_from_dict

logger = setup_logger(__name__)


class Orchestrator:
    """
    Main orchestrator for the AI Life Planner.
    
    Coordinates authentication, data gathering, processing,
    AI generation, and calendar writing.
    """
    
    def __init__(self):
        """
        Initialize the orchestrator.
        
        Loads configuration, authenticates with Google APIs,
        and sets up all necessary services.
        """
        logger.info("Initializing Orchestrator")
        
        # 1. Validate API Key
        self.api_key = get_groq_api_key()
        if not self.api_key:
            raise ValueError("Groq API Key not found. Set GROQ_API_KEY in .env")
        logger.debug("Groq API Key validated")
        
        # 2. Load Configuration
        self.rules = Config.load_phase_config()
        logger.debug(f"Loaded {len(self.rules.get('phases', []))} phases configuration")
        
        # 3. Authenticate with Google
        logger.info("Authenticating with Google APIs")
        raw_services = get_google_services()
        if not all(raw_services):
            raise ConnectionError(
                "Google authentication failed. Run 'python setup.py' first."
            )
        
        # 4. Create Service Layer
        self.calendar_service, self.sheets_service, self.tasks_service = \
            ServiceFactory.create_services(*raw_services)
        logger.debug("Service layer initialized")
        
        # 5. Create Helper Components
        self.data_collector = ServiceFactory.create_data_collector(
            self.calendar_service,
            self.sheets_service,
            self.tasks_service
        )
        self.task_processor = TaskProcessor()
        self.prompt_builder = PromptBuilder(self.rules)
        self.schedule_processor = ScheduleProcessor()
        
        # 6. Store metadata
        self.today_date_str = datetime.date.today().strftime("%Y-%m-%d")
        
        logger.info("Orchestrator initialized successfully")
    
    def run_daily_plan(self) -> bool:
        """
        Execute the full daily planning pipeline.
        
        Returns:
            True if successful, False otherwise
        
        Pipeline Steps:
            1. Clean up previous AI-generated events
            2. Gather data (calendar, tasks, habits)
            3. Process data (filter, prioritize)
            4. Build prompt for LLM
            5. Call AI to generate schedule
            6. Filter conflicts and validate
            7. Write to Google Calendar
        """
        logger.info("="*60)
        logger.info("Starting Daily Plan Generation")
        logger.info("="*60)
        
        try:            
            # Step 1: Gather Data
            logger.info("STEP 1: Gathering Data")
            data = self.data_collector.collect_all_data()
            
            # Assume DataCollector now returns typed model lists
            calendar_events: List[CalendarEvent] = data['calendar_events']
            raw_tasks = data['tasks']
            raw_habits = data['habits']
            
            # Step 2: Process Data
            logger.info("STEP 2: Processing Data")
            tasks: List[Task] = self.task_processor.process_tasks(raw_tasks)
            habits: List[Habit] = filter_habits(raw_habits)
            
            logger.info(
                f"Processed: {len(calendar_events)} calendar events, "
                f"{len(tasks)} prioritized tasks, {len(habits)} habits"
            )
            
            # Step 3: Build Prompt
            logger.info("STEP 3: Building Prompt")
            world_prompt = self.prompt_builder.build_world_prompt(
                calendar_events, tasks, habits
            )
            self.prompt_builder.save_prompt(world_prompt)
            
            system_prompt = load_system_prompt()
            if not system_prompt:
                raise FileNotFoundError("System prompt could not be loaded")
            
            # Step 4: Call AI
            logger.info("STEP 4: Calling AI")
            result = call_groq_llm(system_prompt, world_prompt)
            
            if result["status"] != "success":
                logger.error(f"AI generation failed: {result.get('message')}")
                return False
            
            # The LLM client now returns a List[ScheduleEntry] directly in 'output'
            generated_entries: List[ScheduleEntry] = result['output']
            logger.info(f"Schedule generated successfully with {len(generated_entries)} initial entries")
            
            # Step 5: Post-Process
            logger.info("STEP 5: Post-Processing Schedule")
            
            # Validate entries (valid_entries is List[ScheduleEntry])
            valid_entries, validation_errors = \
                self.schedule_processor.validate_schedule_entries(generated_entries)
            
            if validation_errors:
                logger.warning(f"Found {len(validation_errors)} validation errors")
                for error in validation_errors:
                    logger.warning(f"  - {error}")
            
            # Filter conflicts (final_entries is List[ScheduleEntry])
            final_entries: List[ScheduleEntry] = self.schedule_processor.filter_conflicting_entries(
                valid_entries, calendar_events
            )
            
            if not final_entries:
                logger.error("No valid entries after filtering")
                return False
            
            # Save to file (passing List[ScheduleEntry] directly)
            self.schedule_processor.save_schedule(final_entries)
            
            # Pretty print (passing List[ScheduleEntry] and List[CalendarEvent])
            pretty_print_schedule(final_entries, calendar_events)
            
            # Step 6: Write to Calendar
            logger.info("STEP 6: Writing to Calendar")
            # calendar_service.create_events will need to be updated to accept List[ScheduleEntry]
            created_count = self.calendar_service.create_events(
                final_entries,
                self.today_date_str
            )
            
            logger.info("="*60)
            logger.info(f"SUCCESS: Created {created_count} calendar events")
            logger.info("="*60)
            
            return True
            
        except Exception as e:
            logger.error(f"Fatal error in daily planning: {e}", exc_info=True)
            return False
    
    def _cleanup_previous_events(self) -> None:
        """
        Delete previously generated events (optional).
        Currently disabled to preserve user control.
        """
        logger.info("Cleaning up previous AI-generated events")
        deleted_count = self.calendar_service.delete_generated_events(
            self.today_date_str
        )
        logger.info(f"Deleted {deleted_count} previous events")
    
    @staticmethod
    def create_initial_token() -> bool:
        """
        Static method to run the one-time Google auth flow.
        Called by 'setup.py'.
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("Starting one-time Google authentication")
        
        # Assuming 'auth' is importable from the project root or relevant path
        from auth import create_initial_token
        success = create_initial_token()
        
        if success:
            logger.info("Authentication successful - token.json created")
        else:
            logger.error("Authentication failed")
        
        return success


class OrchestratorFactory:
    """Factory for creating Orchestrator instances with dependency injection."""
    
    @staticmethod
    def create() -> Orchestrator:
        """
        Create a fully initialized Orchestrator instance.
        
        Returns:
            Orchestrator instance ready to run
        
        Raises:
            ValueError: If configuration is invalid
            ConnectionError: If authentication fails
        """
        logger.info("Creating Orchestrator via factory")
        
        # Validate configuration first
        if not Config.validate():
            raise ValueError(
                "Configuration validation failed. "
                "Please run 'python setup.py' first."
            )
        
        return Orchestrator()