from dataclasses import dataclass
from typing import Optional
from .enums import Frequency
from .phase import Phase

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
