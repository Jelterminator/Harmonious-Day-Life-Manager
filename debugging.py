import datetime
import json
from collections import defaultdict
import os

# --- MOCK HELPER FUNCTION (Assumes your rules define these rough phases) ---

def get_phase_by_time(dt_obj):
    """Mocks the function that determines the phase based on a datetime object's time."""
    hour = dt_obj.hour
    if 6 <= hour < 10:
        return "Wood"
    elif 10 <= hour < 14:
        return "Fire"
    elif 14 <= hour < 18:
        return "Earth"
    elif 18 <= hour < 22:
        return "Metal"
    else:
        return "Water"

# --- CORE FUNCTION TO BE TESTED (The corrected version) ---

def pretty_print_schedule(schedule_data, calendar_events):
    """
    Print a readable version of the schedule, showing both generated entries
    and fixed calendar events, sorted by time and grouped by phase.
    """
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("No schedule data to display.")
        return

    # Define today, stripping time information for comparison
    # Use system's local time zone for comparison
    local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    today_date = datetime.datetime.now(local_tz).date()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    
    print(f"\n[DEBUGGER] Current 'Today' Date: {today_date.isoformat()}")
    print(f"[DEBUGGER] Current 'Tomorrow' Date: {tomorrow_date.isoformat()}\n")

    # Helper to safely convert an ISO string (with or without offset) to a local datetime object
    def safe_iso_to_datetime(iso_str):
        if not iso_str:
            return None
        # Handle 'Z' and ensure timezone info is present
        iso_str = iso_str.replace('Z', '+00:00')
        try:
            dt = datetime.datetime.fromisoformat(iso_str)
            if dt.tzinfo is None:
                # Assume local if no timezone provided (common for LLM output)
                return dt.replace(tzinfo=local_tz)
            # Convert to local timezone for consistent comparison
            return dt.astimezone(local_tz)
        except ValueError:
            return None

    # Helper to convert various time formats to HH:MM
    def format_time(time_str):
        dt = safe_iso_to_datetime(time_str)
        if dt:
            return dt.strftime('%H:%M')
        try:
            # Fallback for time-only strings like "18:44"
            parts = time_str.split(':')
            if len(parts) >= 2:
                return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}"
        except:
            pass
        return time_str

    # Build a combined list of all entries
    all_entries = []
    
    # 1. Process Generated Entries
    for entry in schedule_data.get("schedule_entries", []):
        start_dt = safe_iso_to_datetime(entry.get("start_time"))
        
        if not start_dt:
            print(f"Warning: Skipping generated entry due to bad start time: {entry.get('title')}")
            continue

        entry_date = start_dt.date()

        if entry_date == today_date:
            date_key = "today"
        elif entry_date == tomorrow_date:
            date_key = "tomorrow"
        else:
            # Skip if it's not today or tomorrow
            continue

        all_entries.append({
            "title": entry.get("title", "Unknown"),
            "start_time": entry.get("start_time", ""),
            "end_time": entry.get("end_time", ""),
            "phase": get_phase_by_time(start_dt), # Use helper for phase
            "date_key": date_key, # Use this for grouping
            "is_fixed": False,
            "sort_dt": start_dt # Use datetime object for sorting
        })
    
    # 2. Process Fixed Calendar Events
    for event in calendar_events:
        start_str = event.get("start", "")
        
        start_dt = safe_iso_to_datetime(start_str)
        if not start_dt:
            print(f"Warning: Could not process fixed event date for '{event.get('summary', 'Unknown')}'")
            continue
            
        event_date = start_dt.date()
        
        if event_date == today_date:
            date_key = "today"
        elif event_date == tomorrow_date:
            date_key = "tomorrow"
        else:
            continue
            
        phase = get_phase_by_time(start_dt) 
        
        all_entries.append({
            "title": f"**FIXED**: {event.get('summary', 'Unknown')}",
            "start_time": start_str,
            "end_time": event.get("end", ""),
            "phase": phase,
            "date_key": date_key, # Use this for grouping
            "is_fixed": True,
            "sort_dt": start_dt # Use datetime object for sorting
        })
            
    # Sort entries by date then time using the datetime object
    all_entries.sort(key=lambda e: (0 if e["date_key"] == "today" else 1, e["sort_dt"]))
    
    # Group by today/tomorrow
    today_entries = [e for e in all_entries if e["date_key"] == "today"]
    tomorrow_entries = [e for e in all_entries if e["date_key"] == "tomorrow"]
    
    # Print function
    def print_day_schedule(entries, day_label):
        print(f"\n {day_label}:")
        print("-" * 60)
        
        if not entries:
            print("  No entries scheduled")
            return
            
        # Group by phase
        phase_groups = defaultdict(list)
        for entry in entries:
            # Ensure phase is capitalized for grouping consistency
            phase = entry["phase"].upper() 
            phase_groups[phase].append(entry)
        
        # Print in phase order
        phase_order = ["WOOD", "FIRE", "EARTH", "METAL", "WATER"]
        for phase in phase_order:
            if phase in phase_groups:
                print(f"\n{phase} PHASE:")
                for entry in phase_groups[phase]:
                    start_fmt = format_time(entry["start_time"])
                    end_fmt = format_time(entry["end_time"])
                    title = entry["title"]
                    marker = " [FIXED]" if entry["is_fixed"] else ""
                    print(f"  {start_fmt} - {end_fmt}: {title}{marker}")

    # Print header
    print("\n" + "="*60)
    print("      GENERATED HARMONIOUS DAY SCHEDULE (MOCK DATA)")
    print("="*60)
    
    # Print schedules
    print_day_schedule(today_entries, "TODAY")
    print_day_schedule(tomorrow_entries, "TOMORROW")
    
    # Print summary
    print("\n" + "="*60)
    print(f"Total Entries: {len(all_entries)}")
    print(f"Generated: {len(schedule_data.get('schedule_entries', []))} | Fixed Calendar Events: {len(calendar_events)}")
    print("="*60 + "\n")


# --- MOCK DATA SETUP ---

# Use 2025-11-17 as the base date for consistent testing
today = datetime.date.today().isoformat()
tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()


mock_schedule_data = {
  "schedule_entries": [
    {
      "title": "Reading (Water Phase)",
      "start_time": "2025-11-17T19:21:00",
      "end_time": "2025-11-17T20:51:00",
      "phase": "Water",
      "date": "2025-11-17"
    },
    {
      "title": "Meditation (Water Phase)",
      "start_time": "2025-11-17T20:51:00",
      "end_time": "2025-11-17T21:06:00",
      "phase": "Water",
      "date": "2025-11-17"
    },
    {
      "title": "Fajr",
      "start_time": "2025-11-18T05:30:00",
      "end_time": "2025-11-18T05:40:00",
      "phase": "Wood",
      "date": "2025-11-18"
    },
    {
      "title": "Herschrijf: Tegen willens en wetens",
      "start_time": "2025-11-18T05:40:00",
      "end_time": "2025-11-18T06:40:00",
      "phase": "Wood",
      "date": "2025-11-18"
    },
    {
      "title": "Herschrijf: Denken als een wiskundige",
      "start_time": "2025-11-18T06:40:00",
      "end_time": "2025-11-18T07:40:00",
      "phase": "Wood",
      "date": "2025-11-18"
    },
    {
      "title": "Herschrijf: Denken als een natuurkundige",
      "start_time": "2025-11-18T07:40:00",
      "end_time": "2025-11-18T08:40:00",
      "phase": "Wood",
      "date": "2025-11-18"
    },
    {
      "title": "Stretches",
      "start_time": "2025-11-18T08:40:00",
      "end_time": "2025-11-18T09:00:00",
      "phase": "Wood",
      "date": "2025-11-18"
    },
    {
      "title": "Illustrate p2-3 Lege bladzij/Titel+Auteur",
      "start_time": "2025-11-18T10:00:00",
      "end_time": "2025-11-18T12:00:00",
      "phase": "Fire",
      "date": "2025-11-18"
    },
    {
      "title": "Zuhr",
      "start_time": "2025-11-18T13:00:00",
      "end_time": "2025-11-18T13:20:00",
      "phase": "Earth",
      "date": "2025-11-18"
    },
    {
      "title": "Translate Worm & Vlieg",
      "start_time": "2025-11-18T13:20:00",
      "end_time": "2025-11-18T14:20:00",
      "phase": "Earth",
      "date": "2025-11-18"
    },
    {
      "title": "Translate Vlinder & Bidsprinkhaan (1st half)",
      "start_time": "2025-11-18T14:20:00",
      "end_time": "2025-11-18T14:50:00",
      "phase": "Earth",
      "date": "2025-11-18"
    },
    {
      "title": "Asr",
      "start_time": "2025-11-18T15:00:00",
      "end_time": "2025-11-18T15:20:00",
      "phase": "Metal",
      "date": "2025-11-18"
    },
    {
      "title": "Translate Vlinder & Bidsprinkhaan (2nd half)",
      "start_time": "2025-11-18T15:20:00",
      "end_time": "2025-11-18T15:50:00",
      "phase": "Metal",
      "date": "2025-11-18"
    },
    {
      "title": "Maghrib",
      "start_time": "2025-11-18T18:00:00",
      "end_time": "2025-11-18T18:15:00",
      "phase": "Water",
      "date": "2025-11-18"
    },
    {
      "title": "L1-2: Read notes on Einstein model",
      "start_time": "2025-11-18T18:15:00",
      "end_time": "2025-11-18T20:15:00",
      "phase": "Water",
      "date": "2025-11-18"
    },
    {
      "title": "Meditation (Water Phase)",
      "start_time": "2025-11-18T20:15:00",
      "end_time": "2025-11-18T20:45:00",
      "phase": "Water",
      "date": "2025-11-18"
    },
    {
      "title": "Journaling",
      "start_time": "2025-11-18T20:45:00",
      "end_time": "2025-11-18T21:00:00",
      "phase": "Water",
      "date": "2025-11-18"
    },
    {
      "title": "Isha",
      "start_time": "2025-11-18T21:00:00",
      "end_time": "2025-11-18T21:20:00",
      "phase": "Water",
      "date": "2025-11-18"
    }
  ]
}

mock_calendar_events = [
    # Fixed event TODAY (should appear under TODAY)
    {
        "summary": "Gym Session with John",
        "start": f"{today}T17:00:00-05:00", # Example with different timezone offset
        "end": f"{today}T18:00:00-05:00", 
    },
    # Fixed events TOMORROW (should appear under TOMORROW)
    {
        "summary": "Hallo language assessment from Invisible",
        "start": f"{tomorrow}T09:00:00",
        "end": f"{tomorrow}T10:00:00",
    },
    {
        "summary": "EM Innovation Academy",
        "start": f"{tomorrow}T16:00:00",
        "end": f"{tomorrow}T18:00:00",
    },
]

# --- EXECUTION ---

if __name__ == "__main__":
    pretty_print_schedule(mock_schedule_data, mock_calendar_events)