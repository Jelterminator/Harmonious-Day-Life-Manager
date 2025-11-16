# File: main.py
#
# This module defines the main Orchestrator class.
# It is NOT intended to be run directly.
# Run 'init.py' or 'plan.py' instead.

import json
import datetime
import sys
from typing import List, Dict, Any
from pathlib import Path
from googleapiclient.errors import HttpError
from collections import defaultdict

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

    def _build_world_prompt(self, calendar_events, tasks, habits) -> str:
        """Assemble all data into a World Prompt for AI scheduling."""
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        tomorrow_str = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        
        prompt = f"# SCHEDULE GENERATION REQUEST\n"
        prompt += f"**CURRENT TIME**: {now_str}\n"
        prompt += f"The schedule window is from NOW ({now_str}) until the end of tomorrow ({tomorrow_str} 23:59).\n\n"
        
        # ... (rest of your prompt-building logic) ...
        # (This is just a snippet; use your full prompt builder)
        
        # 3. Calendar Events
        prompt += "\n## 3. EXISTING CALENDAR EVENTS (Do Not Schedule Over)\n"
        if calendar_events:
            for event in calendar_events:
                prompt += f"- **{event['summary']}** ({event['start']} to {event['end']})\n"
        else:
            prompt += "No existing fixed appointments.\n"

        # 4. Tasks
        prompt += "\n## 4. TASKS TO SCHEDULE (Prioritized by Urgency)\n"
        if tasks:
            for task in tasks: # Simplify for example
                prompt += f"- **{task['title']}** (Priority: {task.get('priority', 'N/A')}, Effort: {task.get('effort_hours', 'N/A')}h)\n"
        else:
            prompt += "No high-priority tasks.\n"

        # 5. Habits
        prompt += "\n## 5. HABITS TO SCHEDULE\n"
        if habits:
            for habit in habits:
                prompt += f"- [ ] **{habit.get('title', 'Unknown')}** ({habit.get('duration_min')} min)\n"
        else:
            prompt += "No habits.\n"

        # 6. Output Requirements
        prompt += "\n## 6. OUTPUT REQUIREMENTS\n"
        prompt += "Return JSON with this structure:\n"
        prompt += '{\n  "schedule_entries": [\n'
        prompt += '    {"title": "...", "start_time": "HH:MM", "end_time": "HH:MM", "phase": "...", "date": "today|tomorrow"}\n'
        prompt += '  ]\n}\n'
        
        return prompt

    def _save_schedule_to_file(self, schedule_data: Dict[str, Any], filename: Path):
        """Save schedule JSON to file (UTF-8)."""
        try:
            with open(filename, 'w', encoding="utf-8") as f:
                json.dump(schedule_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Schedule saved to {filename}")
        except Exception as e:
            print(f"ERROR: Could not save schedule: {e}")

    def _filter_conflicting_entries(self, schedule_entries, existing_events):
        """Remove AI entries that overlap fixed calendar events."""
        print("Filtering generated schedule against fixed events...")
        # ... (Insert your full filter_conflicting_entries logic here) ...
        # This is just a placeholder
        print(f"Filtered {len(schedule_entries)} entries (placeholder).")
        return schedule_entries # Placeholder

    def _create_calendar_events(self, schedule_entries):
        """Writes the generated schedule entries to Google Calendar."""
        print(f"Writing {len(schedule_entries)} events to Google Calendar...")
        
        # ... (Insert your full create_calendar_events logic here) ...
        # This is just a placeholder
        
        print(f"\n✓ SUCCESSFULLY WROTE {len(schedule_entries)} EVENTS (placeholder)!")