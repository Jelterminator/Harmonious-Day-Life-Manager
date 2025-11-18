# File: src/models/models.py
"""
Data models for Harmonious Day.
Typed dataclasses to replace dictionaries throughout the codebase.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List
from enum import Enum


# ==================== Enums ====================

class PriorityTier(Enum):
    """Task priority tiers based on urgency."""
    T1 = "T1"  # CRITICAL - >4 hours/day or deadline today
    T2 = "T2"  # HIGH - 2-4 hours/day
    T3 = "T3"  # MEDIUM - 1-2 hours/day
    T4 = "T4"  # NORMAL - 0.5-1 hour/day
    T5 = "T5"  # LOW - 0.25-0.5 hour/day
    T6 = "T6"  # CHORES - No deadline
    T7 = "T7"  # VERY LOW - <0.25 hour/day


class Phase(Enum):
    """Wu Xing phases of the day."""
    WOOD = "WOOD"    # 05:30-09:00 - Growth, planning
    FIRE = "FIRE"    # 09:00-13:00 - Peak energy
    EARTH = "EARTH"  # 13:00-15:00 - Grounding
    METAL = "METAL"  # 15:00-18:00 - Organization
    WATER = "WATER"  # 18:00-21:45 - Rest


class Frequency(Enum):
    """Habit frequency options."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"


# ==================== Calendar Models ====================

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


# ==================== Task Models ====================

@dataclass
class Task:
    """Represents a task with priority and deadline."""
    id: str
    title: str
    effort_hours: float
    priority: PriorityTier
    deadline: Optional[datetime] = None
    parent_id: Optional[str] = None
    parent_title: Optional[str] = None
    is_subtask: bool = False
    notes: Optional[str] = None
    list_name: Optional[str] = None
    position: str = "0"
    
    # Calculated fields
    days_until_deadline: float = 0.0
    hours_per_day_needed: float = 0.0
    total_remaining_effort: float = 0.0
    
    def __post_init__(self):
        """Validate task data and auto-convert types."""
        if self.effort_hours < 0:
            raise ValueError(f"Effort hours cannot be negative: {self.title}")
        
        # Auto-convert string priority to Enum
        if isinstance(self.priority, str):
            try:
                self.priority = PriorityTier(self.priority)
            except ValueError:
                # Fallback to default priority
                self.priority = PriorityTier.T4

        # FIX: Only convert deadline if it's a string AND not None
        if self.deadline and isinstance(self.deadline, str):
            try:
                # Use the helper function from your models
                from src.models.models import parse_iso_datetime
                self.deadline = parse_iso_datetime(self.deadline)
            except (ValueError, AttributeError):
                # If parsing fails, set to None
                self.deadline = None
    
    @property
    def deadline_str(self) -> str:
        """Get formatted deadline string."""
        if self.deadline:
            return self.deadline.strftime("%Y-%m-%d")
        return "N/A"
    
    def is_urgent(self) -> bool:
        """Check if task is urgent (T1 or T2)."""
        return self.priority in [PriorityTier.T1, PriorityTier.T2]
    
    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.deadline:
            return False
        # FIX: Handle timezone-aware comparison
        now = datetime.now(self.deadline.tzinfo) if self.deadline.tzinfo else datetime.now()
        return now > self.deadline
    
    def to_dict(self) -> dict:
        """Convert to dictionary for backwards compatibility."""
        return {
            'id': self.id,
            'title': self.title,
            'effort_hours': self.effort_hours,
            'priority': self.priority.value,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'deadline_str': self.deadline_str,
            'parent_id': self.parent_id,
            'parent_title': self.parent_title,
            'is_subtask': self.is_subtask,
            'notes': self.notes,
            'days_until_deadline': self.days_until_deadline,
            'hours_per_day_needed': self.hours_per_day_needed,
            'total_remaining_effort': self.total_remaining_effort,
        }

@dataclass
class TaskProject:
    """Represents a parent task with subtasks."""
    parent_task: Task
    subtasks: List[Task] = field(default_factory=list)
    total_effort: float = 0.0
    deadline: Optional[datetime] = None
    
    def __post_init__(self):
        """Calculate total effort and earliest deadline."""
        if not self.total_effort:
            self.total_effort = sum(t.effort_hours for t in self.subtasks)
        
        if not self.deadline and self.subtasks:
            deadlines = [t.deadline for t in self.subtasks if t.deadline]
            if deadlines:
                self.deadline = min(deadlines)


# ==================== Habit Models ====================

@dataclass
class Habit:
    """Represents a daily or weekly habit."""
    id: str
    title: str
    duration_min: int
    frequency: Frequency
    ideal_phase: Phase
    task_type: str
    due_day: Optional[str] = None
    active: bool = True
    
    def __post_init__(self):
        """Validate and convert types."""
        # Convert string frequency to enum
        if isinstance(self.frequency, str):
            self.frequency = Frequency(self.frequency)
        
        # Convert string phase to enum
        if isinstance(self.ideal_phase, str):
            self.ideal_phase = Phase(self.ideal_phase)
        
        # Validate duration
        if self.duration_min <= 0:
            raise ValueError(f"Duration must be positive: {self.title}")
    
    def is_scheduled_today(self, weekday_name: str) -> bool:
        """Check if habit should be scheduled today."""
        if not self.active:
            return False
        
        if self.frequency == Frequency.DAILY:
            return True
        
        if self.frequency == Frequency.WEEKLY:
            return self.due_day and self.due_day.lower() == weekday_name.lower()
        
        return False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for backwards compatibility."""
        return {
            'id': self.id,
            'title': self.title,
            'duration_min': self.duration_min,
            'frequency': self.frequency.value,
            'ideal_phase': self.ideal_phase.value,
            'task_type': self.task_type,
            'due_day': self.due_day,
            'active': self.active,
        }


# ==================== Schedule Models ====================

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


# ==================== Configuration Models ====================

@dataclass
class PhaseConfig:
    """Configuration for a Wu Xing phase."""
    name: Phase
    start: str  # "HH:MM" format
    end: str    # "HH:MM" format
    qualities: str
    ideal_tasks: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Convert string name to enum, handling icons."""
        if isinstance(self.name, str):
            # Handle "🌳 WOOD" -> "WOOD"
            clean_name = self.name.split(' ')[-1] if ' ' in self.name else self.name
            try:
                self.name = Phase(clean_name)
            except ValueError:
                # Fallback if config has invalid phase name
                self.name = Phase.FIRE


@dataclass
class Anchor:
    """Spiritual/time anchor (e.g., prayer times)."""
    name: str
    time: str  # "HH:MM-HH:MM" format
    phase: Phase
    
    def __post_init__(self):
        """Convert string phase to enum."""
        if isinstance(self.phase, str):
            self.phase = Phase(self.phase)
    
    def get_start_end(self) -> tuple[str, str]:
        """Parse time range into start and end times."""
        if '-' in self.time:
            start, end = self.time.split('-')
            return start.strip(), end.strip()
        return self.time, self.time


@dataclass
class AppConfig:
    """Complete application configuration."""
    phases: List[PhaseConfig]
    anchors: List[Anchor]
    timezone: str = "UTC"
    max_output_tasks: int = 24
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """Create AppConfig from dictionary (e.g., loaded from JSON)."""
        phases = [PhaseConfig(**p) for p in data.get('phases', [])]
        anchors = [Anchor(**a) for a in data.get('anchors', [])]
        
        return cls(
            phases=phases,
            anchors=anchors,
            timezone=data.get('timezone', 'UTC'),
            max_output_tasks=data.get('max_output_tasks', 24)
        )


# ==================== API Response Models ====================

@dataclass
class LLMResponse:
    """Response from LLM API."""
    status: str  # "success" or "fail"
    schedule: Optional[Schedule] = None
    message: Optional[str] = None
    raw_response: Optional[dict] = None
    
    def is_success(self) -> bool:
        """Check if response was successful."""
        return self.status == "success" and self.schedule is not None


@dataclass
class ValidationError:
    """Represents a validation error."""
    field: str
    message: str
    entry_index: Optional[int] = None
    
    def __str__(self) -> str:
        """String representation of error."""
        if self.entry_index is not None:
            return f"Entry {self.entry_index} - {self.field}: {self.message}"
        return f"{self.field}: {self.message}"


# ==================== Helper Functions ====================

def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Robustly parse ISO date strings with 'Z' or offsets."""
    if not date_str:
        return None
    try:
        # specific fix for Python < 3.11 which doesn't handle 'Z' natively in fromisoformat
        clean_str = date_str.replace('Z', '+00:00')
        return datetime.fromisoformat(clean_str)
    except ValueError:
        # Fallback for simple date strings without time
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

def task_from_dict(data: dict) -> Task:
    """Create Task from dictionary with type safety."""
    # Handle Priority Enum conversion safely
    raw_priority = data.get('priority', 'T4')
    try:
        # Handle both "T1" (value) and "PriorityTier.T1" (name) if passed loosely
        if isinstance(raw_priority, str):
            # Strip "PriorityTier." if present
            clean_priority = raw_priority.split('.')[-1]
            priority = PriorityTier(clean_priority)
        else:
            priority = raw_priority
    except ValueError:
        priority = PriorityTier.T4  # Default to Normal if invalid

    return Task(
        id=str(data.get('id', '')), # Ensure string
        title=str(data.get('title', 'Untitled Task')),
        effort_hours=float(data.get('effort_hours', 1.0)),
        priority=priority,
        deadline=parse_iso_datetime(data.get('deadline')),
        parent_id=data.get('parent_id'),
        parent_title=data.get('parent_title'),
        is_subtask=bool(data.get('is_subtask', False)),
        notes=data.get('notes'),
        list_name=data.get('list_name'),
        position=str(data.get('position', '0')),
        # Preserve calculated fields if they exist in the dict
        days_until_deadline=float(data.get('days_until_deadline', 0.0)),
        hours_per_day_needed=float(data.get('hours_per_day_needed', 0.0)),
        total_remaining_effort=float(data.get('total_remaining_effort', 0.0)),
    )

def habit_from_dict(data: dict) -> Habit:
    """Create Habit from dictionary with robust boolean/enum parsing."""
    # Handle Frequency
    try:
        raw_freq = data.get('frequency', 'Daily')
        freq = Frequency(raw_freq) if isinstance(raw_freq, str) else raw_freq
    except ValueError:
        freq = Frequency.DAILY

    # Handle Phase
    try:
        raw_phase = data.get('ideal_phase', 'FIRE')
        phase = Phase(raw_phase) if isinstance(raw_phase, str) else raw_phase
    except ValueError:
        phase = Phase.FIRE

    # Handle Active Boolean (Excel/CSV often uses "Yes"/"No" or "TRUE")
    raw_active = str(data.get('active', 'True')).lower()
    is_active = raw_active in ['yes', 'true', '1', 'active', 'y', 't']

    return Habit(
        id=str(data.get('id', '')),
        title=str(data.get('title', 'Untitled Habit')),
        duration_min=int(float(data.get('duration_min', 15))), # Handle "15.0" strings
        frequency=freq,
        ideal_phase=phase,
        task_type=str(data.get('task_type', 'Habit')),
        due_day=data.get('due_day'),
        active=is_active,
    )

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