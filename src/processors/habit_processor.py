# File: src/processors/habit_processor.py
"""
Habit processing module for Harmonious Day.
Filters habits based on frequency and active status using typed models.
"""

import datetime
from typing import List

from src.utils.logger import setup_logger
# Import the Habit and Frequency models
from src.models.models import Habit, Frequency

logger = setup_logger(__name__)


def filter_habits(habits: List[Habit]) -> List[Habit]:
    """
    Filters the list of Habit objects to select only those that are relevant for today.
    
    Habits are filtered based on:
    - Active status (must be True)
    - Frequency:
        - DAILY: Always included
        - WEEKLY: Only if today matches the due_day
    
    Args:
        habits: List of typed Habit objects
    
    Returns:
        List of filtered Habit objects relevant for today
    """
    # Get the current day of the week, e.g., "Tuesday"
    today_weekday_name = datetime.date.today().strftime("%A")
    
    logger.info(f"Filtering habits for {today_weekday_name}")
    logger.debug(f"Processing {len(habits)} total habits")
    
    relevant_habits: List[Habit] = []
    skipped_inactive_count = 0
    
    for habit in habits:
        # Check active status directly from the boolean attribute
        if not habit.active:
            skipped_inactive_count += 1
            logger.debug(f"Skipping inactive habit: {habit.title}")
            continue
            
        # Use the Frequency Enum value
        frequency = habit.frequency
        
        # Daily habits - always include
        if frequency == Frequency.DAILY:
            relevant_habits.append(habit)
            logger.debug(f"Including daily habit: {habit.title}")
            
        # Weekly habits - check if today matches due day
        elif frequency == Frequency.WEEKLY:
            due_day = habit.due_day
            
            if due_day and due_day.lower() == today_weekday_name.lower():
                relevant_habits.append(habit)
                logger.debug(f"Including weekly habit: {habit.title}")
            else:
                logger.debug(
                    f"Skipping weekly habit '{habit.title}' "
                    f"(due on {due_day}, today is {today_weekday_name})"
                )
                
        # Handle other or unexpected frequencies
        else:
            logger.warning(
                f"Unsupported frequency '{frequency.value}' for habit: {habit.title}"
            )
    
    skipped_frequency_count = len(habits) - len(relevant_habits) - skipped_inactive_count
    
    logger.info(
        f"Filtered habits: {len(relevant_habits)} relevant, "
        f"{skipped_inactive_count} inactive, "
        f"{skipped_frequency_count} not scheduled for today"
    )
    
    return relevant_habits