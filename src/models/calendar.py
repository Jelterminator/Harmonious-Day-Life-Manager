# File: src/models/calendar.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class CalendarEvent:
    """Represents a fixed calendar event."""
    summary: str
    start: datetime
    end: datetime
    event_id: Optional[str] = None
    description: Optional[str] = None
    is_generated: bool = False
    
    def __post_init__(self):
        """Validate event data."""
        if self.end <= self.start:
            raise ValueError(f"Event end time must be after start time: {self.summary}")
    
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes."""
        return int((self.end - self.start).total_seconds() / 60)
    
    def overlaps_with(self, other: 'CalendarEvent') -> bool:
        """Check if this event overlaps with another."""
        return self.start < other.end and self.end > other.start
