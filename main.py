# File: main.py
#
# This module defines the main Orchestrator class.
# It is NOT intended to be run directly.
# Run 'init.py' or 'plan.py' instead.

import json
import datetime
from typing import List, Dict, Any
from pathlib import Path
from collections import defaultdict
import pytz

# --- Local Module Imports ---
# We keep these as separate files for clean Single Responsibility
from auth import get_google_services, create_initial_token
from llm_integration import get_groq_api_key, call_groq_llm, pretty_print_schedule
from task_processor import process_tasks
from habit_processor import filter_habits

# --- Constants ---
SHEET_ID = "1rdyKSYIT7NsIFtKg6UUeCnPEUUDtceKF3sfoVSwiaDM"
HABIT_RANGE = "Habits!A1:G100"
RULES_FILE = Path("config.json")
PROMPT_FILE = Path("last_world_prompt.txt")
SCHEDULE_FILE = Path("generated_schedule.json")

TARGET_TIMEZONE = 'Europe/Amsterdam'
GENERATOR_ID = 'AI_Harmonious_Day_Orchestrator_v1'


class Orchestrator:
    """
    Encapsulates all logic for the AI Life Orchestrator.
    
    This class handles authentication, data fetching, processing,
    AI prompting, and writing to the calendar.
    """
    
    def __init__(self):
        """
        Initializes the Orchestrator by loading static configs and services.
        """
        print("Initializing Orchestrator...")
        
        # 1. Load Groq API Key
        self.api_key = get_groq_api_key()
        if not self.api_key:
            raise ValueError("Groq API Key not found. Set GROQ_API_KEY env var.")
        print("✓ Groq API Key loaded")

        # 2. Load Static Rules
        self.rules = self._load_rules(RULES_FILE)
        if not self.rules:
            raise FileNotFoundError(f"Config file not found or invalid: {RULES_FILE}")
        print("✓ Config loaded")
        
        # 3. Authenticate with Google (fast, using token.json)
        print("Authenticating with Google...")
        services = get_google_services()
        if not all(services):
            raise ConnectionError("Google authentication failed. Run 'init.py'.")
        
        self.services = {
            "calendar": services[0],
            "sheets": services[1],
            "tasks": services[2]
        }
        print("✓ Google Services Authenticated\n")
        
        self.today_date_str = datetime.date.today().strftime("%Y-%m-%d")

    # --------------------------------------------------------------------------
    # Public "Run" Method
    # --------------------------------------------------------------------------

    def run_daily_plan(self):
        """
        Executes the full daily planning pipeline.
        This is the main public method to call.
        """
        print("\n" + "="*40)
        print("  AI LIFE ORCHESTRATOR - RUNNING DAILY PLAN")
        print("="*40 + "\n")

        try:
            # 1. Cleanup
            self._delete_generated_events()
            
            # 2. Gather Data
            print("\n--- STEP 1: GATHERING DATA ---")
            calendar_events = self._get_calendar_events()
            raw_tasks = self._get_google_tasks()
            raw_habits = self._get_habits()

            # 3. Process Data
            print("\n--- STEP 2: PROCESSING DATA ---")
            tasks = process_tasks(raw_tasks) 
            habits = filter_habits(raw_habits)
            print(f"✓ {len(calendar_events)} fixed calendar events")
            print(f"✓ {len(tasks)} prioritized tasks ({len(raw_tasks)} total)") 
            print(f"✓ {len(habits)} habits for today")

            # 4. Build Prompt
            print("\n--- STEP 3: BUILDING PROMPT ---")
            world_prompt = self._build_world_prompt(calendar_events, tasks, habits)
            PROMPT_FILE.write_text(world_prompt, encoding="utf-8")
            print(f"✓ Prompt saved to {PROMPT_FILE}")

            # 5. Call AI
            print("\n--- STEP 4: CALLING AI ---")
            schedule_data = call_groq_llm(world_prompt, self.api_key)
            if not schedule_data:
                print("\n❌ Schedule generation failed. AI returned no data.")
                return

            print("\n✓ Schedule generated!")
            pretty_print_schedule(schedule_data)
            self._save_schedule_to_file(schedule_data, SCHEDULE_FILE)
            
            # 6. Post-Process & Write to Calendar
            print("\n--- STEP 5: WRITING TO CALENDAR ---")
            schedule_entries = schedule_data.get('schedule_entries', [])
            final_entries = self._filter_conflicting_entries(schedule_entries, calendar_events)
            
            if final_entries:
                self._create_calendar_events(final_entries)
            else:
                print("ERROR: Final schedule is empty after filtering. No events to create.")

            print("\n" + "="*60)
            print("              THE HARMONIOUS DAY IS SCHEDULED!             ")
            print("="*60)

        except Exception as e:
            print(f"\n--- FATAL ERROR IN DAILY PLANNING ---")
            import traceback
            traceback.print_exc()

    # --------------------------------------------------------------------------
    # Static "Init" Method
    # --------------------------------------------------------------------------
    
    @staticmethod
    def create_initial_token():
        """
        Static method to run the one-time-only Google auth flow.
        This is called by 'init.py'.
        """
        print("--- Starting One-Time Google Authentication ---")
        print("A browser window will open. Please log in.")
        create_initial_token() # This function is now in auth.py
        print("\n✅ SUCCESS: 'token.json' created!")
        print("You can now run 'plan.py' anytime.")

    # --------------------------------------------------------------------------
    # Internal Helper Methods (Private)
    # --------------------------------------------------------------------------

    def _load_rules(self, file_path: Path) -> Dict[str, Any]:
        """Load Harmonious Day rules from JSON file."""
        try:
            with open(file_path, 'r', encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading rules: {e}")
            return None

    # --- Data Fetching Methods ---

    def _get_calendar_events(self) -> List[Dict[str, str]]:
        """Fetch fixed calendar events."""
        print("Fetching fixed calendar events...")
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            end_of_tomorrow = (
                datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=2),
                                          datetime.time.min)
                .replace(tzinfo=datetime.timezone.utc)
            )

            events_result = self.services["calendar"].events().list(
                calendarId='primary',
                timeMin=now.isoformat(),
                timeMax=end_of_tomorrow.isoformat(),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            formatted_events = []
            for event in events:
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

    def _delete_generated_events(self):
        """Deletes all events previously created by this script."""
        print(f"--- CLEANUP: Deleting existing generated events for {self.today_date_str} ---")
        try:
            start_of_day = datetime.datetime.strptime(self.today_date_str, "%Y-%m-%d")
            end_of_window = start_of_day + datetime.timedelta(days=2)
            time_min = start_of_day.isoformat() + 'Z'
            time_max = end_of_window.isoformat() + 'Z'

            events_result = self.services["calendar"].events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                privateExtendedProperty=f'sourceId={GENERATOR_ID}'
            ).execute()
            
            events_to_delete = events_result.get('items', [])
            if not events_to_delete:
                print("INFO: No previous AI-generated events found to delete.")
                return

            print(f"INFO: Found {len(events_to_delete)} previously generated events to delete...")
            batch = self.services["calendar"].new_batch_http_request()
            deleted_count = 0

            def callback(request_id, response, exception):
                nonlocal deleted_count
                if exception is None:
                    deleted_count += 1
            
            for event in events_to_delete:
                batch.add(
                    self.services["calendar"].events().delete(
                        calendarId='primary', eventId=event['id']
                    ),
                    callback=callback
                )
            batch.execute()
            print(f"✓ SUCCESSFULLY DELETED {deleted_count} PREVIOUSLY GENERATED EVENTS.")
        except Exception as e:
            print(f"ERROR deleting events: {e}")

    def _get_google_tasks(self) -> List[Dict[str, Any]]:
        """Fetch all open tasks from all task lists."""
        print("Fetching tasks from Google Tasks...")
        all_tasks = []
        try:
            task_lists = self.services["tasks"].tasklists().list().execute().get('items', [])
            for tlist in task_lists:
                tasks_result = self.services["tasks"].tasks().list(
                    tasklist=tlist['id'],
                    showCompleted=False,
                    maxResults=100
                ).execute()
                
                for task in tasks_result.get('items', []):
                    all_tasks.append({
                        "title": task.get('title', 'No Title'),
                        "list": tlist['title'], "id": task['id'],
                        "parent": task.get('parent'), "due": task.get('due'),
                        "notes": task.get('notes'),
                    })
            return all_tasks
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            return []

    def _get_habits(self) -> List[Dict[str, Any]]:
        """Fetch habits from Google Sheets."""
        print("Fetching habits from Google Sheets...")
        try:
            result = self.services["sheets"].spreadsheets().values().get(
                spreadsheetId=SHEET_ID, range=HABIT_RANGE
            ).execute()
            values = result.get('values', [])
            if not values or len(values) < 2:
                print("No habit data found in sheet.")
                return []
            
            headers = values[0]
            habits_data = []
            for row in values[1:]:
                row_padded = row + [None] * (len(headers) - len(row))
                habit = {headers[i]: row_padded[i] for i in range(len(headers))}
                habits_data.append(habit)
            return habits_data
        except Exception as e:
            print(f"Error fetching habits: {e}")
            return []

    # --- Prompt & Schedule Processing Methods ---

    def _build_world_prompt(rules, calendar_events, tasks, habits):

        """Assemble all data into a World Prompt for AI scheduling based on Harmonious Day philosophy."""
    
        prompt = f"# SCHEDULE GENERATION REQUEST\n"
        prompt += "Create a schedule for the rest of today and all of tomorrow based on the Harmonious Day philosophy.\n\n"
    
    
    
        now = datetime.datetime.now()
    
        now_str = now.strftime("%Y-%m-%d %H:%M")
    
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    
        tomorrow_str = tomorrow.strftime("%Y-%m-%d")
    
        
    
        prompt += f"**CURRENT TIME**: {now_str}\n"
    
        prompt += f"**IMPORTANT**: Any events scheduled before {now.strftime('%H:%M')} today should be skipped.\n"
    
        prompt += f"The schedule window is from NOW ({now_str}) until the end of tomorrow ({tomorrow_str} 23:59).\n\n"
    
        
    
        # Add task statistics
    
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
    
    
    
        # 4. Tasks
    
        prompt += "\n## 4. TASKS TO SCHEDULE (Prioritized by Urgency)\n"
    
        prompt += "**CRITICAL CONTEXT**: For multi-step tasks, priority is calculated based on TOTAL remaining work vs deadline.\n"
    
        
    
        if tasks:
    
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
    
        prompt += "A single calendar input does not need to be the whole task, and if a task is long its pieces may be planned as multiple events over the course of a day.\n"
    
        prompt += "Remember to change the end time of each event properly: no double bookings allowed.\n\n"
    
    
    
        # 5. Habits
    
        prompt += "## 5. HABITS TO SCHEDULE\n"
    
        prompt += (
    
            "Tasks take absolute priority. Only include habits that fit after T1/T2 tasks are scheduled.\n"
    
            "Aim for a Task:Habit ratio of 3:1. Plan tasks first, then see which habits are possible.\n"
    
            "Habit durations are flexible (±50%).\n"
    
            "Reading must happen every day (minimum 20 minutes).\n\n"
    
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
    
        prompt += "- **T1/T2 PRIORITY**: Schedule all T1 tasks, as many T2 as possible.\n"
    
        prompt += "- Respect anchors and fixed calendar events. Never overlap events.\n"
    
        prompt += "- Match tasks to ideal phases when possible, but urgency overrides phase preference.\n"
    
        prompt += "- Be realistic: 6-10 hours of focused work max per day.\n"
    
        prompt += f"- **DO NOT schedule anything before {now.strftime('%H:%M')} today - that time has passed!**\n"
    
        prompt += "- For events spanning two days, indicate which date in the title (e.g., 'Tomorrow: Task Name').\n\n"
    
        
    
        prompt += "Return JSON with this structure:\n"
    
        prompt += '{\n  "schedule_entries": [\n'
    
        prompt += '    {"title": "...", "start_time": "HH:MM", "end_time": "HH:MM", "phase": "Wood|Fire|Earth|Metal|Water", "date": "today|tomorrow"}\n'
    
        prompt += '  ]\n}\n'
    
        prompt += '\nThe "date" field should be "today" or "tomorrow" to clarify which day the event belongs to.\n'
    
    
    
        return prompt

    def _save_schedule_to_file(self, schedule_data: Dict[str, Any], filename: Path):
        """Save schedule JSON to file (UTF-8)."""
        try:
            # Added a safety check for non-ASCII characters if not using ensure_ascii=False
            with open(filename, 'w', encoding="utf-8") as f:
                json.dump(schedule_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Schedule saved to {filename}")
        except Exception as e:
            # Using specific print for consistency
            print(f"ERROR: Could not save schedule: {e}")

    def _filter_conflicting_entries(self, schedule_entries: List[Dict[str, Any]], existing_events: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Remove AI entries that overlap fixed calendar events."""
        
        # Helper function for robust ISO parsing of fixed events
        def parse_iso(dt_str: str) -> datetime.datetime | None:
            """Parses ISO string, handling 'Z' and ensuring conversion to local timezone-aware DT."""
            try:
                # Use TARGET_TIMEZONE constant from the class/module scope
                local_tz = pytz.timezone(TARGET_TIMEZONE)
                dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                
                # Convert DT to the target timezone (handles different TZ formats)
                if dt.tzinfo is None:
                    # Assume naive DTs are already in the target timezone
                    dt = local_tz.localize(dt)
                else:
                    dt = dt.astimezone(local_tz)
                    
                # Return the timezone-aware datetime
                return dt
            except Exception as e:
                # print(f"Error parsing date string {dt_str}: {e}") # Optional: Debugging log
                return None
        
        print("Filtering generated schedule against fixed events...")
        filtered = []
        
        # Use instance variables for dates/timezone consistency
        local_tz = pytz.timezone(TARGET_TIMEZONE)
        today = datetime.date.today()
        tomorrow = today + datetime.timedelta(days=1)
        
        # Pre-process fixed events once to get standardized, timezone-aware datetimes
        parsed_fixed_events = []
        for evt in existing_events:
            s = parse_iso(evt.get('start', ''))
            e = parse_iso(evt.get('end', ''))
            if s and e:
                parsed_fixed_events.append({'summary': evt.get('summary', 'Unknown'), 'start': s, 'end': e})

        for entry in schedule_entries:
            try:
                date_indicator = entry.get('date', 'today').lower()
                entry_date = tomorrow if date_indicator == 'tomorrow' else today
                
                # 1. Create TIMEZONE-AWARE datetimes for the scheduled entry
                start_h, start_m = map(int, entry['start_time'].split(":"))
                end_h, end_m = map(int, entry['end_time'].split(":"))
                
                start_time_naive = datetime.time(start_h, start_m)
                end_time_naive = datetime.time(end_h, end_m)
                
                entry_start = local_tz.localize(datetime.datetime.combine(entry_date, start_time_naive))
                entry_end = local_tz.localize(datetime.datetime.combine(entry_date, end_time_naive))
                
                # 2. Handle overnight events (end time < start time)
                if entry_end <= entry_start:
                    entry_end += datetime.timedelta(days=1)
                
                has_conflict = False
                for evt in parsed_fixed_events:
                    # Check for overlap: Start1 < End2 AND End1 > Start2
                    if evt['start'] < entry_end and evt['end'] > entry_start:
                        has_conflict = True
                        print(f"⚠ Skipping '{entry['title']}' due to overlap with '{evt['summary']}' ({evt['start'].strftime('%H:%M')} - {evt['end'].strftime('%H:%M')})")
                        break
                
                if not has_conflict:
                    filtered.append(entry)
            
            except (ValueError, KeyError) as e:
                print(f"Skipping entry due to malformed time/date for '{entry.get('title', 'Unknown')}': {e}")
                
        print(f"✓ Filtered down to {len(filtered)} non-conflicting entries.")
        return filtered

    def _create_calendar_events(self, schedule_entries: List[Dict[str, Any]]):
        """Writes the generated schedule entries as events to the primary Google Calendar."""
        
        # Ensure we are using instance variables (self.services) and constants
        calendar_service = self.services["calendar"]
        date_str = self.today_date_str # Use the date str stored in __init__
        local_tz = pytz.timezone(TARGET_TIMEZONE)
        now = datetime.datetime.now(local_tz) # Now is timezone-aware
        
        # Use a dictionary lookup for calendar color IDs
        color_map = {
            'WOOD': '10', 'FIRE': '11', 'EARTH': '5',
            'METAL': '8', 'WATER': '9'
        }
        
        count = 0
        batch = calendar_service.new_batch_http_request()
        
        today_date = datetime.date.today()
        tomorrow_date = today_date + datetime.timedelta(days=1)

        def callback(request_id, response, exception):
            nonlocal count
            if exception is not None:
                # Log detailed error for debugging
                print(f"Error inserting event (ID: {request_id}): {exception}")
            else:
                count += 1
        
        print(f"Writing {len(schedule_entries)} events to Google Calendar...")

        for entry in schedule_entries:
            try:
                # 1. Determine date
                date_indicator = entry.get('date', 'today').lower()
                entry_date = tomorrow_date if date_indicator == 'tomorrow' else today_date
                
                # 2. Parse times
                start_h, start_m = map(int, entry['start_time'].split(":"))
                end_h, end_m = map(int, entry['end_time'].split(":"))
                
                # 3. Combine date and time, and localize to TARGET_TIMEZONE
                start_time_naive = datetime.time(start_h, start_m)
                end_time_naive = datetime.time(end_h, end_m)
                
                start_dt = local_tz.localize(datetime.datetime.combine(entry_date, start_time_naive))
                end_dt = local_tz.localize(datetime.datetime.combine(entry_date, end_time_naive))
                
                # 4. Handle overnight events (end time < start time)
                if end_dt <= start_dt:
                    end_dt = end_dt + datetime.timedelta(days=1)
                
                # 5. Skip events that are in the past (using localized 'now')
                if start_dt < now:
                    print(f"⏭ Skipping past event: {entry['title']} at {start_dt.strftime('%H:%M')}")
                    continue
                
                # 6. Build event body
                event = {
                    'summary': entry['title'],
                    'description': f"Phase: {entry.get('phase', 'N/A')}",
                    'start': {
                        'dateTime': start_dt.isoformat(),
                        'timeZone': TARGET_TIMEZONE,
                    },
                    'end': {
                        'dateTime': end_dt.isoformat(),
                        'timeZone': TARGET_TIMEZONE,
                    },
                    # Ensure phase name is capitalized for lookup
                    'colorId': color_map.get(entry.get('phase', '').upper(), '1'), 
                    'extendedProperties': {
                        'private': {
                            'harmoniousDayGenerated': date_str,
                            'sourceId': GENERATOR_ID
                        }
                    },
                }
                
                # 7. Add to batch
                batch.add(
                    calendar_service.events().insert(calendarId='primary', body=event),
                    callback=callback
                )
            
            except (ValueError, KeyError, TypeError) as e:
                print(f"Skipping entry due to formatting error for '{entry.get('title', 'Unknown')}': {e}")
        
        # Execute batch request
        if batch._requests: # Check if the batch has any requests added
             batch.execute()
        else:
            print("INFO: No events were scheduled after filtering out past events.")
            
        print(f"\n✓ SUCCESSFULLY WROTE {count} EVENTS TO YOUR GOOGLE CALENDAR!")
    
    
    