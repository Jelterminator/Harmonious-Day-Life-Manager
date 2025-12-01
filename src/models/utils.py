# File: src/models/utils.py
"""
Utility functions for Harmonious Day models.
"""

from datetime import datetime
from typing import Optional
from .enums import PriorityTier, Frequency
from .phase import Phase
from .tasks import Task
from .habits import Habit
from .schedule import ScheduleEntry

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
