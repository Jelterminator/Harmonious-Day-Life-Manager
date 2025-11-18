# File: src/services/sheets_service.py

from typing import List, Dict, Any
from googleapiclient.discovery import Resource

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class GoogleSheetsService:
    """Handles all Google Sheets operations."""
    
    def __init__(self, sheets_service: Resource):
        """
        Initialize sheets service.
        
        Args:
            sheets_service: Authenticated Google Sheets API resource
        """
        self.service = sheets_service
    
    def get_habits(
        self, 
        sheet_id: str = Config.SHEET_ID,
        range_name: str = Config.HABIT_RANGE
    ) -> List[Dict[str, Any]]:
        """
        Fetch habits from Google Sheets.
        
        NOTE: This method returns raw data (List[Dict]) and relies on DataCollector
        to convert it to the typed Habit model.
        
        Args:
            sheet_id: Spreadsheet ID
            range_name: Range to fetch (e.g., "Habits!A:H")
        
        Returns:
            List of habit dictionaries (raw sheet data)
        """
        logger.info(f"Fetching habits from Google Sheets: {sheet_id} - {range_name}")
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values or len(values) < 2:
                logger.warning("No header or data rows found in habit sheet")
                return []
            
            headers = values[0]
            habits_data = []
            
            for row in values[1:]:
                # Ensure the row has enough elements to match the header, filling with empty strings
                row_padded = row + [''] * (len(headers) - len(row))
                # Create a dictionary mapping header names (keys) to cell values
                habit = {headers[j]: row_padded[j] for j in range(len(headers))}
                habits_data.append(habit)
            
            logger.info(f"Fetched {len(habits_data)} raw habit rows")
            return habits_data
            
        except Exception as e:
            logger.error(f"Error fetching habits from sheets: {e}", exc_info=True)
            return []