import json
import datetime
from pathlib import Path
from googleapiclient.errors import HttpError
from auth import get_google_services
from deepseek_integration import get_groq_api_key, call_groq_llm, pretty_print_schedule
from task_processor import process_tasks
from collections import defaultdict

SHEET_ID = "1rdyKSYIT7NsIFtKg6UUeCnPEUUDtceKF3sfoVSwiaDM"
HABIT_RANGE = "Habits!A1:G100"
RULES_FILE = Path("config.json")

# --- GLOBAL CONFIGURATION FOR STEP 4 (CALENDAR WRITE) ---
TARGET_TIMEZONE = 'Europe/Amsterdam'
# IMPORTANT: This ID is used to uniquely mark and safely DELETE ONLY the events 
# created by this orchestrator. Do not change it unless you want to lose the ability 
# to clean up old events.
GENERATOR_ID = 'AI_Harmonious_Day_Orchestrator_v1' 


# --- GOOGLE API HELPER FUNCTIONS ---

def load_rules(file_path):
    """Load Harmonious Day rules from JSON file."""
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
    """
    Fetch all of today's calendar events that were NOT created by this script.
    These are the fixed appointments/constraints (meetings, etc.).
    """
    print("Fetching today's fixed calendar events...")
    try:
        today = datetime.date.today()
        # Use datetime module from the standard library
        start_of_day = datetime.datetime.combine(today, datetime.time.min).isoformat() + 'Z'
        end_of_day = datetime.datetime.combine(today, datetime.time.max).isoformat() + 'Z'

        # Fetch all events today
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_of_day,
            timeMax=end_of_day,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return []
        formatted_events = []
        for event in events:
            # ONLY keep events that do NOT have the GENERATOR_ID tag
            extended_props = event.get('extendedProperties', {}).get('private', {})
            if extended_props.get('sourceId') != GENERATOR_ID: 
                formatted_events.append({
                    "summary": event['summary'],
                    "start": event['start'].get('dateTime', event['start'].get('date')),
                    "end": event['end'].get('dateTime', event['end'].get('date'))
                })
        
        return formatted_events
        
    except Exception as e:
        print(f"Error fetching calendar events: {e}")
        return []



def delete_generated_events(calendar_service, date_str):
    """
    Deletes all events previously created by this script for the given date.
    This prevents duplicates and ensures idempotency. It only deletes events 
    tagged with the unique GENERATOR_ID.
    """
    print(f"\n--- CLEANUP: Deleting existing generated events for {date_str} ---")
    
    try:
        # 1. Prepare time window for today
        start_of_day = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        end_of_day = start_of_day.replace(hour=23, minute=59, second=59)

        # 2. Query events using the unique extended property (sourceId)
        # This is the safe guard—it only finds events this script created.
        query_params = {
            'calendarId': 'primary',
            'timeMin': start_of_day.isoformat() + 'Z',
            'timeMax': end_of_day.isoformat() + 'Z',
            'singleEvents': True,
            # Filter by our unique private extended property key/value pair
            'privateExtendedProperty': f'sourceId={GENERATOR_ID}'
        }
        
        events_result = calendar_service.events().list(**query_params).execute()
        events_to_delete = events_result.get('items', [])
        
        if not events_to_delete:
            print("INFO: No previous AI-generated schedule events found to delete.")
            return

        print(f"INFO: Found {len(events_to_delete)} previously generated events to delete...")
        
        deleted_count = 0
        batch = calendar_service.new_batch_http_request()

        def callback(request_id, response, exception):
            nonlocal deleted_count
            if exception is not None:
                print(f"Error deleting event (ID: {request_id}): {exception}")
            else:
                deleted_count += 1

        for event in events_to_delete:
            batch.add(
                calendar_service.events().delete(
                    calendarId='primary', 
                    eventId=event['id']
                ), 
                callback=callback
            )
            
        batch.execute()
        
        print(f"✓ SUCCESSFULLY DELETED {deleted_count} PREVIOUSLY GENERATED EVENTS.")
        
    except HttpError as e:
        print(f"ERROR deleting events (HTTP Error): {e}")
    except Exception as e:
        print(f"ERROR deleting events: {e}")

def get_google_tasks(service):
    """Fetch all open tasks from all task lists (raw data), including parent relationships."""
    print("Fetching tasks from Google Tasks...")
    all_tasks = []
    try:
        task_lists = service.tasklists().list().execute().get('items', [])
        
        for tlist in task_lists:
            
            tasks = []
            page_token = None
            
            # Handle pagination
            while True:
                tasks_result = service.tasks().list(
                    tasklist=tlist['id'],
                    showCompleted=False,
                    maxResults=500,
                    pageToken=page_token
                ).execute()
                
                page_tasks = tasks_result.get('items', [])
                tasks.extend(page_tasks)
                
                page_token = tasks_result.get('nextPageToken')
                if not page_token:
                    break
            
            for task in tasks:
                all_tasks.append({
                    "title": task.get('title', 'No Title'),
                    "list": tlist['title'],
                    "id": task['id'],
                    "parent": task.get('parent'),
                    "due": task.get('due'),
                    "notes": task.get('notes'),
                    "position": task.get('position', '0'),  # CRITICAL: Add position for ordering
                    "updated": task.get('updated')
                })

        return all_tasks
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return []

    
def get_habits(service, sheet_id, range_name):
    """Fetch habits from Google Sheets."""
    print("Fetching habits from Google Sheets...")
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values or len(values) < 2:
            print("No habit data found in sheet.")
            return []
            
        headers = values[0]
        habits_data = []
        
        for row in values[1:]:
            # Ensure the row data is mapped correctly, handling short rows
            habit = {headers[i]: (row[i] if i < len(row) else None) for i in range(len(headers))}
            habits_data.append(habit)
            
        return habits_data
    except Exception as e:
        print(f"Error fetching habits: {e}")
        return []


# --- WORLD PROMPT BUILDER ---

def build_world_prompt(rules, calendar_events, tasks, habits):
    """Assemble all data into a World Prompt for AI scheduling based on Harmonious Day philosophy."""

    today_str = datetime.date.today().strftime("%A, %B %d, %Y")

    prompt = f"# SCHEDULE GENERATION REQUEST\n\nToday is: {today_str}\n\n"
    prompt += "Create a complete daily schedule based on the Harmonious Day philosophy.\n\n"
    
    # Add task statistics for context
    if tasks:
        t1_count = sum(1 for t in tasks if t['priority'] == 'T1')
        t2_count = sum(1 for t in tasks if t['priority'] == 'T2')
        total_effort = sum(t['effort_hours'] for t in tasks)
        prompt += f"**TASK OVERVIEW**: {len(tasks)} tasks ({t1_count} URGENT T1, {t2_count} HIGH T2) = ~{total_effort:.1f}h total effort\n\n"

    # 1. Phases
    prompt += "## 1. HARMONIOUS DAY PHASES\n"
    for phase in rules.get('phases', []):
        phase_name = phase['name'].split()[-1]
        prompt += f"**{phase_name}** ({phase['start']}-{phase['end']})\n"
        prompt += f"- {phase['qualities']}\n"
        prompt += f"- Ideal Tasks: {', '.join(phase['ideal_tasks'])}\n\n"

    # 2. Anchors
    prompt += "## 2. SACRED ANCHOR POINTS (Fixed)\n"
    for anchor in rules.get('anchors', []):
        prompt += f"- {anchor['time']}: {anchor['name']}\n"

    # 3. Calendar Events
    prompt += "\n## 3. EXISTING CALENDAR EVENTS (Do Not Schedule Over)\n"
    prompt += "THESE ARE FIXED APPOINTMENTS. DO NOT MODIFY OR DELETE THEM.\n"
    if calendar_events:
        for event in calendar_events:
            prompt += f"- **{event['summary']}** ({event['start']} to {event['end']})\n"
    else:
        prompt += "No existing fixed appointments.\n"

    # 4. Tasks - with detailed project context
    prompt += "\n## 4. TASKS TO SCHEDULE (Prioritized by Urgency)\n"
    prompt += "**CRITICAL CONTEXT**: For multi-step tasks, priority is calculated based on TOTAL remaining work vs deadline.\n"
    prompt += "**RULE**: Only the FIRST incomplete subtask of each parent is shown. Complete it today to unlock the next.\n\n"
    
    if tasks:
        # Group by priority for clarity
        by_priority = defaultdict(list)
        for task in tasks:
            by_priority[task['priority']].append(task)
        
        for priority in ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7']:
            if priority in by_priority:
                priority_tasks = by_priority[priority]
                total_hours = sum(t['effort_hours'] for t in priority_tasks)
                
                if priority == 'T1':
                    prompt += f"### 🚨 {priority} - CRITICAL URGENCY - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
                    prompt += "These require >8h/day of work to meet deadline, or are past due. MUST schedule today.\n\n"
                elif priority == 'T2':
                    prompt += f"### ⚠️ {priority} - HIGH URGENCY - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
                    prompt += "These require 6-8h/day of work to meet deadline. Schedule as much as possible.\n\n"
                elif priority == 'T3':
                    prompt += f"### {priority} - MODERATE - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
                else:
                    prompt += f"### {priority} - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
                
                for task in priority_tasks:
                    this_task_effort = f"{task['effort_hours']:.1f}h"
                    total_remaining = f"{task['total_remaining_effort']:.1f}h"
                    deadline = task.get('deadline_str', 'N/A')
                    days_left = f"{task.get('days_until_deadline', 0):.1f}"
                    hours_per_day = f"{task.get('hours_per_day_needed', 0):.1f}"
                    
                    if task.get('is_subtask'):
                        prompt += f"- **{task['title']}** [Step 1 of {task['remaining_subtasks']} in: {task.get('parent_title', 'Unknown')}]\n"
                        prompt += f"  - THIS task: {this_task_effort} | TOTAL project: {total_remaining} remaining\n"
                        prompt += f"  - Deadline: {deadline} ({days_left} days) | Need: {hours_per_day}h/day to finish on time\n"
                    else:
                        prompt += f"- **{task['title']}**\n"
                        prompt += f"  - Effort: {this_task_effort}\n"
                        prompt += f"  - Deadline: {deadline} ({days_left} days) | Need: {hours_per_day}h/day\n"
                    
                    if task.get('notes'):
                        notes_clean = task['notes'].replace('\n', ' ').strip()
                        if notes_clean and not notes_clean.startswith('[Effort:'):
                            prompt += f"  - Notes: {notes_clean}\n"
                    
                    prompt += "\n"
    else:
        prompt += "No high-priority tasks.\n"

    # 5. Habits
    prompt += "\n## 5. HABITS TO SCHEDULE\n"
    prompt += (
        "Tasks take absolute priority. Only include habits that fit after T1/T2 tasks are scheduled.\n"
        "Aim for Task:Habit ratio of 3:1. Prefer habits not done recently.\n\n"
    )
    if habits:
        for habit in habits:
            prompt += f"- [ ] **{habit.get('title', 'Unknown')}**"
            if habit.get('frequency'):
                prompt += f" (Frequency: {habit.get('frequency')})"
            if habit.get('last_completed'):
                prompt += f" | Last: {habit.get('last_completed')}"
            prompt += "\n"
    else:
        prompt += "No habits.\n"

    # 6. Output Requirements
    prompt += "\n## 6. OUTPUT REQUIREMENTS\n"
    prompt += "Rules:\n"
    prompt += "- **T1/T2 PRIORITY**: Schedule all T1 tasks, as many T2 as possible. These are calculated based on total remaining effort vs deadline.\n"
    prompt += "- **ONE SUBTASK PER PARENT**: Only schedule the first incomplete subtask shown. Don't invent additional steps.\n"
    prompt += "- **SEQUENTIAL**: Complete today's subtask before tomorrow's subtask can be scheduled.\n"
    prompt += "- Respect anchors and fixed calendar events\n"
    prompt += "- Match tasks to ideal phases when possible, but urgency overrides phase preference\n"
    prompt += "- Split tasks over 90 minutes into smaller blocks with breaks\n"
    prompt += "- Be realistic: 6-8 hours of focused work max\n"
    prompt += "- Include breaks between blocks (10-15 min)\n"
    prompt += "- Habits only in remaining time after tasks\n\n"
    
    prompt += "Return JSON with this structure:\n"
    prompt += '{\n  "schedule_entries": [\n'
    prompt += '    {"title": "...", "start_time": "HH:MM", "end_time": "HH:MM", "phase": "Wood|Fire|Earth|Metal|Water"}\n'
    prompt += '  ]\n}\n'

    return prompt



def save_schedule_to_file(schedule_data, filename="generated_schedule.json"):
    """Save schedule JSON to file."""
    try:
        output_path = Path(filename)
        with open(output_path, 'w') as f:
            json.dump(schedule_data, f, indent=2)
        print(f"✓ Schedule saved to {output_path}")
    except Exception as e:
        print(f"ERROR: Could not save schedule: {e}")


# --- STEP 4: WRITING TO CALENDAR ---

def create_calendar_events(calendar_service, schedule_entries, date_str):
    """
    Writes the generated schedule entries as events to the primary Google Calendar.
    
    Args:
        calendar_service: The authenticated Google Calendar service object.
        schedule_entries (list): List of dictionaries containing 'title', 'start_time', 'end_time', and 'phase'.
        date_str (str): The date in 'YYYY-MM-DD' format (e.g., '2025-11-11').
    """
    print("\n--- STEP 4: WRITING TO GOOGLE CALENDAR ---")
    
    # Mapping phases to Google Calendar colors (1-11) for visual distinction
    color_map = {
        'Wood': '2',   # Green (Growth)
        'Fire': '11',  # Orange/Red (Energy/Deep Work)
        'Earth': '1',  # Light Blue/Default (Integration/Rest)
        'Metal': '5',  # Yellow/Gold (Planning/Admin)
        'Water': '10'  # Purple (Rest/Training)
    }
    
    count = 0
    # Create a batch request for speed and efficiency
    batch = calendar_service.new_batch_http_request()

    def callback(request_id, response, exception):
        nonlocal count
        if exception is not None:
            # Report the error for failed events
            print(f"Error inserting event (ID: {request_id}): {exception}")
        else:
            count += 1

    for entry in schedule_entries:
        try:
            # Combine the date string with the time string (e.g., '2025-11-11 09:00')
            start_dt = datetime.datetime.strptime(f"{date_str} {entry['start_time']}", "%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.strptime(f"{date_str} {entry['end_time']}", "%Y-%m-%d %H:%M")
            
            event = {
                'summary': entry['title'],
                'description': f"Phase: {entry['phase']}",
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': TARGET_TIMEZONE,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': TARGET_TIMEZONE,
                },
                'colorId': color_map.get(entry['phase'], '1'),
                # Notifications REMOVED: Events will now use the calendar's default setting.
                'extendedProperties': {
                    'private': {
                        'harmoniousDayGenerated': date_str,
                        'sourceId': GENERATOR_ID # This unique ID is crucial for safe cleanup.
                    }
                },
            }

            # Add the event insertion to the batch for later execution
            batch.add(calendar_service.events().insert(calendarId='primary', body=event), callback=callback)

        except Exception as e:
            print(f"Skipping entry due to formatting error for '{entry.get('title', 'Unknown')}': {e}")
            
    # Execute the batch insertion
    print(f"Writing {len(schedule_entries)} events to Google Calendar in a single batch...")
    batch.execute()

    print(f"\n✓ SUCCESSFULLY WROTE {count} EVENTS TO YOUR GOOGLE CALENDAR!")
    print("\n" + "="*60)
    print("           THE HARMONIOUS DAY IS SCHEDULED!             ")
    print("="*60)

def filter_conflicting_entries(schedule_entries, existing_events):
    """
    Remove any AI-scheduled events that overlap with user's fixed calendar events.
    """
    def parse_time(dt_str):
        # Handles both full ISO and 'YYYY-MM-DDTHH:MM:SSZ'
        try:
            return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M")

    filtered = []
    for entry in schedule_entries:
        entry_start = datetime.datetime.strptime(entry['start_time'], "%H:%M").time()
        entry_end = datetime.datetime.strptime(entry['end_time'], "%H:%M").time()

        conflict = False
        for evt in existing_events:
            evt_start = parse_time(evt['start']).time()
            evt_end = parse_time(evt['end']).time()

            # Simple overlap test
            if (entry_start < evt_end) and (entry_end > evt_start):
                conflict = True
                break

        if conflict:
            print(f"⚠️ Skipping '{entry['title']}' (conflicts with a fixed event)")
        else:
            filtered.append(entry)

    return filtered

# --- MAIN ORCHESTRATOR EXECUTION ---

if __name__ == "__main__":
    print("="*40)
    print("  AI LIFE ORCHESTRATOR ")
    print("="*40 + "\n")
    
    # Determine today's date for use in both the prompt and calendar writing
    TODAY_DATE_STR = datetime.date.today().strftime("%Y-%m-%d")
    
    api_key = get_groq_api_key()
    if not api_key:
        print("\n❌ Need DeepSeek API key")
        print("Get from: https://platform.deepseek.com/")
        print("Set with: export DEEPSEEK_API_KEY='your-key'")
        exit(1)
    
    print("Authenticating with Google...")
    calendar_service, sheets_service, tasks_service = get_google_services()
    
    if not all([calendar_service, sheets_service, tasks_service]):
        print("❌ Google authentication failed")
        exit(1)
    
    print("✓ Authenticated\n")
    
    print("Loading configuration...")
    rules = load_rules(RULES_FILE)
    if not rules:
        print("❌ Config load failed")
        exit(1)
    print("✓ Config loaded\n")
    
    # --- CRITICAL CLEANUP STEP ---
    # This runs BEFORE fetching constraints or generating the schedule.
    # It removes old AI-generated events to prevent duplicates.
    delete_generated_events(calendar_service, TODAY_DATE_STR)
    # ---------------------------
    
    print("Gathering data...")
    # NOTE: get_calendar_events now ignores events created by this script.
    calendar_events = get_calendar_events(calendar_service) 
    
    # --- TASK PROCESSING STEP ---
    raw_tasks = get_google_tasks(tasks_service)
    tasks = process_tasks(raw_tasks) 
    # --------------------------
    
    habits = get_habits(sheets_service, SHEET_ID, HABIT_RANGE)
    
    print(f"✓ {len(calendar_events)} fixed calendar events (Meetings, etc.)")
    print(f"✓ {len(tasks)} prioritized tasks ({len(raw_tasks)} total)") 
    print(f"✓ {len(habits)} habits")
    
    print("Building World Prompt...")
    world_prompt = build_world_prompt(rules, calendar_events, tasks, habits)
    
    prompt_file = Path("last_world_prompt.txt")
    with open(prompt_file, 'w') as f:
        f.write(world_prompt)
    print(f"✓ Prompt saved to {prompt_file}\n")
    
    print("Sending to GROQ AI...")
    print("-"*60)
    schedule_data = call_groq_llm(world_prompt, api_key)

    
    
    if schedule_data:
        print("\n✓ Schedule generated!\n")
        
        pretty_print_schedule(schedule_data)
        save_schedule_to_file(schedule_data)
        
        # --- FINAL STEP: WRITE TO CALENDAR ---
        schedule_entries = schedule_data.get('schedule_entries', []) if isinstance(schedule_data, dict) else schedule_data

        # Filter out any AI events that overlap existing fixed calendar events
        schedule_entries = filter_conflicting_entries(schedule_entries, calendar_events)
        
        if calendar_service and schedule_entries:
            # This inserts the new, clean schedule.
            create_calendar_events(calendar_service, schedule_entries, TODAY_DATE_STR)
        else:
            print("ERROR: Final schedule is empty or calendar service is unavailable. Cannot proceed to Step 4.")
            
    else:
        print("\n❌ Schedule generation failed")
        exit(1)
