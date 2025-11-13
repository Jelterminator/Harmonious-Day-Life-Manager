import json
import datetime
from pathlib import Path
from googleapiclient.errors import HttpError
from auth import get_google_services
from llm_integration import get_groq_api_key, call_groq_llm, pretty_print_schedule
from task_processor import process_tasks
from habit_processor import filter_habits
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
    Fetch all events from now until the end of tomorrow,
    excluding events created by this orchestrator.
    """
    print("Fetching fixed calendar events for the rest of today and tomorrow...")
    try:
        now = datetime.datetime.now(datetime.timezone.utc)
        end_of_tomorrow = (
            datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=2),
                                      datetime.time.min)
            .replace(tzinfo=datetime.timezone.utc)
        )

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat(),
            timeMax=end_of_tomorrow.isoformat(),
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
    It only deletes events tagged with the unique GENERATOR_ID.
    """
    print(f"\n--- CLEANUP: Deleting existing generated events for {date_str} ---")

    try:
        # 1. Prepare time window starting at date_str 00:00:00 (naive)
        start_of_day = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        # cover the whole of today AND tomorrow by adding 2 days
        end_of_window = start_of_day + datetime.timedelta(days=2)

        # Use ISO format; Google API expects RFC3339. We send naive ISO + 'Z' (floating)
        time_min = start_of_day.isoformat() + 'Z'
        time_max = end_of_window.isoformat() + 'Z'

        query_params = {
            'calendarId': 'primary',
            'timeMin': time_min,
            'timeMax': time_max,
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

    prompt = f"# SCHEDULE GENERATION REQUEST\n"
    prompt += "Create a schedule for the rest of today and all of tomorrow based on the Harmonious Day philosophy.\n\n"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    prompt += f"The schedule window is from {now_str} until the end of {tomorrow_str} 23:59.\n\n"

    
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
        
    # 2. Anchors
    prompt += "## 2. SACRED ANCHOR POINTS (Fixed)\n"
    for anchor in rules.get('anchors', []):
        prompt += f"- {anchor['time']}: {anchor['name']}\n"

    # 3. Calendar Events
    prompt += "\n## 3. EXISTING CALENDAR EVENTS (Do Not Schedule Over)\n"
    prompt += "THESE ARE FIXED APPOINTMENTS: THEY CANNOT BE CANCELLED, RESCHEDULED OR MOVED. DO NOT MODIFY OR DELETE THEM.\n"
    if calendar_events:
        for event in calendar_events:
            prompt += f"- **{event['summary']}** ({event['start']} to {event['end']})\n"
    else:
        prompt += "No existing fixed appointments.\n"

    # 4. Tasks - with detailed project context
    prompt += "\n## 4. TASKS TO SCHEDULE (Prioritized by Urgency)\n"
    prompt += "**CRITICAL CONTEXT**: For multi-step tasks, priority is calculated based on TOTAL remaining work vs deadline.\n"
    
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
                    prompt += f"### {priority} - CRITICAL URGENCY - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
                    prompt += "These require >8h/day of work to meet deadline, or are past due. MUST schedule today.\n\n"
                elif priority == 'T2':
                    prompt += f"### {priority} - HIGH URGENCY - {len(priority_tasks)} tasks, {total_hours:.1f}h\n"
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

    prompt += "Try to plan tasks for more time than their project requires per day, otherwise the deadline will be missed.\n"
    prompt += "A single caledar input does not need to be the whole task, and if a task is long its pieces may be planned as multiple events over the course of a day. And even if the full task cannot be completed it is good to plan a part: something is better than nothing.\n"
    prompt += "Remember to change the time of the end of each event, so that the pieces of tasks do not become doubly planned agenda items.\n"

    # 5. Habits
    prompt += "\n## 5. HABITS TO SCHEDULE\n"
    prompt += (
        "Tasks take absolute priority. Only include habits that fit after T1/T2 tasks are scheduled.\n"
        "Aim for a Task:Habit ratio of 3:1. Just plan tasks first, and see which habits are possible after.\n"
        "The time habits take is very flexible and can be increased or decreased with up to 50%, if desired."
        "Reading must happen every day and the minimum time requirement is low: as few as 20 minutes can already be a reading event.\n\n"
    )
    if habits:
        for habit in habits:
            prompt += f"- [ ] **{habit.get('title', 'Unknown')}**"
            if habit.get('duration_min'):
                prompt += f" (Ideal duration: {habit.get('duration_min')} minutes)"
            if habit.get('frequency'):
                prompt += f" (Frequency: {habit.get('frequency')})"
            if habit.get('ideal_phase'):
                prompt += f" (Phase: {habit.get('ideal_phase')})"
            prompt += "\n"
    else:
        prompt += "No habits.\n"

    # 6. Output Requirements
    prompt += "\n## 6. OUTPUT REQUIREMENTS\n"
    prompt += "Rules:\n"
    prompt += "- **T1/T2 PRIORITY**: Schedule all T1 tasks, as many T2 as possible. These are calculated based on total remaining effort vs deadline.\n"
    prompt += "- Respect anchors and fixed calendar events, and never let events overlap.\n"
    prompt += "- Match tasks to ideal phases when possible, but urgency overrides phase preference\n"
    prompt += "- Be realistic: 6-10 hours of focused work max\n"
    
    prompt += "Return JSON with this structure:\n"
    prompt += '{\n  "schedule_entries": [\n'
    prompt += '    {"title": "...", "start_time": "HH:MM", "end_time": "HH:MM", "phase": "Wood|Fire|Earth|Metal|Water"}\n'
    prompt += '  ]\n}\n'

    return prompt

def save_schedule_to_file(schedule_data, filename="generated_schedule.json"):
    """Save schedule JSON to file (UTF-8)."""
    try:
        output_path = Path(filename)
        with open(output_path, 'w', encoding="utf-8") as f:
            json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Schedule saved to {output_path}")
    except Exception as e:
        print(f"ERROR: Could not save schedule: {e}")

# --- STEP 4: WRITING TO CALENDAR ---

def create_calendar_events(calendar_service, schedule_entries, date_str):
    """
    Writes the generated schedule entries as events to the primary Google Calendar.
    date_str: 'YYYY-MM-DD' for the start date (today). Entries that cross midnight will
    be placed on the next day.
    """
    print("\n--- STEP 4: WRITING TO GOOGLE CALENDAR ---")

    # Mapping phases to Google Calendar colors (1-11) for visual distinction
    color_map = {
        'Wood': '2',   # Green
        'Fire': '11',  # Orange/Red
        'Earth': '5',  # Yellow/Gold
        'Metal': '8',  # Light Blue
        'Water': '10'  # Purple
    }

    count = 0
    batch = calendar_service.new_batch_http_request()

    def callback(request_id, response, exception):
        nonlocal count
        if exception is not None:
            print(f"Error inserting event (ID: {request_id}): {exception}")
        else:
            count += 1

    for entry in schedule_entries:
        try:
            # Parse naive datetimes for the provided day
            # Detect whether the entry is for today or tomorrow
            entry_date = datetime.date.today()
            start_h, start_m = map(int, entry['start_time'].split(":"))
            # If AI time wraps around (e.g. "01:00" but after "23:00"), assume tomorrow
            if start_h < datetime.datetime.now().hour and datetime.datetime.now().hour > 18:
                entry_date += datetime.timedelta(days=1)
            
            start_dt = datetime.datetime.combine(entry_date, datetime.time(start_h, start_m))
            end_h, end_m = map(int, entry['end_time'].split(":"))
            end_dt = datetime.datetime.combine(entry_date, datetime.time(end_h, end_m))

            # If the end is <= start, assume it goes into the next day
            if end_dt <= start_dt:
                end_dt = end_dt + datetime.timedelta(days=1)

            event = {
                'summary': entry['title'],
                'description': f"Phase: {entry.get('phase', '')}",
                'start': {
                    'dateTime': start_dt.isoformat(),
                    'timeZone': TARGET_TIMEZONE,
                },
                'end': {
                    'dateTime': end_dt.isoformat(),
                    'timeZone': TARGET_TIMEZONE,
                },
                'colorId': color_map.get(entry.get('phase'), '1'),
                'extendedProperties': {
                    'private': {
                        'harmoniousDayGenerated': date_str,
                        'sourceId': GENERATOR_ID
                    }
                },
            }

            batch.add(calendar_service.events().insert(calendarId='primary', body=event), callback=callback)

        except Exception as e:
            print(f"Skipping entry due to formatting error for '{entry.get('title', 'Unknown')}': {e}")

    print(f"Writing {len(schedule_entries)} events to Google Calendar in a single batch...")
    batch.execute()

    print(f"\n✓ SUCCESSFULLY WROTE {count} EVENTS TO YOUR GOOGLE CALENDAR!")
    print("\n" + "="*60)
    print("           THE HARMONIOUS DAY IS SCHEDULED!             ")
    print("="*60)

def filter_conflicting_entries(schedule_entries, existing_events):
    """Remove AI entries that overlap fixed calendar events."""
    def parse_iso(dt_str):
        try:
            return datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except Exception:
            return None

    filtered = []
    for entry in schedule_entries:
        entry_start = datetime.datetime.strptime(entry['start_time'], "%H:%M").time()
        entry_end = datetime.datetime.strptime(entry['end_time'], "%H:%M").time()
        has_conflict = False

        for evt in existing_events:
            s = parse_iso(evt['start'])
            e = parse_iso(evt['end'])
            if not (s and e):
                continue
            # same day overlap
            if s.time() < entry_end and e.time() > entry_start:
                has_conflict = True
                print(f"Skipping '{entry['title']}' due to overlap with '{evt['summary']}'")
                break
        if not has_conflict:
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
        print("\n❌ Need API key")
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

    # --- HABIT PROCESSING STEP ---    
    raw_habits = get_habits(sheets_service, SHEET_ID, HABIT_RANGE)
    habits = filter_habits(raw_habits)
    
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
