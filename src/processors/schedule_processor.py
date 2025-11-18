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
from src.models.models import ScheduleEntry, CalendarEvent, Phase, schedule_entry_from_dict 

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
        """
        self.logger.info("Filtering generated schedule against fixed events")
        
        filtered: List[ScheduleEntry] = []
        conflicts_found = []
        
        for entry in schedule_entries:
            if entry.end_time <= entry.start_time:
                self.logger.warning(f"Skipping entry with invalid duration: {entry.title}")
                continue
    
            has_conflict = False
            conflicting_event_summary = None
            
            # Create a temporary CalendarEvent from the ScheduleEntry to use the overlaps_with method
            temp_entry_event = CalendarEvent(
                summary=entry.title,
                start=entry.start_time,
                end=entry.end_time
            )
            
            for fixed_event in existing_events:
                try:
                    if fixed_event.overlaps_with(temp_entry_event):
                        has_conflict = True
                        conflicting_event_summary = fixed_event.summary
                        break
                except TypeError as e:
                    # If there's still a timezone comparison issue, log and skip
                    self.logger.warning(f"Timezone comparison error for {entry.title}: {e}")
                    continue
            
            if has_conflict:
                conflicts_found.append({
                    'title': entry.title,
                    'time': f"{entry.start_time.strftime('%H:%M')}-{entry.end_time.strftime('%H:%M')}",
                    'blocked_by': conflicting_event_summary
                })
                self.logger.debug(
                    f"Skipping '{entry.title}' "
                    f"({entry.start_time.time()}-{entry.end_time.time()}) - "
                    f"conflicts with '{conflicting_event_summary}'"
                )
            else:
                filtered.append(entry)
                
        # Log conflict summary (same as before)
        if conflicts_found:
            self.logger.warning(f"Filtered out {len(conflicts_found)} conflicting entries:")
            for conflict in conflicts_found:
                self.logger.warning(
                    f"  - {conflict['title']} ({conflict['time']}) "
                    f"blocked by {conflict['blocked_by']}"
                )
            
        self.logger.info(
            f"Final schedule: {len(filtered)} non-conflicting entries "
            f"(removed {len(conflicts_found)} conflicts)"
        )
        
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