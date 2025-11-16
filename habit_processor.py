# File: habit_processor.py

import datetime
from typing import List, Dict, Any

def filter_habits(raw_habits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters the raw list of habits to select only those that are relevant for today.
    """
    
    today_weekday_name = datetime.date.today().strftime("%A")
    
    print(f"Filtering habits for today: {today_weekday_name}...")
    print(f"Total habits to process: {len(raw_habits)}")
    
    relevant_habits = []
    
    for habit in raw_habits:
        # More robust active status check
        active_status = str(habit.get('active', '')).strip().lower()
        is_active = active_status in ['yes', 'true', '1', 'active', 'on']
        
        if not is_active:
            continue
        
        frequency = habit.get('frequency', 'Daily')
        
        # Daily habits - always include
        if frequency == 'Daily':
            relevant_habits.append(habit)
            
        # Weekly habits - check if today matches due day
        elif frequency == 'Weekly':
            due_day = str(habit.get('due_day', '')).strip()
            if due_day.lower() == today_weekday_name.lower():
                relevant_habits.append(habit)
    return relevant_habits
