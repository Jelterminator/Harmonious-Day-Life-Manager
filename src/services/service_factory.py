# File: src/services/service_factory.py

from typing import Tuple
from googleapiclient.discovery import Resource

from src.core.config_manager import Config
from src.utils.logger import setup_logger
from src.services.calendar_service import GoogleCalendarService
from src.services.sheets_service import GoogleSheetsService
from src.services.tasks_service import GoogleTasksService
from src.services.data_collector import DataCollector

logger = setup_logger(__name__)

class ServiceFactory:
    """Factory for creating service instances."""
    
    @staticmethod
    def create_services(
        calendar_service: Resource,
        sheets_service: Resource,
        tasks_service: Resource
    ) -> Tuple[GoogleCalendarService, GoogleSheetsService, GoogleTasksService]:
        """
        Create service wrapper instances.
        
        Args:
            calendar_service: Authenticated calendar API resource
            sheets_service: Authenticated sheets API resource
            tasks_service: Authenticated tasks API resource
        
        Returns:
            Tuple of (calendar_service, sheets_service, tasks_service)
        """
        return (
            GoogleCalendarService(calendar_service),
            GoogleSheetsService(sheets_service),
            GoogleTasksService(tasks_service)
        )
    
    @staticmethod
    def create_data_collector(
        calendar_service: GoogleCalendarService,
        sheets_service: GoogleSheetsService,
        tasks_service: GoogleTasksService
    ) -> DataCollector:
        """
        Create data collector instance.
        
        Args:
            calendar_service: Calendar service instance
            sheets_service: Sheets service instance
            tasks_service: Tasks service instance
        
        Returns:
            DataCollector instance
        """
        return DataCollector(calendar_service, sheets_service, tasks_service)