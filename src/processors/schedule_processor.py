# File: src/processors/schedule_processor.py
"""
Schedule processing module.
Handles datetime parsing, conflict detection, and schedule validation.
"""

import datetime
import json
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import pytz

from src.core.config_manager import Config
from src.utils.logger import setup_logger

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
    
    def parse_iso_to_local(
        self, 
        s: str, 
        date_hint: Optional[datetime.date] = None
    ) -> datetime.datetime:
        """
        Parse various timestamp formats to local timezone datetime.
        
        Args:
            s: Timestamp string in various formats
            date_hint: Date to use for time-only strings
        
        Returns:
            Timezone-aware datetime object
        
        Examples:
            >>> processor = ScheduleProcessor()
            >>> dt = processor.parse_iso_to_local("08:00", date_hint=date(2025,11,18))
            >>> dt.hour
            8
        """
        # Only time provided (e.g., "08:00")
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', s):
            if date_hint is None:
                date_hint = datetime.date.today()
            parts = list(map(int, s.split(':')))
            hour = parts[0]
            minute = parts[1]
            second = parts[2] if len(parts) > 2 else 0
            dt = datetime.datetime(
                date_hint.year, date_hint.month, date_hint.day,
                hour, minute, second
            )
            dt = self.timezone.localize(dt)
            return dt
        
        # Full ISO string
        dt = datetime.datetime.fromisoformat(s.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = self.timezone.localize(dt)
        else:
            dt = dt.astimezone(self.timezone)
        return dt
    
    def filter_conflicting_entries(
        self,
        schedule_entries: List[Dict[str, Any]],
        existing_events: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Remove entries that overlap with fixed calendar events.
        
        Args:
            schedule_entries: Generated schedule entries
            existing_events: Fixed calendar events
        
        Returns:
            Filtered list of non-conflicting entries
        """
        self.logger.info("Filtering generated schedule against fixed events")
        
        filtered = []
        conflicts_found = []
        
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        # Pre-process fixed events
        parsed_fixed_events = []
        for evt in existing_events:
            try:
                s_raw = evt.get('start', '')
                e_raw = evt.get('end', '')
                s = self.parse_iso_to_local(s_raw)
                e = self.parse_iso_to_local(e_raw)
                if s and e:
                    parsed_fixed_events.append({
                        'summary': evt.get('summary', 'Unknown'),
                        'start': s,
                        'end': e
                    })
            except Exception as ex:
                self.logger.warning(
                    f"Skipping fixed event '{evt.get('summary', 'Unknown')}' "
                    f"due to parse error: {ex}"
                )
        
        # Check each entry for conflicts
        for entry in schedule_entries:
            try:
                date_indicator = entry.get('date', 'today').lower()
                entry_date = tomorrow if date_indicator == 'tomorrow' else today
                
                # Parse entry times
                entry_start = self.parse_iso_to_local(
                    entry['start_time'], 
                    date_hint=entry_date
                )
                entry_end = self.parse_iso_to_local(
                    entry['end_time'], 
                    date_hint=entry_date
                )
                
                # Handle overnight events
                if entry_end <= entry_start:
                    entry_end = entry_end + datetime.timedelta(days=1)
                
                # Check for overlaps
                has_conflict = False
                conflicting_event = None
                
                for evt in parsed_fixed_events:
                    # Overlap: evt.start < entry_end AND evt.end > entry_start
                    if evt['start'] < entry_end and evt['end'] > entry_start:
                        has_conflict = True
                        conflicting_event = evt
                        break
                
                if has_conflict:
                    conflicts_found.append({
                        'title': entry.get('title', 'Unknown'),
                        'time': f"{entry['start_time']}-{entry['end_time']}",
                        'blocked_by': conflicting_event['summary']
                    })
                    self.logger.debug(
                        f"Skipping '{entry.get('title', 'Unknown')}' "
                        f"({entry['start_time']}-{entry['end_time']}) - "
                        f"conflicts with '{conflicting_event['summary']}'"
                    )
                else:
                    # Attach parsed datetimes for later use
                    entry['_parsed_start'] = entry_start
                    entry['_parsed_end'] = entry_end
                    filtered.append(entry)
            
            except (ValueError, KeyError, TypeError) as e:
                self.logger.warning(
                    f"Skipping malformed entry '{entry.get('title', 'Unknown')}': {e}"
                )
        
        # Log conflict summary
        if conflicts_found:
            self.logger.warning(f"Filtered out {len(conflicts_found)} conflicting entries:")
            for conflict in conflicts_found:
                self.logger.warning(
                    f"  - {conflict['title']} ({conflict['time']}) "
                    f"blocked by {conflict['blocked_by']}"
                )
            self.logger.info(
                "TIP: These tasks should be rescheduled. "
                "Consider running the planner again after your calendar events."
            )
        
        self.logger.info(
            f"Final schedule: {len(filtered)} non-conflicting entries "
            f"(removed {len(conflicts_found)} conflicts)"
        )
        
        return filtered
    
    def save_schedule(
        self, 
        schedule_data: Dict[str, Any], 
        filepath: Path = Config.SCHEDULE_OUTPUT_FILE
    ) -> bool:
        """
        Save schedule JSON to file.
        
        Args:
            schedule_data: Schedule dictionary to save
            filepath: Output file path
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding="utf-8") as f:
                json.dump(schedule_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Schedule saved to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Could not save schedule: {e}", exc_info=True)
            return False
    
    @staticmethod   
    def _parse_date_to_iso(date_str: str) -> str | None:
        """Try to parse a date string into ISO YYYY-MM-DD. Return None if cannot parse."""
        s = date_str.strip()
        # today / tomorrow
        if s.lower() == "today":
            return datetime.date.today().isoformat()
        if s.lower() == "tomorrow":
            return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    
        # Try isoformat first (handles YYYY-MM-DD reliably)
        try:
            d = datetime.date.fromisoformat(s)
            return d.isoformat()
        except Exception:
            pass
    
        # Try other known patterns
        for fmt, pattern in Config.DATE_PATTERNS:
            if pattern.match(s):
                try:
                    d = datetime.datetime.strptime(s, fmt).date()
                    return d.isoformat()
                except Exception:
                    continue
    
        # As a last attempt, be forgiving: try parsing common separators
        try:
            s2 = re.sub(r"[^\d]", "-", s)  # convert separators to '-'
            parts = s2.split("-")
            if len(parts) == 3:
                # attempt day-first if it looks like dd-mm-yyyy
                if len(parts[0]) == 2 and len(parts[2]) == 4:
                    d = datetime.datetime.strptime(s2, "%d-%m-%Y").date()
                else:
                    d = datetime.datetime.strptime(s2, "%Y-%m-%d").date()
                return d.isoformat()
        except Exception:
            pass
    
        return None
    
    
    def validate_schedule_entries(self, entries: List[Dict[str, Any]]
                                  ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Validate schedule entries and return valid ones with error messages.
    
        - Accepts 'today', 'tomorrow' and concrete dates.
        - Normalizes `entry['date']` to ISO YYYY-MM-DD on success.
        """
        valid_entries: List[Dict[str, Any]] = []
        errors: List[str] = []
    
        required_fields = ['title', 'start_time', 'end_time', 'phase', 'date']
        valid_phases = ['WOOD', 'FIRE', 'EARTH', 'METAL', 'WATER']
    
        today = datetime.date.today()
    
        for i, entry in enumerate(entries):
            # Check required fields
            missing_fields = [f for f in required_fields if f not in entry]
            if missing_fields:
                error = (
                    f"Entry {i+1} ('{entry.get('title', 'Unknown')}') "
                    f"missing fields: {', '.join(missing_fields)}"
                )
                errors.append(error)
                self.logger.warning(error)
                continue
    
            # Validate phase
            phase_value = str(entry.get('phase', '')).upper()
            if phase_value not in valid_phases:
                error = (
                    f"Entry {i+1} ('{entry['title']}') "
                    f"has invalid phase: {entry.get('phase')}"
                )
                errors.append(error)
                self.logger.warning(error)
                continue
            # normalize phase
            entry['phase'] = phase_value
    
            # Validate and normalize date
            raw_date = str(entry.get('date', '')).strip()
            parsed_iso = self._parse_date_to_iso(raw_date)
            if not parsed_iso:
                error = (
                    f"Entry {i+1} ('{entry['title']}') "
                    f"has invalid date: {entry.get('date')}"
                )
                errors.append(error)
                self.logger.warning(error)
                continue
    
            # Optional: warn if date is in the past
            try:
                parsed_date = datetime.date.fromisoformat(parsed_iso)
                if parsed_date < today:
                    self.logger.warning(
                        f"Entry {i+1} ('{entry['title']}') has a past date: {parsed_iso}"
                    )
            except Exception:
                # shouldn't happen because parsed_iso came from fromisoformat
                pass
    
            # set normalized date string
            entry['date'] = parsed_iso
    
            # optionally validate time formats here (skipped to keep parity with original)
    
            valid_entries.append(entry)
    
        self.logger.info(
            f"Validated {len(valid_entries)}/{len(entries)} entries ({len(errors)} errors)"
        )
        return valid_entries, errors