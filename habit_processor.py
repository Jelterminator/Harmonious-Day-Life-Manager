import random
import datetime

# Day name mapping for filtering
WEEKDAY_MAP = {
    0: 'Monday',
    1: 'Tuesday', 
    2: 'Wednesday',
    3: 'Thursday',
    4: 'Friday',
    5: 'Saturday',
    6: 'Sunday'
}

def filter_habits(habits, target_date=None):
    """
    Filter habits based on frequency, date parity, and random selection rules.
    
    Args:
        habits: List of habit dictionaries from config.json or Google Sheets
        target_date: datetime.date object (defaults to today)
    
    Returns:
        List of filtered habits that should be scheduled for the target date
    """
    if target_date is None:
        target_date = datetime.date.today()
    
    day_of_week = WEEKDAY_MAP[target_date.weekday()]
    day_number = target_date.day
    is_even_date = (day_number % 2 == 0)
    is_odd_date = (day_number % 2 == 1)
    
    filtered = []
    
    for habit in habits:
        habit_title = habit.get('title', '').strip()
        frequency = habit.get('frequency', 'Daily').strip()
        
        # Rule 1: Filter by frequency (day of week)
        if frequency == 'Daily':
            pass  # Include for all days
        elif frequency == 'Weekly':
            # Weekly habits need specific day assignment
            # Check if habit has a specific day in its ID or notes
            habit_id = habit.get('id', '')
            
            # Map weekly sports to specific days based on due_day column
            weekly_day_map = {
                'S01': 'Monday',
                'S02': 'Tuesday',
                'S03': 'Wednesday',
                'S04': 'Thursday',
                'S05': 'Friday',
                'S06': 'Saturday',
                'S07': 'Sunday',
                'H14': 'Sunday'  # Weekly Reflection
            }
            
            if habit_id in weekly_day_map:
                if weekly_day_map[habit_id] != day_of_week:
                    continue  # Skip if not the right day
            elif 'Weekly Reflection' in habit_title:
                if day_of_week != 'Sunday':  # Default weekly tasks to Sunday
                    continue
            elif 'Call Family' in habit_title:
                if day_of_week != 'Sunday':
                    continue
            else:
                # Other weekly habits default to Sunday
                if day_of_week != 'Sunday':
                    continue
        else:
            # Unknown frequency, skip
            continue
        
        # Rule 2: Date parity filters (EVEN dates)
        if is_even_date:
            if habit.get('id') == 'H07':  # Circuit training
                continue
            if habit.get('id') == 'H11':  # Meditation (Earth Phase)
                continue
            if habit.get('id') == 'H15':  # Xi Sui Jing
                continue
            if habit.get('id') == 'H19':  # Yoga Nidra
                continue
        
        # Rule 3: Date parity filters (ODD dates)
        if is_odd_date:
            if habit.get('id') == 'H05':  # Morning run
                continue
            if habit.get('id') == 'H13':  # Sketching
                continue
            if habit.get('id') == 'H16':  # Asana Yoga
                continue
            if habit.get('id') == 'H18':  # Meditation (Water Phase)
                continue
        
        # Rule 4: Random 50% filter for Reading (Water Phase)
        if habit.get('id') == 'H17':  # Reading (Water Phase)
            # Use date as seed for consistency within the same day
            random.seed(target_date.toordinal())
            if random.random() < 0.5:
                continue
            # Reset seed to avoid affecting other random operations
            random.seed()
        
        # If we've made it here, include the habit
        filtered.append(habit)
    
    return filtered
