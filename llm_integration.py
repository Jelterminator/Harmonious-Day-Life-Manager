# File: llm_integration.py
# Optimized for OpenAI gpt-oss-20b on Groq
# Mobile consumer build target model

# -*- coding: utf-8 -*-

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import time
import datetime
import re
from collections import defaultdict
import sys
from pathlib import Path

# Add parent directory to path to import from main
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables
load_dotenv()

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT_FILE = Path("system_prompt.txt")

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

# ==================== PRIMARY MODEL: gpt-oss-20b ====================
# OpenAI's compact MoE model (20B params, 3.6B active)
# Optimized for:
# - Consumer/single-GPU deployment
# - 1000 T/sec throughput on Groq
# - Reasoning-enabled with configurable effort
# - 128K context window
# - Cost-efficient: $0.10 input / $0.50 output per 1M tokens
# - Apache 2.0 licensed (can ship on mobile consumer build)
# ===================================================================

MODEL_CONFIG = {
    "id": "openai/gpt-oss-20b",
    "name": "GPT-OSS 20B",
    "speed_tps": 1000,
    "context_window": 131072,
    "description": "OpenAI gpt-oss-20b - Consumer-deployable reasoning model"
}

# Reasoning effort levels: 'low', 'medium', 'high'
# For scheduling: use 'low' for speed, 'medium' for accuracy
REASONING_EFFORT = 'medium'

def get_groq_api_key():
    """Retrieve the Groq API key from environment variables."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY not set in environment.")
        print("""
How to get a FREE Groq API key:
1. Visit https://console.groq.com/
2. Sign up (no credit card required)
3. Create an API key
4. Set it: export GROQ_API_KEY='your-key-here'
""")
        return None
    return api_key


def load_system_prompt():
    """Load the system prompt from the external text file."""
    if not SYSTEM_PROMPT_FILE.exists():
        print(f"ERROR: Missing {SYSTEM_PROMPT_FILE}")
        return None
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def _normalize_schedule_data(data):
    """Normalize phase and date capitalization."""
    phase_map = {'wood': 'Wood', 'fire': 'Fire', 'earth': 'Earth', 'metal': 'Metal', 'water': 'Water'}
    
    valid_entries = []
    for entry in data.get("schedule_entries", []):
        # Check required fields
        if not all(k in entry for k in ["title", "start_time", "end_time", "phase", "date"]):
            continue
        # Normalize
        entry["phase"] = phase_map.get(entry["phase"].lower(), entry["phase"])
        entry["date"] = entry["date"].lower()
        valid_entries.append(entry)
    
    data["schedule_entries"] = valid_entries
    return data


def _extract_json(llm_text: str) -> dict | None:
    """
    Extract the LAST valid JSON object from the text.
    Handles:
        - escaped JSON inside quotes
        - double-encoded JSON
        - reasoning output with stray braces
        - Groq OSS models that embed huge reasoning dumps
    """

    import json
    import re

    if not llm_text:
        return None

    # STEP 1 - Extract only the *last* {...} block
    json_candidates = list(re.finditer(r'\{[\s\S]*\}', llm_text))
    if not json_candidates:
        return None

    last_block = json_candidates[-1].group(0)

    # STEP 2 - Try parsing it directly
    try:
        return json.loads(last_block)
    except:
        pass

    # STEP 3 - Unescape if it is inside a string
    try:
        unescaped = bytes(last_block, "utf-8").decode("unicode_escape")
        return json.loads(unescaped)
    except:
        pass

    # STEP 4 - Sometimes the JSON is wrapped in quotes
    stripped = last_block.strip()
    if (stripped.startswith('"') and stripped.endswith('"')) or \
       (stripped.startswith("'") and stripped.endswith("'")):
        try:
            inner = stripped[1:-1]
            return json.loads(inner)
        except:
            pass

    # STEP 5 - Final attempt: unescape + strip quotes
    try:
        stripped = stripped.strip('"').strip("'")
        unescaped = stripped.encode("utf-8").decode("unicode_escape")
        return json.loads(unescaped)
    except:
        return None

def call_groq_llm(system_prompt, world_prompt, model_config=MODEL_CONFIG, reasoning_effort=REASONING_EFFORT):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    # Enhanced payload with JSON mode
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": 0,
        "max_completion_tokens": 32768,
        "top_p": 1,
        "reasoning_effort": reasoning_effort,
        "response_format": {"type": "json_object"},  # Force JSON mode
        "stop": None
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    
        data = response.json()
        
        if "choices" not in data or not data["choices"]:
            raise ValueError("Groq API returned no choices.")
    
        msg = data["choices"][0]["message"]
    
        content = msg.get("content")
        reasoning = msg.get("reasoning")
        
        # Collect raw candidates for debugging
        raw_candidates = [
            content,
            reasoning,
            data["choices"][0].get("message", {}).get("content"),
            data["choices"][0].get("message", {}).get("reasoning"),
        ]
        
        print("\n--- DEBUG: Raw candidates ---")
        for i, candidate in enumerate(raw_candidates, 1):
            if candidate:
                preview = str(candidate)[:200] + "..." if len(str(candidate)) > 200 else str(candidate)
                print(f"Candidate {i} preview: {preview}")
    
        final_output = None
        
        for candidate in raw_candidates:
            if candidate and str(candidate).strip():
                final_output = str(candidate).strip()
                break
        
        if final_output is None:
            print("\n--- DEBUG: No valid candidate found ---")
            return {
                "status": "fail",
                "message": "Model returned empty content and reasoning.",
                "raw": data
            }
        
        # STEP 1: Parse JSON
        extracted_json = _extract_json(final_output)
        
        if not extracted_json:
            print("\n--- DEBUG: Failed to extract valid JSON ---")
            print(f"Raw output:\n{final_output[:1000]}")
            return {
                "status": "fail",
                "message": "Could not parse JSON from model output",
                "raw": data
            }
        
        # STEP 2: Normalize and Fix data (timestamps, capitalization, etc.)
        # This now uses the _normalize_schedule_data and _fix_timestamp helpers
        
        # First, fix timestamps and filter bad entries
        if "schedule_entries" in extracted_json:
            fixed_entries = []
            for entry in extracted_json.get("schedule_entries", []):
                # Validate required fields
                if not all(k in entry for k in ["title", "start_time", "end_time", "phase", "date"]):
                    print(f"Warning: Skipping entry missing required fields: {entry.get('title', 'Unknown')}")
                    continue
                
                # Fix malformed timestamps
                entry["start_time"] = _fix_timestamp(entry["start_time"])
                entry["end_time"] = _fix_timestamp(entry["end_time"])
                
                fixed_entries.append(entry)
            
            extracted_json["schedule_entries"] = fixed_entries
            print(f"\n--- DEBUG: Validated and fixed {len(fixed_entries)} schedule entries ---")
        
        # Now, normalize phase/date capitalization
        # This activates the previously unused _normalize_schedule_data function
        normalized_data = _normalize_schedule_data(extracted_json)
        print(f"--- DEBUG: Normalized {len(normalized_data.get('schedule_entries', []))} entries ---")
        
        return {
            "status": "success",
            "output": normalized_data, # Return the fully cleaned data
            "raw": data
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Network error calling Groq LLM: {e}")
        return {"status": "fail", "message": str(e), "raw": None}
    
    except ValueError as e:
        print(f"Invalid response from Groq LLM: {e}")
        return {"status": "fail", "message": str(e), "raw": data}
    
    except Exception as e:
        print(f"Unexpected error in call_groq_llm: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e), "raw": data}


def _fix_timestamp(timestamp_str):
    """
    Fix malformed timestamps returned by the AI.
    Converts various formats to ISO format.
    """
    import re
    
    timestamp_str = str(timestamp_str).strip()
    
    # Already in correct ISO format with timezone
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}', timestamp_str):
        return timestamp_str
    
    # ISO format without timezone: "2025-11-17T18:25:00"
    if re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', timestamp_str):
        return timestamp_str
    
    # Simple time format "18:25:00" or "18:25" (no date)
    if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', timestamp_str):
        return timestamp_str
    
    # Space-separated: "2025-11-17 18:25:00" or "2025-11-17 18:25" or "2025-11-17 18"
    match = re.match(r'(\d{4}-\d{2}-\d{2})\s+(\d{1,2})(?::(\d{2}))?(?::(\d{2}))?', timestamp_str)
    if match:
        date_part = match.group(1)
        hour = match.group(2).zfill(2)
        minute = match.group(3).zfill(2) if match.group(3) else "00"
        second = match.group(4).zfill(2) if match.group(4) else "00"
        return f"{date_part}T{hour}:{minute}:{second}"
    
    # If we can't parse it, return as-is
    print(f"Warning: Could not parse timestamp '{timestamp_str}'")
    return timestamp_str


def get_phase_by_time(dt_obj):
    """
    Determine the Wu Xing phase from a datetime object.
    Uses the same logic as defined in config.json and system_prompt.txt
    """
    if isinstance(dt_obj, str):
        import datetime
        import pytz
        # Parse string to datetime
        if 'T' in dt_obj:
            dt_obj = datetime.datetime.fromisoformat(dt_obj.replace('Z', '+00:00'))
        else:
            # Assume it's just time
            parts = dt_obj.split(':')
            dt_obj = datetime.datetime.now().replace(
                hour=int(parts[0]), 
                minute=int(parts[1]) if len(parts) > 1 else 0
            )
    
    hour = dt_obj.hour
    minute = dt_obj.minute
    time_in_minutes = hour * 60 + minute
    
    # Phase boundaries (in minutes from midnight)
    # WOOD: 05:30 - 09:00 (330 - 540)
    # FIRE: 09:00 - 13:00 (540 - 780)
    # EARTH: 13:00 - 15:00 (780 - 900)
    # METAL: 15:00 - 18:00 (900 - 1080)
    # WATER: 18:00 - 21:45 (1080 - 1305), and also 21:45 - 05:30 (1305+ and 0-330)
    
    if 330 <= time_in_minutes < 540:
        return "WOOD"
    elif 540 <= time_in_minutes < 780:
        return "FIRE"
    elif 780 <= time_in_minutes < 900:
        return "EARTH"
    elif 900 <= time_in_minutes < 1080:
        return "METAL"
    else:  # WATER phase covers 18:00-21:45 and 21:45-05:30
        return "WATER"


def pretty_print_schedule(schedule_data, calendar_events):
    """
    Print a readable version of the schedule, showing both generated entries
    and fixed calendar events, sorted by time and grouped by phase.
    """
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("No schedule data to display.")
        return

    import datetime
    from collections import defaultdict
    
    # Define today, stripping time information for comparison
    local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    today_date = datetime.datetime.now(local_tz).date()
    tomorrow_date = today_date + datetime.timedelta(days=1)
    
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
            "phase": entry.get("phase", "Unknown"),
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
            
        # Determine phase from time (assuming get_phase_by_time accepts a datetime object)
        try:
            # NOTE: Assuming 'get_phase_by_time' is defined elsewhere and works with datetime
            phase = get_phase_by_time(start_dt) 
        except NameError:
            phase = "Unknown"
        
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
    print("      GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)
    
    # Print schedules
    print_day_schedule(today_entries, "TODAY")
    print_day_schedule(tomorrow_entries, "TOMORROW")
    
    # Print summary
    print("\n" + "="*60)
    print(f"Total Entries: {len(all_entries)}")
    print(f"Generated: {len(schedule_data.get('schedule_entries', []))} | Fixed Calendar Events: {len(calendar_events)}")
    print("="*60 + "\n")