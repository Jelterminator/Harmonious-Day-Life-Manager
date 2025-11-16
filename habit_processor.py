# File: habit_processor.py

import datetime
from typing import List, Dict, Any

def filter_habits(raw_habits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters the raw list of habits to select only those that are relevant for today.
    
    A habit is relevant if:
    1. It is active ('active' == 'Yes').
    2. It is a 'Daily' habit.
    3. OR, it is a 'Weekly' habit and its 'due_day' matches today's weekday name.
    """
    
    # Get today's full weekday name (e.g., "Monday", "Tuesday")
    today_weekday_name = datetime.date.today().strftime("%A")
    
    print(f"Filtering habits for today: {today_weekday_name}...")
    
    relevant_habits = []
    
    for habit in raw_habits:
        # Check if the habit is active
        if habit.get('active', 'No') != 'Yes':
            continue
        
        frequency = habit.get('frequency', 'Daily')
        
        # 1. Include all 'Daily' habits
        if frequency == 'Daily':
            relevant_habits.append(habit)
            
        # 2. Check 'Weekly' habits against today's day
        elif frequency == 'Weekly':
            due_day = habit.get('due_day', '').strip()
            
            if due_day == today_weekday_name:
                relevant_habits.append(habit)
            
    return relevant_habits
