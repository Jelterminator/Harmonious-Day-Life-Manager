import json
import datetime
from pathlib import Path

# Import our auth function from the separate file
from auth import get_google_services

# --- CONFIGURATION ---
# 1. The ID of your Habit Tracker Google Sheet
SHEET_ID = "1rdyKSYIT7NsIFtKg6UUeCnPEUUDtceKF3sfoVSwiaDM" 

# 2. The name of the tab (and range) for your habits
#    This MUST match your sheet, e.g., "Habits!A1:G100"
HABIT_RANGE = "Habits!A1:G100" # Make sure the tab name is correct!

# 3. The path to your new rules engine
RULES_FILE = Path("config.json")


def load_rules(file_path):
    """Loads the Harmonious Day rules from the JSON file."""
    print(f"Loading rules from {file_path}...")
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: {file_path} contains invalid JSON.")
        return None

def get_calendar_events(service):
    """Fetches all of today's calendar events."""
    print("Fetching today's calendar events...")
    try:
        today = datetime.date.today()
        start_of_day = datetime.datetime.combine(today, datetime.time.min).isoformat() + 'Z'
        end_of_day = datetime.datetime.combine(today, datetime.time.max).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return [] # No events, just return empty list
            
        # Format for the AI
        formatted_events = [
            {
                "summary": event['summary'],
                "start": event['start'].get('dateTime', event['start'].get('date')),
                "end": event['end'].get('dateTime', event['end'].get('date'))
            } for event in events
        ]
        return formatted_events
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return []

def get_google_tasks(service):
    """Fetches all open tasks from all task lists."""
    print("Fetching tasks from Google Tasks...")
    all_tasks = []
    try:
        task_lists = service.tasklists().list().execute().get('items', [])
        
        for tlist in task_lists:
            tasks_result = service.tasks().list(
                tasklist=tlist['id'],
                showCompleted=False,
                maxResults=100
            ).execute()
            
            tasks = tasks_result.get('items', [])
            
            for task in tasks:
                all_tasks.append({
                    "title": task.get('title', 'No Title'),
                    "list": tlist['title'],
                    "id": task['id'],
                    "due": task.get('due'),
                    "notes": task.get('notes')
                })
        return all_tasks
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

def get_habits(service, sheet_id, range_name):
    """Fetches habits from Google Sheets and returns a list of dicts."""
    print("Fetching habits from Google Sheets...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            print("No habit data or headers found in GSheet.")
            return []
            
        headers = values[0]
        habits_data = []
        
        for row in values[1:]:
            # Create a dict for each row, matching header to value
            habit = {headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers))}
            habits_data.append(habit)
            
        return habits_data
    except Exception as e:
        print(f"Error fetching habits: {e}")
        return []

def get_daily_sport(sport_schedule):
    """Gets today's specific 'Harde Sport' from the schedule."""
    today_weekday = str(datetime.date.today().weekday()) # 0=Monday, 6=Sunday
    return sport_schedule.get(today_weekday, {"name": "Rest Day", "details": "No sport scheduled."})


def build_world_prompt(rules, calendar_events, tasks, habits, daily_sport):
    """Assembles all fetched data into a single 'World Prompt' for the AI."""
    
    today_str = datetime.date.today().strftime("%A, %B %d, %Y")
    
    # --- 1. The Persona and Goal ---
    prompt = (
        "You are an expert life scheduler, blending the Harmonious Day philosophy (a fusion of Deen and Dao) "
        "with practical task management. Your goal is to create a complete, optimal, and harmonious "
        "schedule for today in JSON format. Do not schedule over 'Anchor Events' or 'Busy Time'.\n\n"
        f"Today is: {today_str}\n"
    )
    
    # --- 2. The Rules ---
    prompt += "## 1. Harmonious Day Philosophy (The Rules)\n"
    prompt += "These are the energetic phases of the day. Schedule tasks in their ideal phase.\n"
    for phase in rules.get('phases', []):
        prompt += f"* **{phase['name']} ({phase['start']}-{phase['end']}):** {phase['qualities']} (Ideal: {', '.join(phase['ideal_tasks'])})\n"

    # --- 3. Anchor Points (from config) ---
    prompt += "\n## 2. Harmonious Day Anchor Points (The Framework)\n"
    prompt += "These are the non-negotiable pillars of the day. The schedule must flow around them.\n"
    for anchor in rules.get('anchors', []):
        prompt += f"* **{anchor['time']}:** {anchor['name']}\n"

    # --- 4. Calendar Events (from GCal) ---
    prompt += "\n## 3. Today's Anchor Events & Busy Time (From Calendar)\n"
    prompt += "These are external appointments. You MUST schedule around them.\n"
    if calendar_events:
        for event in calendar_events:
            prompt += f"* {event['summary']} (Starts: {event['start']}, Ends: {event['end']})\n"
    else:
        prompt += "* No busy appointments today.\n"

    # --- 5. Tasks (from GTasks) ---
    prompt += "\n## 4. Task List (To Be Scheduled)\n"
    prompt += "These are the tasks that need to be slotted into the day.\n"
    if tasks:
        for task in tasks:
            prompt += f"* [ ] **{task['title']}** (From List: '{task['list']}')\n"
            if task['notes']:
                prompt += f"      Notes: {task['notes'].replace('n', ' ')}\n"
    else:
        prompt += "* No tasks to schedule.\n"

    # --- 6. Habits (from GSheet) ---
    prompt += "\n## 5. Habit Database (To Be Scheduled)\n"
    prompt += "These are recurring habits. Schedule them, paying attention to 'last_completed'.\n"
    if habits:
        for habit in habits:
            prompt += f"* [ ] **{habit.get('title')}** (Type: {habit.get('task_type')}, Freq: {habit.get('frequency')}, Last: {habit.get('last_completed')})\n"
    else:
        prompt += "* No habits found in Google Sheet.\n"

    # --- 7. Sport (from config) ---
    prompt += "\n## 6. Today's 'Harde Sport' Focus\n"
    prompt += "This is the specific physical training for today, part of the Water phase.\n"
    prompt += f"* **{daily_sport['name']}**: {daily_sport['details']}\n"
    
    # --- 8. The Instruction ---
    prompt += "\n## 7. Your Task\n"
    prompt += (
        "Based on all this data, generate a complete schedule for today. "
        "Return **only a JSON array** of `schedule_entries`."
        "Each entry must have 'title', 'start_time', 'end_time', and 'phase' (e.g., 'Wood', 'Fire')."
        "Be realistic with timing and include breaks. Ensure you schedule all tasks and habits."
    )
    
    return prompt


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    # 1. Authenticate and get services
    calendar_service, sheets_service, tasks_service = get_google_services()
    
    if all([calendar_service, sheets_service, tasks_service]):
        # 2. Load the rules
        rules = load_rules(RULES_FILE)
        
        if rules:
            # 3. Fetch all state data
            calendar_events = get_calendar_events(calendar_service)
            tasks = get_google_tasks(tasks_service)
            habits = get_habits(sheets_service, SHEET_ID, HABIT_RANGE)
            daily_sport = get_daily_sport(rules.get('sport_schedule', {}))
            
            # 4. Build the World Prompt
            world_prompt = build_world_prompt(rules, calendar_events, tasks, habits, daily_sport)
            
            # --- This is the final output of Step 2 ---
            print("=========================================================")
            print("               WORLD PROMPT (Ready for AI)               ")
            print("=========================================================")
            print(world_prompt)
            print("=========================================================")
            print("\nStep 2 Complete. We are ready to send this to DeepSeek.")
