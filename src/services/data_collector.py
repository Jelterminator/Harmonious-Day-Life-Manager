# File: src/services/data_collector.py

import datetime
from typing import List, Dict, Any, Optional
from src.models.models import CalendarEvent, Task, Habit, task_from_dict, habit_from_dict 
from src.core.config_manager import Config
from src.utils.logger import setup_logger

# Import the service classes
from src.services.calendar_service import GoogleCalendarService
from src.services.sheets_service import GoogleSheetsService
from src.services.tasks_service import GoogleTasksService 


logger = setup_logger(__name__)


# Define a typed dict for the collector's output for clarity
class CollectedData(Dict):
    calendar_events: List[CalendarEvent]
    tasks: List[Task]
    habits: List[Habit]


class DataCollector:
    """Collects all data needed for schedule generation and converts it to typed models."""
    
    def __init__(
        self,
        calendar_service: GoogleCalendarService,
        sheets_service: GoogleSheetsService,
        tasks_service: GoogleTasksService
    ):
        """
        Initialize data collector with services.
        
        Args:
            calendar_service: Calendar service instance (returns CalendarEvent objects)
            sheets_service: Sheets service instance (returns raw dicts)
            tasks_service: Tasks service instance (returns raw dicts)
        """
        self.calendar = calendar_service
        self.sheets = sheets_service
        self.tasks = tasks_service
        self.logger = setup_logger(__name__)
    
    def collect_all_data(self) -> CollectedData:
        """
        Collect all data needed for scheduling and convert raw inputs into models.
        
        Returns:
            Dictionary containing fully typed lists of events, tasks, and habits.
        """
        self.logger.info("Starting data collection and conversion for schedule generation")
        
        # 1. Collect Calendar Events (The calendar service now returns typed CalendarEvent objects)
        calendar_events: List[CalendarEvent] = self.calendar.get_upcoming_events(days_ahead=2)
        
        # 2. Collect and Convert Tasks (Raw dicts must be converted)
        raw_tasks_list = self.tasks.get_all_tasks() # Assumed to return List[Dict]
        tasks: List[Task] = []
        for raw_task in raw_tasks_list:
            try:
                tasks.append(task_from_dict(raw_task))
            except Exception as e:
                self.logger.error(
                    f"Failed to convert task {raw_task.get('title', 'Unknown')}: {e}"
                )
                
        # 3. Collect and Convert Habits (Raw dicts must be converted)
        raw_habits_list = self.sheets.get_habits() # Assumed to return List[Dict]
        habits: List[Habit] = []
        for raw_habit in raw_habits_list:
            try:
                habits.append(habit_from_dict(raw_habit))
            except Exception as e:
                self.logger.error(
                    f"Failed to convert habit {raw_habit.get('title', 'Unknown')}: {e}"
                )
        
        self.logger.info(
            f"Collection successful: {len(calendar_events)} events, "
            f"{len(tasks)} valid tasks, {len(habits)} valid habits"
        )
        
        return {
            'calendar_events': calendar_events,
            'tasks': tasks,
            'habits': habits
        }