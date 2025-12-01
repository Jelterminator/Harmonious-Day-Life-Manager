# File: src/processors/schedule_processor.py
"""
Schedule processing module.
Handles datetime parsing, conflict detection, and schedule validation using typed models.
"""

import datetime
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import pytz

from src.core.config_manager import Config
from src.utils.logger import setup_logger
# Import the typed models and factory function
from src.models import ScheduleEntry, CalendarEvent, Phase, schedule_entry_from_dict, parse_iso_datetime

logger = setup_logger(__name__)


class ScheduleProcessor:
    """Processes and validates generated schedules."""
    
    def __init__(self, timezone: str = Config.TARGET_TIMEZONE):
        """
        Initialize schedule processor.
        
        Args:
            timezone: Timezone name (e.g., 'Europe/Amsterdam')
        """
        self.timezone = pytz.timezone(timezone)
        self.logger = setup_logger(__name__)

    # NOTE: The public parse_iso_to_local is removed. Datetime parsing is now handled
    # by schedule_entry_from_dict or the CalendarEvent objects themselves.
    # The conflict filter will now use the datetime objects inside the models.
    
    def filter_conflicting_entries(self,
        schedule_entries: List[ScheduleEntry],
        existing_events: List[CalendarEvent]) -> List[ScheduleEntry]:
        """
        Remove generated schedule entries that overlap with fixed calendar events.
        Maximizes use of existing model functionality.
        """
        self.logger.info("Filtering generated schedule against fixed events")
        
        # Pre-normalize all fixed events once
        normalized_fixed_events = []
        for event in existing_events:
            try:
                start_dt = parse_iso_datetime(event.start.isoformat())
                end_dt = parse_iso_datetime(event.end.isoformat())
                normalized_fixed_events.append({
                    'summary': event.summary,
                    'start': start_dt,
                    'end': end_dt
                })
            except Exception as e:
                self.logger.warning(f"Could not normalize event '{event.summary}': {e}")
        
        filtered: List[ScheduleEntry] = []
        conflicts_found = []
        
        for entry in schedule_entries:
            if entry.end_time <= entry.start_time:
                self.logger.warning(f"Skipping entry with invalid duration: {entry.title}")
                continue
    
            has_conflict = False
            conflicting_event_summary = None
            
            # Normalize entry times once
            entry_start = parse_iso_datetime(entry.start_time.isoformat())
            entry_end = parse_iso_datetime(entry.end_time.isoformat())
            
            # Check against all normalized fixed events
            for fixed_event in normalized_fixed_events:
                if (fixed_event['start'] < entry_end and 
                    fixed_event['end'] > entry_start):
                    has_conflict = True
                    conflicting_event_summary = fixed_event['summary']
                    break
            
            if has_conflict:
                conflicts_found.append({
                    'title': entry.title,
                    'time': f"{entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')}",
                    'blocked_by': conflicting_event_summary
                })
            else:
                filtered.append(entry)
                
        # Logging remains the same...
        return filtered
    
    # --- Renamed and adapted to handle typed ScheduleEntry objects ---
    
    def save_schedule(
        self, 
        schedule_entries: List[ScheduleEntry],  # Accepts typed ScheduleEntry objects
        filepath: Path = Config.SCHEDULE_OUTPUT_FILE
    ) -> bool:
        """
        Save schedule JSON to file.
        
        Args:
            schedule_entries: List of ScheduleEntry objects to save
            filepath: Output file path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Prepare data for JSON serialization, converting ScheduleEntry objects to dicts
            data_to_save = {
                "schedule_entries": [
                    entry.to_dict() if hasattr(entry, 'to_dict') else entry.__dict__
                    for entry in schedule_entries
                ],
                "generated_at": datetime.datetime.now().isoformat()
            }
            
            with open(filepath, 'w', encoding="utf-8") as f:
                # Need a custom encoder for datetime and Enum objects if they are not converted to dicts/strings
                # Assuming ScheduleEntry has a .to_dict() or a custom JSONEncoder is used elsewhere
                json.dump(data_to_save, f, indent=2, default=str, ensure_ascii=False)
                
            self.logger.info(f"Schedule saved to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Could not save schedule: {e}", exc_info=True)
            return False
            
    # --- The date parsing logic is now integrated into the ScheduleEntry factory, 
    #     but we will keep a simplified validation helper for the raw input phase. ---

    def validate_schedule_entries(
        self, 
        raw_entries: List[ScheduleEntry] # <-- Corrected type hint to expect typed objects
    ) -> Tuple[List[ScheduleEntry], List[str]]:
        """
        Validate raw schedule entries (now expected to be typed ScheduleEntry objects)
        and return valid ones, along with a list of error messages.
        
        We now rely on attribute access and assume upstream components are creating 
        these objects from the LLM output.
        """
        valid_entries: List[ScheduleEntry] = []
        errors: List[str] = []
        
        self.logger.info(f"Validating {len(raw_entries)} raw schedule entries.")
        
        for i, entry in enumerate(raw_entries):
            # Access attributes directly, assuming `entry` is a ScheduleEntry or similar object
            # Use getattr for robustness to handle potentially malformed objects missing attributes
            title = getattr(entry, 'title', f'Entry {i+1}')
            
            try:
                # We no longer call schedule_entry_from_dict(raw_entry) as the input is 
                # expected to be a typed object, not a dictionary.
                
                # Check 1: Explicitly check for valid datetime objects
                if not isinstance(entry.start_time, datetime.datetime) or not isinstance(entry.end_time, datetime.datetime):
                    raise TypeError("Start or end time is not a valid datetime object.")
                
                # Check 2: Time span validation (now relying on the logic inside ScheduleEntry.__post_init__).
                # If the validation in __post_init__ was skipped during creation, we can manually 
                # check the core business logic conflict here:
                
                if entry.end_time <= entry.start_time and not (entry.end_time.date() > entry.start_time.date()):
                    raise ValueError("End time must be strictly after start time on the same day.")

                valid_entries.append(entry)
                
            except (AttributeError, ValueError, TypeError) as e:
                # Catch errors related to missing attributes or failed validation
                error_msg = f"Skipping invalid entry '{title}': {e}"
                errors.append(error_msg)
                self.logger.warning(error_msg)
        
        self.logger.info(
            f"Validation complete: {len(valid_entries)} valid entries "
            f"({len(errors)} errors)"
        )
        return valid_entries, errors