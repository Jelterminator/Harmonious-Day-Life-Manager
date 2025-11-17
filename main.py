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
HABIT_RANGE = "Habits!A:H"
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
        print("\n" + "="*60)
        print("  AI LIFE ORCHESTRATOR - RUNNING DAILY PLAN")
        print("="*60 + "\n")

        try:
            # 1. Cleanup
            self._delete_generated_events()
            
            # 2. Gather Data
            print("\n--- STEP 1: GATHERING DATA ---")
            
            calendar_events = self._get_calendar_events()
            raw_tasks = self._get_google_tasks()
            raw_habits = self._get_habits()
            rules = self.rules

            # 3. Process Data
            print("\n--- STEP 2: PROCESSING DATA ---")
            tasks = process_tasks(raw_tasks) 
            habits = filter_habits(raw_habits)
            print(f"✓ {len(calendar_events)} fixed calendar events")
            print(f"✓ {len(tasks)} prioritized tasks ({len(raw_tasks)} total)") 
            print(f"✓ {len(habits)} habits for today ({len(raw_habits)} total)")

            # 4. Build Prompt
            print("\n--- STEP 3: BUILDING PROMPT ---")
            world_prompt = self._build_world_prompt(rules, calendar_events, tasks, habits)
            PROMPT_FILE.write_text(world_prompt, encoding="utf-8")
            print(f"✓ Prompt saved to {PROMPT_FILE}")

            # 5. Call AI
            print("\n--- STEP 4: CALLING AI ---")
            schedule_data = call_groq_llm(world_prompt, self.api_key)
            if not schedule_data:
                print("\n❌ Schedule generation failed. AI returned no data.")
                return

            print("\n✓ Schedule generated!")
            pretty_print_schedule(schedule_data, calendar_events)
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
        all_tasks = []
        print("Fetching tasks from Google Tasks...")
    
        try:
            task_lists = self.services["tasks"].tasklists().list().execute().get("items", [])
    
            for tlist in task_lists:
                page_token = None
    
                while True:
                    kwargs = {
                        "tasklist": tlist["id"],
                        "showCompleted": False,
                        "maxResults": 100,  # Google's real max
                    }
                    if page_token:
                        kwargs["pageToken"] = page_token
    
                    response = self.services["tasks"].tasks().list(**kwargs).execute()
    
                    for task in response.get("items", []):
                        # Only include open tasks
                        if task.get("status") != "needsAction":
                            continue
    
                        all_tasks.append({
                            "title": task.get("title", "No Title"),
                            "list": tlist["title"],
                            "id": task["id"],
                            "parent": task.get("parent"),
                            "due": task.get("due"),
                            "notes": task.get("notes"),
                        })
    
                    # Get next page
                    page_token = response.get("nextPageToken")
                    if not page_token:
                        break
    
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
            for i, row in enumerate(values[1:]):
                # Pad row to match header length
                row_padded = row + [''] * (len(headers) - len(row))
                habit = {headers[i]: row_padded[i] for i in range(len(headers))}
                habits_data.append(habit)
            
            print(f"Fetched {len(habits_data)} habits")
            return habits_data
        except Exception as e:
            print(f"Error fetching habits: {e}")
            return []

    # --- Prompt & Schedule Processing Methods ---

    def _build_world_prompt(self, rules, calendar_events, tasks, habits):
        """Compact world prompt for Harmonious Day scheduling (minimal tokens)."""
    
        now = datetime.datetime.now()
        now_str = now.strftime("%Y-%m-%d %H:%M")
        today_date = now.date()
        tomorrow_date = today_date + datetime.timedelta(days=1)
    
        # header + window
        prompt_lines = []
        prompt_lines.append(f"SCHEDULE REQUEST")
        prompt_lines.append(f"NOW: {now_str}")
        prompt_lines.append(f"SCHEDULE_WINDOW: {now_str} -> {tomorrow_date} 23:59")
        prompt_lines.append(f"SKIP_BEFORE: {now.strftime('%H:%M')}")  # do not schedule earlier today
        prompt_lines.append("") 
    
        # phases one-line
        phase_parts = []
        for p in rules.get("phases", []):
            phase_parts.append(f"{p['name'].replace('🌳 ','').split()[0]}:{p['start']}-{p['end']}")
        prompt_lines.append("PHASES: " + " | ".join(phase_parts))
    
        # anchors one-line list
        anchors = [f"{a['time']}:{a['name']}" for a in rules.get("anchors", [])]
        prompt_lines.append("ANCHORS: " + " | ".join(anchors) if anchors else "ANCHORS: none")
        prompt_lines.append("")
    
        # calendar events (compact lines)
        prompt_lines.append("CALENDAR_EVENTS: (summary|start|end)")
        if calendar_events:
            for e in calendar_events:
                prompt_lines.append(f"{e.get('summary','-')}|{e.get('start')}|{e.get('end')}")
        else:
            prompt_lines.append("NONE")
        prompt_lines.append("")
    
        # tasks: compact pipe entries prioritized by priority
        prompt_lines.append("TASKS: (title|priority|effort_h|total_remain_h|deadline|days_left|h_per_day|is_subtask|parent|notes)")
        if tasks:
            by_priority = defaultdict(list)
            for t in tasks:
                by_priority[t['priority']].append(t)
            for pr in sorted(by_priority.keys()):  # T1, T2, ...
                for t in by_priority[pr]:
                    notes = t.get("notes") or ""  # <-- default to empty string
                    # clean up any problematic characters
                    notes_clean = notes.replace("\n", " ").replace("|", "/").strip()
                    title_clean = t.get("title","").replace("|","/").strip()
                    parent_clean = str(t.get("parent_title") or "").replace("|","/").strip()
                    
                    line = "|".join([
                        title_clean,
                        pr,
                        f"{t.get('effort_hours',0):.1f}",
                        f"{t.get('total_remaining_effort',0):.1f}",
                        t.get("deadline_str","N/A"),
                        f"{t.get('days_until_deadline',0):.1f}",
                        f"{t.get('hours_per_day_needed',0):.1f}",
                        "1" if t.get("is_subtask") else "0",
                        parent_clean,
                        notes_clean
                    ])
                    prompt_lines.append(line)
        else:
            prompt_lines.append("NONE")
        prompt_lines.append("")
    
        # habits compact
        prompt_lines.append("HABITS: (title|mins_ideal|frequency|ideal_phase)")
        if habits:
            for h in habits:
                prompt_lines.append("|".join([
                    h.get("title","").replace("|","/"),
                    str(h.get("duration_min","")),
                    str(h.get("frequency","")),
                    str(h.get("ideal_phase",""))
                ]))
        else:
            prompt_lines.append("NONE")
        prompt_lines.append("")
    
        # constraints (explicit, short)
        prompt_lines.append("CONSTRAINTS:")
        prompt_lines.append("- Keep the time of Calendar Events free, never schedule anything over them, not even the anchors. ")
        prompt_lines.append("- Schedule as many tasks as capacity allows; only then consider habits.")
        prompt_lines.append("- Realistic focused work per day: 6-12h. 8 hours of demanding tasks is ideal.")
        prompt_lines.append("- Habits come last, and skipping a habit is not a problem.")
        prompt_lines.append("")
    
        # output schema required (exact)
        prompt_lines.append("OUTPUT_JSON: exact format below")
        prompt_lines.append('{"schedule_entries":[{"title":"...","start_time":"HH:MM","end_time":"HH:MM","phase":"Wood|Fire|Earth|Metal|Water","date":"today|tomorrow"}]}')
    
        return "\n".join(prompt_lines)


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
    
    
    