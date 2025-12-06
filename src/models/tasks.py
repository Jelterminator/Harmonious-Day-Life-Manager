# src/models/tasks.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from .enums import PriorityTier
from .common import parse_iso_datetime

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
        deadline=parse_iso_datetime(data.get('deadline') or data.get('due')),
        parent_id=data.get('parent_id') or data.get('parent'),
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
