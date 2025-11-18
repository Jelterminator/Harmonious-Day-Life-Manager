# File: clear.py
"""
Script to clear all AI-generated events from the Google Calendar 
for today and tomorrow, by leveraging the GoogleCalendarService.
It uses the unique GENERATOR_ID to identify events created by the application.
"""

import datetime
import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Core system imports
    from src.core.config_manager import Config
    from src.auth.google_auth import get_google_services
    from src.services.calendar_service import GoogleCalendarService
    # Using setup_logger for consistency with scripts/plan.py and src/services/calendar_service.py
    from src.utils.logger import setup_logger 
except ImportError as e:
    # Log and exit cleanly if essential modules are missing
    print(f"FATAL ERROR: Could not import core modules. Please check your package structure. Error: {e}")
    sys.exit(1)


# Initialize Logger
logger = setup_logger(__name__)

def main() -> int:
    """
    Main entry point to clear today's and tomorrow's AI-generated schedules
    using the GoogleCalendarService.
    
    Returns:
        Exit code (0 for success, 1 for failure).
    """
    start_time = datetime.datetime.now()
    
    logger.info("="*60)
    logger.info("Starting Harmonious Day Schedule Cleanup")
    logger.info("="*60)

    try:
        # 1. Get Google API Resource
        logger.info("Initializing Google Calendar Service...")
        google_service_resource = get_google_services()
        if not google_service_resource:
            logger.critical("Could not initialize Google Calendar service resource. Exiting.")
            return 1
        
        # 2. Instantiate the Calendar Service
        calendar_service = GoogleCalendarService(google_service_resource[0])

        # 3. Determine start date for deletion window (Today)
        # The service's delete_generated_events method clears a 2-day window 
        # starting from the provided date. This single call covers Today and Tomorrow.
        today = datetime.date.today()
        today_str = today.strftime("%Y-%m-%d")
        
        logger.info(f"Clearing AI-generated events in the 2-day window starting from: {today_str}")

        # 4. Execute Deletion
        total_deleted = calendar_service.delete_generated_events(today_str)
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        
        logger.info("="*60)
        logger.info(f"Cleanup completed successfully in {elapsed:.2f} seconds.")
        logger.info(f"Total events deleted: {total_deleted}")
        logger.info("="*60)
        
        return 0
            
    except Exception as e:
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        logger.error("="*60)
        logger.error(f"Cleanup failed after {elapsed:.2f} seconds due to an unexpected error.", exc_info=True)
        logger.error(f"Error: {e}")
        logger.error("="*60)
        return 1

if __name__ == '__main__':
    sys.exit(main())