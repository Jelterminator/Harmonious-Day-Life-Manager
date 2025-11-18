# File: src/services/calendar_service.py

import datetime
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import Resource

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GoogleCalendarService:
    """Handles all Google Calendar operations."""
    
    def __init__(self, calendar_service: Resource):
        """
        Initialize calendar service.
        
        Args:
            calendar_service: Authenticated Google Calendar API resource
        """
        self.service = calendar_service
        self.generator_id = Config.GENERATOR_ID
    
    def get_upcoming_events(
        self, 
        days_ahead: int = 2
    ) -> List[Dict[str, str]]:
        """
        Fetch upcoming calendar events.
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of event dictionaries with summary, start, and end times
        """
        logger.info(f"Fetching calendar events for next {days_ahead} days")
        
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            end_time = (
                datetime.datetime.combine(
                    datetime.date.today() + datetime.timedelta(days=days_ahead),
                    datetime.time.min
                ).replace(tzinfo=datetime.timezone.utc)
            )
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=now.isoformat(),
                timeMax=end_time.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Filter out AI-generated events
            formatted_events = []
            for event in events:
                extended_props = event.get('extendedProperties', {}).get('private', {})
                if extended_props.get('sourceId') != self.generator_id:
                    formatted_events.append({
                        "summary": event['summary'],
                        "start": event['start'].get('dateTime', event['start'].get('date')),
                        "end": event['end'].get('dateTime', event['end'].get('date'))
                    })
            
            logger.info(f"Found {len(formatted_events)} fixed calendar events")
            return formatted_events
            
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}", exc_info=True)
            return []
    
    def delete_generated_events(self, date_str: str) -> int:
        """
        Delete all events previously created by this application.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        
        Returns:
            Number of events deleted
        """
        logger.info(f"Deleting generated events for {date_str}")
        
        try:
            start_of_day = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            end_of_window = start_of_day + datetime.timedelta(days=2)
            time_min = start_of_day.isoformat() + 'Z'
            time_max = end_of_window.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                privateExtendedProperty=f'sourceId={self.generator_id}'
            ).execute()
            
            events_to_delete = events_result.get('items', [])
            if not events_to_delete:
                logger.info("No previous AI-generated events found")
                return 0
            
            logger.info(f"Deleting {len(events_to_delete)} previous events")
            
            batch = self.service.new_batch_http_request()
            deleted_count = 0
            
            def callback(request_id, response, exception):
                nonlocal deleted_count
                if exception is None:
                    deleted_count += 1
                else:
                    logger.warning(f"Failed to delete event {request_id}: {exception}")
            
            for event in events_to_delete:
                batch.add(
                    self.service.events().delete(
                        calendarId='primary',
                        eventId=event['id']
                    ),
                    callback=callback
                )
            
            batch.execute()
            logger.info(f"Successfully deleted {deleted_count} events")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting events: {e}", exc_info=True)
            return 0
    
    def create_events(
        self, 
        schedule_entries: List[Dict[str, Any]],
        date_str: str
    ) -> int:
        """
        Create calendar events from schedule entries.
        
        Args:
            schedule_entries: List of schedule entry dictionaries
            date_str: Date string for extended properties
        
        Returns:
            Number of events created
        """
        logger.info(f"Creating {len(schedule_entries)} calendar events")
        
        batch = self.service.new_batch_http_request()
        created_count = 0
        
        def callback(request_id, response, exception):
            nonlocal created_count
            if exception is None:
                created_count += 1
            else:
                logger.error(f"Failed to create event {request_id}: {exception}")
        
        for entry in schedule_entries:
            try:
                # Use pre-parsed datetime objects if available
                start_dt = entry.get('_parsed_start')
                end_dt = entry.get('_parsed_end')
                
                if not (start_dt and end_dt):
                    logger.warning(f"Skipping entry without parsed times: {entry.get('title')}")
                    continue
                
                event = {
                    'summary': entry.get('title', 'No title'),
                    'description': f"Phase: {entry.get('phase', 'N/A')}",
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': Config.TARGET_TIMEZONE,
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': Config.TARGET_TIMEZONE,
                    },
                    'colorId': Config.PHASE_COLORS.get(
                        entry.get('phase', '').upper(), 
                        '1'
                    ),
                    'extendedProperties': {
                        'private': {
                            'harmoniousDayGenerated': date_str,
                            'sourceId': self.generator_id
                        }
                    },
                }
                
                batch.add(
                    self.service.events().insert(
                        calendarId='primary',
                        body=event
                    ),
                    callback=callback
                )
                
            except Exception as e:
                logger.error(
                    f"Error preparing event {entry.get('title')}: {e}",
                    exc_info=True
                )
        
        if getattr(batch, "_requests", None):
            try:
                batch.execute()
            except Exception as e:
                logger.error(f"Batch execution failed: {e}", exc_info=True)
        
        logger.info(f"Successfully created {created_count} events")
        return created_count
