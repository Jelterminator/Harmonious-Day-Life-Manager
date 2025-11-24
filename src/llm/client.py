# File: src/llm/client.py
"""
LLM integration module for Harmonious Day.
Handles communication with Groq API and schedule generation.
"""

import json
import requests
import datetime
import re
from typing import Dict, Any, Optional, List
from collections import defaultdict
import pytz

from src.core.config_manager import Config
from src.utils.logger import setup_logger
# New imports for type-safe models
from src.models.models import ScheduleEntry, CalendarEvent, Phase, parse_iso_datetime, schedule_entry_from_dict 

logger = setup_logger(__name__)


def get_groq_api_key() -> Optional[str]:
    """
    Retrieve the Groq API key from configuration.
    
    Returns:
        API key string or None if not found
    """
    api_key = Config.GROQ_API_KEY
    
    if not api_key:
        logger.error("GROQ_API_KEY not set in environment")
        logger.error("""
How to get a FREE Groq API key:
1. Visit https://console.groq.com/
2. Sign up (no credit card required)
3. Create an API key
4. Add to .env file: GROQ_API_KEY='your-key-here'
""")
        return None
    
    logger.debug("Groq API key loaded successfully")
    return api_key


def load_system_prompt() -> Optional[str]:
    """
    Load the system prompt from the external text file.
    
    Returns:
        System prompt string or None if file not found
    """
    if not Config.SYSTEM_PROMPT_FILE.exists():
        logger.error(f"System prompt file not found: {Config.SYSTEM_PROMPT_FILE}")
        return None
    
    logger.debug(f"Loading system prompt from {Config.SYSTEM_PROMPT_FILE}")
    try:
        content = Config.SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
        logger.info(f"System prompt loaded ({len(content)} characters)")
        return content
    except Exception as e:
        logger.error(f"Error reading system prompt: {e}", exc_info=True)
        return None


def _normalize_schedule_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize phase and date capitalization in schedule data.
    
    Args:
        data: Raw schedule data dictionary from LLM
    
    Returns:
        Normalized schedule data dictionary
    """
    # Create a map to ensure phase is in ALL_CAPS for the Phase Enum
    phase_map = {p.value.lower(): p.value for p in Phase}
    
    valid_entries = []
    for entry in data.get("schedule_entries", []):
        # Check required fields (already checked in call_groq_llm, but good for safety)
        required_fields = ["title", "start_time", "end_time", "phase", "date"]
        if not all(k in entry for k in required_fields):
            logger.warning(f"Skipping entry missing required fields: {entry.get('title', 'Unknown')}")
            continue
        
        # Normalize phase
        original_phase = entry["phase"]
        # Map lowercased phase to the official ALL_CAPS enum value string
        entry["phase"] = phase_map.get(entry["phase"].lower(), original_phase.upper())
        if entry["phase"] != original_phase:
            logger.debug(f"Normalized phase '{original_phase}' -> '{entry['phase']}'")
        
        # Normalize date
        entry["date"] = entry["date"].lower()
        
        valid_entries.append(entry)
    
    logger.info(f"Normalized {len(valid_entries)} valid schedule entries")
    data["schedule_entries"] = valid_entries
    return data


def _extract_json(llm_text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the LAST valid JSON object from the text.
    
    Args:
        llm_text: Raw text response from LLM
    
    Returns:
        Parsed JSON dictionary or None if extraction fails
    """
    if not llm_text:
        logger.warning("Empty LLM text provided to _extract_json")
        return None
    
    logger.debug(f"Attempting to extract JSON from {len(llm_text)} character response")
    
    # STEP 1 - Extract only the *last* {...} block
    json_candidates = list(re.finditer(r'\{[\s\S]*\}', llm_text))
    if not json_candidates:
        logger.error("No JSON-like blocks found in LLM response")
        return None
    
    last_block = json_candidates[-1].group(0)
    logger.debug(f"Found {len(json_candidates)} JSON-like blocks, using last one")
    
    # STEP 2 - Try parsing it directly
    try:
        result = json.loads(last_block)
        logger.info("Successfully parsed JSON on first attempt")
        return result
    except json.JSONDecodeError:
        logger.debug("Direct JSON parsing failed, trying unescape")
    
    # STEP 3 - Unescape if it is inside a string
    try:
        unescaped = bytes(last_block, "utf-8").decode("unicode_escape")
        result = json.loads(unescaped)
        logger.info("Successfully parsed JSON after unescaping")
        return result
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.debug("Unescaped parsing failed, trying quote stripping")
    
    # STEP 4 - Sometimes the JSON is wrapped in quotes
    stripped = last_block.strip()
    if (stripped.startswith('"') and stripped.endswith('"')) or \
       (stripped.startswith("'") and stripped.endswith("'")):
        try:
            inner = stripped[1:-1]
            result = json.loads(inner)
            logger.info("Successfully parsed JSON after quote stripping")
            return result
        except json.JSONDecodeError:
            logger.debug("Quote-stripped parsing failed")
    
    # STEP 5 - Final attempt: unescape + strip quotes
    try:
        stripped = stripped.strip('"').strip("'")
        unescaped = stripped.encode("utf-8").decode("unicode_escape")
        result = json.loads(unescaped)
        logger.info("Successfully parsed JSON after full cleanup")
        return result
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error("All JSON extraction attempts failed")
    
    return None


def _fix_timestamp(timestamp_str: str) -> str:
    """
    Fix malformed timestamps returned by the AI.
    Converts various formats to ISO format.
    
    Args:
        timestamp_str: Raw timestamp string from LLM
    
    Returns:
        Normalized timestamp string in ISO format
    """
    timestamp_str = str(timestamp_str).strip()
    
    # Already in correct ISO format with timezone
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}', timestamp_str):
        return timestamp_str
    
    # ISO format without timezone: "2025-11-17T18:25:00"
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', timestamp_str):
        return timestamp_str + "+01:00"  # Add default timezone
    
    # Simple time format "18:25:00" or "18:25" (no date) - FIXED
    time_only_match = re.match(r'^(\d{1,2}):(\d{2})(?::(\d{2}))?$', timestamp_str)
    if time_only_match:
        # Use today's date as default for time-only entries
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        hour = time_only_match.group(1).zfill(2)
        minute = time_only_match.group(2).zfill(2)
        second = time_only_match.group(3).zfill(2) if time_only_match.group(3) else "00"
        fixed = f"{today}T{hour}:{minute}:{second}+01:00"
        logger.debug(f"Fixed time-only timestamp: '{timestamp_str}' -> '{fixed}'")
        return fixed
    
    # Space-separated: "2025-11-17 18:25:00" or "2025-11-17 18:25" or "2025-11-17 18"
    match = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?', timestamp_str)
    if match:
        date_part = match.group(1)
        hour = match.group(2).zfill(2)
        minute = match.group(3).zfill(2) if match.group(3) else "00"
        second = match.group(4).zfill(2) if match.group(4) else "00"
        fixed = f"{date_part}T{hour}:{minute}:{second}+01:00"
        logger.debug(f"Fixed space-separated timestamp: '{timestamp_str}' -> '{fixed}'")
        return fixed
    
    # If we can't parse it, return as-is but log a warning
    logger.warning(f"Could not parse timestamp '{timestamp_str}'")
    return timestamp_str


def call_groq_llm(
    system_prompt: str, 
    world_prompt: str, 
    model_id: str = Config.MODEL_ID,
    reasoning_effort: str = Config.REASONING_EFFORT
) -> Dict[str, Any]:
    """
    Call Groq LLM API to generate schedule.
    
    Args:
        system_prompt: System instructions for the LLM
        world_prompt: User prompt with scheduling constraints
        model_id: Model identifier to use
        reasoning_effort: Reasoning level ('low', 'medium', 'high')
    
    Returns:
        Dictionary with 'status' ('success' or 'fail') and 'output' (List[ScheduleEntry]) or 'message'
    """
    logger.info(f"Calling Groq LLM with model: {model_id}")
    logger.debug(f"System prompt: {len(system_prompt)} chars, World prompt: {len(world_prompt)} chars")
    
    headers = {
        "Authorization": f"Bearer {Config.GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": 0,
        "max_completion_tokens": Config.MAX_COMPLETION_TOKENS,
        "top_p": 1,
        "reasoning_effort": reasoning_effort,
        "response_format": {"type": "json_object"},
        "stop": None
    }
    
    try:
        logger.info("Sending request to Groq API...")
        response = requests.post(Config.GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        data = response.json()
        logger.debug(f"Received response from Groq API")
        
        if "choices" not in data or not data["choices"]:
            logger.error("Groq API returned no choices")
            return {"status": "fail", "message": "No choices in response", "raw": data}
        
        msg = data["choices"][0]["message"]
        content = msg.get("content")
        reasoning = msg.get("reasoning")
        
        # Collect raw candidates for debugging
        raw_candidates = [content, reasoning]
        
        logger.debug(f"Content length: {len(content) if content else 0}")
        logger.debug(f"Reasoning length: {len(reasoning) if reasoning else 0}")
        
        final_output = None
        for candidate in raw_candidates:
            if candidate and str(candidate).strip():
                final_output = str(candidate).strip()
                break
        
        if final_output is None:
            logger.error("Model returned empty content and reasoning")
            return {
                "status": "fail",
                "message": "Model returned empty content and reasoning.",
                "raw": data
            }
        
        # Extract JSON
        extracted_json = _extract_json(final_output)
        
        if not extracted_json:
            logger.error("Failed to extract valid JSON from model output")
            return {
                "status": "fail",
                "message": "Could not parse JSON from model output",
                "raw": data
            }
        
        # 1. Fix timestamps and preliminary validation
        # In call_groq_llm, after fixing timestamps but before creating ScheduleEntry:
        fixed_entries = []
        for entry in extracted_json.get("schedule_entries", []):
            # Validate required fields
            required = ["title", "start_time", "end_time", "phase", "date"]
            if not all(k in entry for k in required):
                logger.warning(f"Skipping entry missing fields: {entry.get('title', 'Unknown')}")
                continue
                
            # Fix timestamps
            entry["start_time"] = _fix_timestamp(entry["start_time"])
            entry["end_time"] = _fix_timestamp(entry["end_time"])
            
            # NEW: Validate that timestamps are parseable before proceeding
            try:
                start_parsed = parse_iso_datetime(entry["start_time"])
                end_parsed = parse_iso_datetime(entry["end_time"])
                
                if start_parsed is None or end_parsed is None:
                    logger.warning(f"Skipping entry with unparseable timestamps: {entry.get('title', 'Unknown')}")
                    logger.debug(f"Start: {entry['start_time']}, End: {entry['end_time']}")
                    continue
                    
                # Also validate that start_time < end_time
                if start_parsed >= end_parsed:
                    logger.warning(f"Skipping entry with invalid time range: {entry.get('title', 'Unknown')}")
                    logger.debug(f"Start: {start_parsed}, End: {end_parsed}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Skipping entry due to timestamp error: {e}")
                continue
            
            fixed_entries.append(entry)
        
        # Temporary debug - add this right after the timestamp fixing loop
        for i, entry in enumerate(fixed_entries):
            start_parsed = parse_iso_datetime(entry["start_time"])
            end_parsed = parse_iso_datetime(entry["end_time"])
            logger.debug(f"Entry {i}: {entry['title']}")
            logger.debug(f"  Raw start: {entry['start_time']} -> Parsed: {start_parsed}")
            logger.debug(f"  Raw end: {entry['end_time']} -> Parsed: {end_parsed}")    
        
        extracted_json["schedule_entries"] = fixed_entries
        logger.info(f"Validated and fixed {len(fixed_entries)} schedule entries")

        # 2. Normalize phase/date casing
        normalized_data = _normalize_schedule_data(extracted_json)
        
        # 3. Convert to ScheduleEntry models
        schedule_entries: List[ScheduleEntry] = []
        for entry_dict in normalized_data.get("schedule_entries", []):
            try:
                # Use the utility function to create the typed model
                entry_obj = schedule_entry_from_dict(entry_dict)
                schedule_entries.append(entry_obj)
            except Exception as e:
                logger.error(f"Failed to create ScheduleEntry from dict: {e}. Skipping entry: {entry_dict.get('title', 'Unknown')}", exc_info=True)
        
        logger.info("Schedule generation successful")
        return {
            "status": "success",
            "output": schedule_entries, # Returns List[ScheduleEntry]
            "raw": data
        }
    
    except requests.exceptions.Timeout:
        logger.error("Groq API request timed out")
        return {"status": "fail", "message": "Request timed out", "raw": None}
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error calling Groq LLM: {e}", exc_info=True)
        return {"status": "fail", "message": str(e), "raw": None}
    except ValueError as e:
        logger.error(f"Invalid response from Groq LLM: {e}", exc_info=True)
        return {"status": "fail", "message": str(e), "raw": None}
    except Exception as e:
        logger.error(f"Unexpected error in call_groq_llm: {e}", exc_info=True)
        return {"status": "error", "message": str(e), "raw": None}


def get_phase_by_time(dt_obj: Any) -> Phase:
    """
    Determine the Wu Xing phase from a datetime object or string.
    
    Args:
        dt_obj: Datetime object or time string (ISO or HH:MM).
    
    Returns:
        Phase enum (Phase.WOOD, Phase.FIRE, etc.)
    """
    if isinstance(dt_obj, str):
        # Parse string to datetime
        try:
            if 'T' in dt_obj:
                # Handle ISO format with date/time
                dt_obj = datetime.datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
            else:
                # Assume it's just time: HH:MM or HH:MM:SS
                time_parts = list(map(int, dt_obj.split(':')))
                # Create a placeholder datetime for the current day
                now = datetime.datetime.now()
                dt_obj = now.replace(
                    hour=time_parts[0], 
                    minute=time_parts[1] if len(time_parts) > 1 else 0,
                    second=time_parts[2] if len(time_parts) > 2 else 0,
                    microsecond=0
                )
        except Exception:
            # Fallback for unparseable string, assume current time to get a phase
            logger.warning(f"Could not parse time string '{dt_obj}' in get_phase_by_time. Using current time.")
            dt_obj = datetime.datetime.now()

    hour = dt_obj.hour
    minute = dt_obj.minute
    time_in_minutes = hour * 60 + minute
    
    # Phase boundaries (in minutes from midnight)
    if 330 <= time_in_minutes < 540:  # 05:30 - 09:00
        return Phase.WOOD
    elif 540 <= time_in_minutes < 780:  # 09:00 - 13:00
        return Phase.FIRE
    elif 780 <= time_in_minutes < 900:  # 13:00 - 15:00
        return Phase.EARTH
    elif 900 <= time_in_minutes < 1080:  # 15:00 - 18:00
        return Phase.METAL
    else:  # 18:00 - 05:30 (handles wrap-around)
        return Phase.WATER


def pretty_print_schedule(
    schedule_entries: List[ScheduleEntry], 
    calendar_events: List[CalendarEvent]
) -> None:
    """
    Print a readable version of the schedule.
    
    Shows both generated entries and fixed calendar events,
    sorted by time and grouped by phase.
    
    Args:
        schedule_entries: List of ScheduleEntry objects
        calendar_events: List of CalendarEvent objects
    """
    if not schedule_entries and not calendar_events:
        logger.warning("No schedule data to display")
        print("No schedule data to display.")
        return
    
    logger.info("Generating pretty-printed schedule")
    
    # Define today, stripping time information for comparison
    local_tz = pytz.timezone(Config.TARGET_TIMEZONE)
    now = datetime.datetime.now(local_tz)
    today_date = now.date()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    
    def format_time(dt_obj: datetime.datetime) -> str:
        """Convert datetime object to HH:MM format."""
        # Ensure the datetime object is localized to the target timezone for consistent output
        if dt_obj.tzinfo is not None and dt_obj.tzinfo.utcoffset(dt_obj) is not None:
             dt_obj = dt_obj.astimezone(local_tz)
        return dt_obj.strftime('%H:%M')
    
    # Build combined list of all entries
    all_entries = []
    
    # Process Generated Entries
    for entry in schedule_entries:
        start_dt = entry.start_time.astimezone(local_tz)
        
        entry_date = start_dt.date()
        if entry_date == today_date:
            date_key = "today"
        elif entry_date == tomorrow_date:
            date_key = "tomorrow"
        else:
            continue
        
        all_entries.append({
            "title": entry.title,
            "start_time": entry.start_time,
            "end_time": entry.end_time,
            "phase": entry.phase.value, # Use .value from Phase enum
            "date_key": date_key,
            "is_fixed": False,
            "sort_dt": start_dt
        })
    
    # Process Fixed Calendar Events
    for event in calendar_events:
        start_dt = event.start.astimezone(local_tz)
        
        event_date = start_dt.date()
        if event_date == today_date:
            date_key = "today"
        elif event_date == tomorrow_date:
            date_key = "tomorrow"
        else:
            continue
        
        # Get phase from utility and use its value
        phase = get_phase_by_time(start_dt).value 
        
        all_entries.append({
            "title": f"**FIXED**: {event.summary}",
            "start_time": event.start,
            "end_time": event.end,
            "phase": phase,
            "date_key": date_key,
            "is_fixed": True,
            "sort_dt": start_dt
        })
    
    # Sort entries
    all_entries.sort(key=lambda e: (0 if e["date_key"] == "today" else 1, e["sort_dt"]))
    
    # Group by today/tomorrow
    today_entries = [e for e in all_entries if e["date_key"] == "today"]
    tomorrow_entries = [e for e in all_entries if e["date_key"] == "tomorrow"]
    
    def print_day_schedule(entries: List[Dict[str, Any]], day_label: str) -> None:
        """Print schedule for one day."""
        print(f"\n {day_label}:")
        print("-" * 60)
        
        if not entries:
            print("  No entries scheduled")
            return
        
        # Group by phase
        phase_groups = defaultdict(list)
        for entry in entries:
            phase = entry["phase"].upper()
            phase_groups[phase].append(entry)
        
        # Print in phase order
        phase_order = [p.value for p in Phase]
        for phase in phase_order:
            if phase in phase_groups:
                print(f"\n{phase} PHASE:")
                for entry in phase_groups[phase]:
                    start_fmt = format_time(entry["start_time"])
                    end_fmt = format_time(entry["end_time"])
                    title = entry["title"]
                    # Clean up bold for pretty printing
                    title = title.replace('**', '') 
                    marker = " [FIXED]" if entry["is_fixed"] else ""
                    print(f"  {start_fmt} - {end_fmt}: {title}{marker}")
    
    # Print header
    print("\n" + "="*60)
    print("      GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)
    
    # Print schedules
    print_day_schedule(today_entries, f"TODAY ({today_date.strftime('%A, %B %d').upper()})")
    print_day_schedule(tomorrow_entries, f"TOMORROW ({tomorrow_date.strftime('%A, %B %d').upper()})")
    
    # Print summary
    print("\n" + "="*60)
    print(f"Total Entries: {len(all_entries)}")
    print(f"Generated: {len(schedule_entries)} | "
          f"Fixed Calendar Events: {len(calendar_events)}")
    print("="*60 + "\n")
    
    logger.info(f"Pretty-printed schedule with {len(all_entries)} total entries")


# Output schema for reference
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "schedule_entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "phase": {"type": "string"},
                    "date": {"type": "string"}
                },
                "required": ["title", "start_time", "end_time", "phase", "date"]
            }
        }
    },
    "required": ["schedule_entries"]
}