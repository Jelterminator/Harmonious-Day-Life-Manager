# File: src/processors/habit_processor.py
"""
Habit processing module for Harmonious Day.
Filters habits based on frequency and active status.
"""

import datetime
from typing import List, Dict, Any

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def filter_habits(raw_habits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters the raw list of habits to select only those that are relevant for today.
    
    Habits are filtered based on:
    - Active status (must be 'yes', 'true', '1', 'active', or 'on')
    - Frequency:
        - Daily: Always included
        - Weekly: Only if today matches the due_day
    
    Args:
        raw_habits: List of habit dictionaries from Google Sheets
    
    Returns:
        List of filtered habits relevant for today
    
    Example:
        >>> raw_habits = [
        ...     {'title': 'Morning Run', 'active': 'yes', 'frequency': 'Daily'},
        ...     {'title': 'Weekly Review', 'active': 'yes', 'frequency': 'Weekly', 'due_day': 'Monday'}
        ... ]
        >>> filtered = filter_habits(raw_habits)  # On Monday
        >>> len(filtered)
        2
    """
    today_weekday_name = datetime.date.today().strftime("%A")
    
    logger.info(f"Filtering habits for {today_weekday_name}")
    logger.debug(f"Processing {len(raw_habits)} total habits")
    
    relevant_habits = []
    skipped_count = 0
    
    for habit in raw_habits:
        # More robust active status check
        active_status = str(habit.get('active', '')).strip().lower()
        is_active = active_status in ['yes', 'true', '1', 'active', 'on']
        
        if not is_active:
            skipped_count += 1
            logger.debug(f"Skipping inactive habit: {habit.get('title', 'Unknown')}")
            continue
        
        frequency = habit.get('frequency', 'Daily')
        
        # Daily habits - always include
        if frequency == 'Daily':
            relevant_habits.append(habit)
            logger.debug(f"Including daily habit: {habit.get('title', 'Unknown')}")
            
        # Weekly habits - check if today matches due day
        elif frequency == 'Weekly':
            due_day = str(habit.get('due_day', '')).strip()
            if due_day.lower() == today_weekday_name.lower():
                relevant_habits.append(habit)
                logger.debug(f"Including weekly habit: {habit.get('title', 'Unknown')}")
            else:
                logger.debug(
                    f"Skipping weekly habit '{habit.get('title', 'Unknown')}' "
                    f"(due on {due_day}, today is {today_weekday_name})"
                )
        else:
            logger.warning(
                f"Unknown frequency '{frequency}' for habit: {habit.get('title', 'Unknown')}"
            )
    
    logger.info(
        f"Filtered habits: {len(relevant_habits)} relevant, "
        f"{skipped_count} inactive, "
        f"{len(raw_habits) - len(relevant_habits) - skipped_count} not scheduled for today"
    )
    
    return relevant_habits