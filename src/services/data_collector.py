# File: src/services/data_collector.py

import datetime
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import Resource

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class DataCollector:
    """Collects all data needed for schedule generation."""
    
    def __init__(
        self,
        calendar_service: GoogleCalendarService,
        sheets_service: GoogleSheetsService,
        tasks_service: GoogleTasksService
    ):
        """
        Initialize data collector with services.
        
        Args:
            calendar_service: Calendar service instance
            sheets_service: Sheets service instance
            tasks_service: Tasks service instance
        """
        self.calendar = calendar_service
        self.sheets = sheets_service
        self.tasks = tasks_service
        self.logger = setup_logger(__name__)
    
    def collect_all_data(self) -> Dict[str, Any]:
        """
        Collect all data needed for scheduling.
        
        Returns:
            Dictionary with keys: calendar_events, raw_tasks, raw_habits
        """
        self.logger.info("Collecting all data for schedule generation")
        
        calendar_events = self.calendar.get_upcoming_events(days_ahead=2)
        raw_tasks = self.tasks.get_all_tasks()
        raw_habits = self.sheets.get_habits()
        
        self.logger.info(
            f"Data collected: {len(calendar_events)} events, "
            f"{len(raw_tasks)} tasks, {len(raw_habits)} habits"
        )
        
        return {
            'calendar_events': calendar_events,
            'raw_tasks': raw_tasks,
            'raw_habits': raw_habits
        }