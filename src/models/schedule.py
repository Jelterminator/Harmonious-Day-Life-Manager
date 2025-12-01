# File: src/models/schedule.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from .phase import Phase
from .common import parse_iso_datetime

@dataclass
class ScheduleEntry:
    """Represents a single entry in the generated schedule."""
    title: str
    start_time: datetime
    end_time: datetime
    phase: Phase
    date_indicator: str  # "today" or "tomorrow"
    
    # Optional metadata
    is_fixed: bool = False
    task_id: Optional[str] = None
    habit_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate entry data."""
        # Convert string phase to enum
        if isinstance(self.phase, str):
            self.phase = Phase(self.phase)
        
        # Validate times
        if self.end_time <= self.start_time:
            # Allow overnight entries
            if (self.end_time.date() > self.start_time.date()):
                raise ValueError(
                    f"Entry end must be after start: {self.title}"
                )
    
    def duration_minutes(self) -> int:
        """Calculate entry duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)
    
    def overlaps_with(self, other: 'ScheduleEntry') -> bool:
        """Check if this entry overlaps with another."""
        return self.start_time < other.end_time and self.end_time > other.start_time
    
    def to_dict(self) -> dict:
        """Convert to dictionary for LLM output format."""
        return {
            'title': self.title,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'phase': self.phase.value,
            'date': self.date_indicator.lower(),
        }


@dataclass
class Schedule:
    """Represents a complete daily schedule."""
    entries: List[ScheduleEntry] = field(default_factory=list)
    generation_date: datetime = field(default_factory=datetime.now)
    
    def add_entry(self, entry: ScheduleEntry) -> None:
        """Add an entry to the schedule."""
        self.entries.append(entry)
    
    def get_entries_by_phase(self, phase: Phase) -> List[ScheduleEntry]:
        """Get all entries for a specific phase."""
        return [e for e in self.entries if e.phase == phase]
    
    def get_entries_for_date(self, date_indicator: str) -> List[ScheduleEntry]:
        """Get entries for 'today' or 'tomorrow'."""
        return [e for e in self.entries if e.date_indicator == date_indicator]
    
    def total_scheduled_minutes(self) -> int:
        """Calculate total scheduled time in minutes."""
        return sum(e.duration_minutes() for e in self.entries)
    
    def has_conflicts(self) -> bool:
        """Check if schedule has any overlapping entries."""
        for i, entry1 in enumerate(self.entries):
            for entry2 in self.entries[i+1:]:
                if entry1.overlaps_with(entry2):
                    return True
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'schedule_entries': [e.to_dict() for e in self.entries],
            'generation_date': self.generation_date.isoformat(),
            'total_minutes': self.total_scheduled_minutes(),
        }

def schedule_entry_from_dict(data: dict) -> ScheduleEntry:
    """Create ScheduleEntry from dictionary."""
    return ScheduleEntry(
        title=data['title'],
        start_time=parse_iso_datetime(data['start_time']), # Use the helper
        end_time=parse_iso_datetime(data['end_time']),     # Use the helper
        phase=Phase(data['phase']) if isinstance(data['phase'], str) else data['phase'],
        date_indicator=data.get('date', 'today'),
        is_fixed=bool(data.get('is_fixed', False)),
        task_id=data.get('task_id'),
        habit_id=data.get('habit_id') 
    )
