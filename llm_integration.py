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

def call_groq_llm(system_prompt, world_prompt, model_config=MODEL_CONFIG, reasoning_effort=REASONING_EFFORT, output_schema=OUTPUT_SCHEMA):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }

    # Payload as recommended by Groq docs
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
        "stop": None,
        # Force JSON Schema
        #"response_format": "json_schema",
        #"json_schema": output_schema,  # dict defining your schema
        #"strict": True                 # enforce strict adherence if supported
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
            print(f"Candidate {i}: {repr(candidate)}")
    
        final_output = None
        
        for candidate in raw_candidates:
            if candidate and str(candidate).strip():
                final_output = str(candidate).strip()
                print(f"\n--- DEBUG: Selected final_output ---\n{final_output}\n")
                break
        
        if final_output is None:
            print("\n--- DEBUG: No valid candidate found ---")
            return {
                "status": "fail",
                "message": "Model returned empty content and reasoning.",
                "raw": data
            }
        
        # Parse JSON (guaranteed to work)
        extracted_json = _extract_json(final_output)
        
        print("\n--- DEBUG: Extracted JSON ---")
        print(json.dumps(extracted_json, indent=2))
        
        return {
            "status": "success",
            "output": extracted_json,
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
        return {"status": "error", "message": str(e), "raw": data}



def get_phase_by_time(dt_obj: datetime.datetime) -> str:
    """Helper function to determine the Wu Xing phase from a datetime object."""
    hour = dt_obj.hour * 60 + dt_obj.minute
    
    # Define phase boundaries in minutes from midnight (00:00)
    # WOOD: 05:30 - 09:00 (330 - 540)
    # FIRE: 09:00 - 13:00 (540 - 780)
    # EARTH: 13:00 - 15:00 (780 - 900)
    # METAL: 15:00 - 18:00 (900 - 1080)
    # WATER: 18:00 - 21:45 (1080 - 1305)
    
    if 330 <= hour < 540:
        return "Wood"
    elif 540 <= hour < 780:
        return "Fire"
    elif 780 <= hour < 900:
        return "Earth"
    elif 900 <= hour < 1080:
        return "Metal"
    elif 1080 <= hour < 1305 or hour < 330 or hour >= 1305:
        return "Water"
    else:
        return "Unknown"


def pretty_print_schedule(schedule_data, calendar_events):
    """
    Print a readable version of the schedule, integrating fixed calendar events 
    and generated schedule entries, sorted by time and grouped by phase.
    """
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("No schedule data to display.")
        return

    # Use today's date for reference
    today_date = datetime.date.today()
    
    # Convert fixed calendar events into the same format as schedule_entries
    all_entries = schedule_data["schedule_entries"]
    
    for event in calendar_events:
        try:
            # Parse start/end times from ISO format
            start_dt = datetime.datetime.fromisoformat(event["start"].replace('Z', '+00:00'))
            
            # Determine date key ('today' or 'tomorrow')
            event_date = start_dt.date()
            if event_date == today_date:
                date_key = "today"
            elif event_date == today_date + datetime.timedelta(days=1):
                date_key = "tomorrow"
            else:
                continue
                
            # Determine phase
            phase_name = get_phase_by_time(start_dt)
            
            all_entries.append({
                "title": f"**FIXED**: {event['summary']}",
                "start_time": start_dt.isoformat(),
                "end_time": datetime.datetime.fromisoformat(
                    event["end"].replace('Z', '+00:00')
                ).isoformat(),
                "phase": phase_name,
                "date": date_key,
                "is_fixed": True
            })
        except Exception as e:
            print(f"Skipping calendar event: {event.get('summary', 'Unknown')}. Error: {e}")

    # Sort all entries
    def sort_key(e):
        date_index = 0 if e["date"] == "today" else 1
        return (date_index, e["start_time"])

    all_entries.sort(key=sort_key)
    
    # Print
    print("\n" + "="*60)
    print("        GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)

    today_combined = [e for e in all_entries if e["date"] == "today"]
    tomorrow_combined = [e for e in all_entries if e["date"] == "tomorrow"]
    
    phase_order = ["Wood", "Fire", "Earth", "Metal", "Water"]

    def print_schedule_block(entries, day_label):
        if not entries:
            return

        print(f"\n {day_label}:")
        print("-" * 60)
        
        day_phases = {}
        for entry in entries:
            phase = entry.get("phase", "Unknown")
            day_phases.setdefault(phase, []).append(entry)
        
        for phase in phase_order:
            if phase in day_phases:
                print(f"\n{phase.upper()} PHASE:")
                for e in day_phases[phase]:
                    print(f"  {e['start_time']} - {e['end_time']}: {e['title']}")

    print_schedule_block(today_combined, "TODAY")
    print_schedule_block(tomorrow_combined, "TOMORROW")
    
    total_generated = len(schedule_data["schedule_entries"])
    total_fixed = len(calendar_events)
    
    print("\n" + "="*60)
    print(f"Total Entries: {len(today_combined) + len(tomorrow_combined)}")
    print(f"Generated: {total_generated} | Fixed Calendar Events: {total_fixed}")
    print("="*60 + "\n")