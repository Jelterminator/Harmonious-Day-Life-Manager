# File: src/services/calendar_service.py

import datetime
from typing import List, Optional
from googleapiclient.discovery import Resource

# Import necessary models and helper functions
from src.core.config_manager import Config
from src.utils.logger import setup_logger
from src.models.models import CalendarEvent, ScheduleEntry

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
    ) -> List[CalendarEvent]:
        """
        Fetch upcoming fixed calendar events and convert them to CalendarEvent objects.
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of CalendarEvent objects (excluding AI-generated ones)
        """
        logger.info(f"Fetching calendar events for next {days_ahead} days")
        
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            # Fetch events up until the start of the day after the window
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
            typed_events = []
            
            for event in events:
                extended_props = event.get('extendedProperties', {}).get('private', {})
                
                # Filter out AI-generated events using the sourceId
                if extended_props.get('sourceId') != self.generator_id:
                    try:
                        # Extract start/end, preferring dateTime (full timestamp) over date (all-day)
                        start_time_raw = event['start'].get('dateTime', event['start'].get('date'))
                        end_time_raw = event['end'].get('dateTime', event['end'].get('date'))
                        
                        start_dt = self._parse_gc_time(start_time_raw)
                        end_dt = self._parse_gc_time(end_time_raw)

                        if start_dt and end_dt:
                            typed_events.append(CalendarEvent(
                                event_id=event.get('id'),
                                summary=event.get('summary', 'No Title'),
                                start=start_dt,
                                end=end_dt,
                                is_generated=False
                            ))
                    except Exception as e:
                        logger.warning(f"Could not parse event data for {event.get('summary')}: {e}")

            logger.info(f"Found {len(typed_events)} fixed calendar events")
            return typed_events
            
        except Exception as e:
            logger.error(f"Error fetching calendar events: {e}", exc_info=True)
            return []

    def _parse_gc_time(self, time_str: str) -> Optional[datetime.datetime]:
        """Helper to safely parse Google Calendar date/dateTime strings."""
        if not time_str:
            return None
        try:
            # Full ISO format with time and timezone
            return datetime.datetime.fromisoformat(time_str)
        except ValueError:
            try:
                # Date-only format (for all-day events, treat as midnight UTC)
                date_obj = datetime.datetime.strptime(time_str, "%Y-%m-%d").date()
                return datetime.datetime.combine(date_obj, datetime.time.min).replace(
                    tzinfo=datetime.timezone.utc
                )
            except ValueError:
                return None
    
    def delete_generated_events(self, date_str: str) -> int:
        """
        Delete all events previously created by this application.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
        
        Returns:
            Number of events deleted
        """
        logger.info(f"Deleting generated events for window starting at {date_str}")
        
        try:
            # Ensure date_str is just the date part if it accidentally includes time
            if 'T' in date_str:
                date_str = date_str.split('T')[0]

            start_of_day = datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            # Search a 2-day window from the start of the specified day
            end_of_window = start_of_day + datetime.timedelta(days=2)
            time_min = start_of_day.isoformat()
            time_max = end_of_window.isoformat()
            
            # Use privateExtendedProperty filter for efficiency
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
        schedule_entries: List[ScheduleEntry], 
        date_str: str
    ) -> int:
        """
        Create calendar events from schedule entries.
        
        Args:
            schedule_entries: List of ScheduleEntry objects
            date_str: Date string for extended properties
        
        Returns:
            Number of events created
        """
        logger.info(f"Creating {len(schedule_entries)} calendar events")
        
        if not schedule_entries:
            return 0

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
                # Use the start_time and end_time attributes directly
                start_dt = entry.start_time
                end_dt = entry.end_time
                
                # Map phase string to config color ID if available
                color_id = '1' # Default lavender
                if entry.phase:
                    # Entry phase is an Enum, get its value for lookup
                    color_id = Config.PHASE_COLORS.get(entry.phase.value, '1')

                event = {
                    'summary': entry.title,
                    'description': f"Phase: {entry.phase.value if entry.phase else 'N/A'}",
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': Config.TARGET_TIMEZONE, 
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': Config.TARGET_TIMEZONE,
                    },
                    'colorId': color_id,
                    'extendedProperties': {
                        'private': {
                            'harmoniousDayGenerated': date_str,
                            'sourceId': self.generator_id,
                            'isFixed': 'false'
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
                    f"Error preparing event {entry.title}: {e}",
                    exc_info=True
                )
        
        # Check if the batch has requests before executing
        if hasattr(batch, "_requests") and batch._requests:
            try:
                batch.execute()
            except Exception as e:
                logger.error(f"Batch execution failed: {e}", exc_info=True)
        
        logger.info(f"Successfully created {created_count} events")
        return created_count