# File: src/models/enum.py

from enum import Enum

class PriorityTier(Enum):
    """Task priority tiers based on urgency."""
    T1 = "T1"  # CRITICAL - >12 hours/day or deadline today
    T2 = "T2"  # HIGH - 6-12 hours/day
    T3 = "T3"  # MEDIUM - 3-6 hours/day
    T4 = "T4"  # NORMAL - 1.5-3 hour/day
    T5 = "T5"  # LOW - 0.75-1.5 hour/day
    T6 = "T6"  # CHORES - No deadline
    T7 = "T7"  # VERY LOW - <0.75 hour/day


class Frequency(Enum):
    """Habit frequency options."""
    DAILY = "Daily"
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
