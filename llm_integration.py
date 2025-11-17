# File: llm_integration.py
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
import time
import datetime

# Load environment variables
load_dotenv()

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT_FILE = Path("system_prompt.txt")

# ==================== MODEL SELECTION (Nov 2025) ====================
# Based on actual Groq documentation for Structured Outputs support:
# https://console.groq.com/docs/structured-outputs#supported-models
#
# ONLY moonshotai/kimi-k2-instruct-0905 supports json_schema mode!
# All other models only support basic json_object mode.
#
# PRIMARY MODEL: moonshotai/kimi-k2-instruct-0905
# - 1T parameters MoE (32B activated)
# - 256K context window (largest on Groq)
# - Native JSON Schema support (ONLY MODEL WITH THIS)
# - Excellent for structured outputs and tool calling
# - Cost: $1.00/1M input, $3.00/1M output
# - Speed: 200+ tokens/sec
# - Recommended temp: 0.6 (from model docs)
#
# FALLBACK MODELS (JSON Object mode only):
# - llama-3.3-70b-versatile: Production model, good general purpose
# - llama-3.1-8b-instant: Fastest, cheapest, good for simple tasks
# ==================================================================

CURRENT_GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"
FALLBACK_MODEL = "llama-3.3-70b-versatile"

# JSON Schema for structured output (only works with Kimi K2)
SCHEDULE_SCHEMA = {
    "type": "object",
    "description": "A generated daily schedule based on the Harmonious Day principles.",
    "properties": {
        "schedule_entries": {
            "type": "array",
            "description": "A list of scheduled tasks, anchors, and habits for the planning window.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "A concise description of the scheduled activity (e.g., 'T3 Study: Hume', 'Reading (Water Phase)', or 'Fajr & Centering')."
                    },
                    "start_time": {
                        "type": "string",
                        "pattern": "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",
                        "description": "The start time in HH:MM 24-hour format.",
                        "example": "09:00"
                    },
                    "end_time": {
                        "type": "string",
                        "pattern": "^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$",
                        "description": "The end time in HH:MM 24-hour format. Must not be after 21:45.",
                        "example": "10:30"
                    },
                    "phase": {
                        "type": "string",
                        "enum": ["Wood", "Fire", "Earth", "Metal", "Water", "Sleep"],
                        "description": "The element phase the entry falls into."
                    },
                    "date": {
                        "type": "string",
                        "enum": ["today", "tomorrow"],
                        "description": "Indicates whether the entry is for the current day or the next day."
                    }
                },
                "required": ["title", "start_time", "end_time", "phase", "date"]
            }
        },
        "sleep_entry": {
            "type": "object",
            "description": "A single, optional entry to represent the Sleep period (21:45 to 05:30) if it falls within the schedule window. This entry MUST be omitted if the LLM cannot safely schedule it.",
            "properties": {
                "title": {"type": "string", "const": "Sleep"},
                "start_time": {"type": "string", "pattern": "^(21):[4-5][5-9]$", "example": "21:45"},
                "end_time": {"type": "string", "const": "05:30"},
                "phase": {"type": "string", "const": "Water"},
                "date": {"type": "string", "enum": ["today", "tomorrow"]}
            },
            "required": ["title", "start_time", "end_time", "phase", "date"]
        }
    },
    "required": ["schedule_entries"]
}


def get_groq_api_key():
    """Retrieve the Groq API key from environment variables."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("❌ ERROR: GROQ_API_KEY not set in environment.")
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
        print(f"❌ ERROR: Missing {SYSTEM_PROMPT_FILE}")
        return None
    return SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")


def call_groq_llm(
    world_prompt, 
    api_key, 
    system_prompt_path=SYSTEM_PROMPT_FILE, 
    groq_model=CURRENT_GROQ_MODEL,
    max_retries=3
):
    """
    Send the world prompt to Groq and return parsed JSON schedule.
    
    Args:
        world_prompt: The user prompt with scheduling data
        api_key: Groq API key
        system_prompt_path: Path to system prompt file
        groq_model: Model to use (default: kimi-k2-instruct-0905)
        max_retries: Number of retry attempts on failure
        
    Returns:
        dict: Parsed schedule data with all entries in 'schedule_entries', or None on failure.
    """
    
    # Load system prompt
    try:
        system_prompt = Path(system_prompt_path).read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"❌ ERROR: Could not read system prompt: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Determine model support for JSON Schema and build payload
    supports_schema = groq_model == "moonshotai/kimi-k2-instruct-0905"
    temp = 0.6 if supports_schema else 0.0 # Kimi K2 vs Llama
    
    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": temp,
        "max_tokens": 4096,
        "top_p": 0.95 if supports_schema else 1.0,
    }

    # Apply structured outputs configuration
    if supports_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "schedule_response",
                "schema": SCHEDULE_SCHEMA,
                "strict": True
            }
        }
    else:
        payload["response_format"] = {"type": "json_object"}

    # Retry logic for robustness
    for attempt in range(max_retries):
        try:
            mode = "JSON Schema" if supports_schema else "JSON Object"
            print(f"📡 Calling Groq API (attempt {attempt + 1}/{max_retries})...")
            print(f"   Model: {groq_model}")
            print(f"   Mode: {mode}")
            
            response = requests.post(
                GROQ_API_URL,
                headers=headers,
                json=payload,
                timeout=90
            )
            response.raise_for_status()

            result = response.json()
            
            # --- Error Checking and Fallback ---
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                print(f"❌ API Error: {error_msg}")
                
                if "does not support" in error_msg.lower() and attempt == 0:
                    print(f"⚠️ Switching to fallback model: {FALLBACK_MODEL}")
                    return call_groq_llm(
                        world_prompt, api_key, system_prompt_path, 
                        FALLBACK_MODEL, max_retries - 1
                    )
                continue

            # --- Success and Parsing ---
            content = result["choices"][0]["message"]["content"]
            schedule_data = json.loads(content)
            
            # --- Handle Sleep Entry and Final Structure ---
            if "schedule_entries" not in schedule_data or not isinstance(schedule_data["schedule_entries"], list):
                print("❌ ERROR: Generated JSON is missing or has incorrect 'schedule_entries' format.")
                continue

            # Check for and merge the optional sleep_entry into schedule_entries
            sleep_entry = schedule_data.pop("sleep_entry", None)
            if sleep_entry:
                schedule_data["schedule_entries"].append(sleep_entry)

            # --- Logging and Return ---
            usage = result.get("usage", {})
            entries_count = len(schedule_data['schedule_entries'])
            
            print(f"✅ Success!")
            print(f"   Entries: {entries_count}")
            print(f"   Tokens: {usage.get('total_tokens', 'N/A')} "
                  f"(in: {usage.get('prompt_tokens', 'N/A')}, "
                  f"out: {usage.get('completion_tokens', 'N/A')})")
            
            return schedule_data

        except requests.exceptions.RequestException as e:
            print(f"❌ Network error (attempt {attempt + 1}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Response: {e.response.text[:500]}")
            
            if attempt == max_retries - 1 and groq_model != FALLBACK_MODEL:
                print(f"⚠️ Trying fallback model: {FALLBACK_MODEL}")
                return call_groq_llm(world_prompt, api_key, system_prompt_path, FALLBACK_MODEL, 1)
            
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"   Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"   Raw content: {content[:500]}...")
            
            # Attempt to recover JSON from markdown block
            try:
                if "```json" in content:
                    json_start = content.find("```json") + 7
                    json_end = content.find("```", json_start)
                    content = content[json_start:json_end].strip()
                    # Re-run the main success logic on recovered content
                    schedule_data = json.loads(content)
                    print("✅ Recovered JSON from markdown")
                    
                    # Merge sleep entry if present
                    sleep_entry = schedule_data.pop("sleep_entry", None)
                    if sleep_entry:
                        schedule_data["schedule_entries"].append(sleep_entry)
                        
                    return schedule_data
            except Exception as recover_e:
                print(f"❌ Recovery failed: {recover_e}")
                pass
                
        except Exception as e:
            print(f"❌ Unexpected error: {type(e).__name__}: {e}")
            
    print("❌ All retry attempts exhausted")
    return None


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
    elif 1080 <= hour < 1305 or hour < 330 or hour >= 1305: # Covers sleep/pre-Fajr
        return "Water"
    else:
        return "Unknown" # Should not happen if boundaries are set right

def pretty_print_schedule(schedule_data: Dict[str, List[Dict[str, str]]], calendar_events: List[Dict[str, str]]):
    """
    Print a readable version of the schedule, integrating fixed calendar events 
    and generated schedule entries, sorted by time and grouped by phase.
    """
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("⚠️ No schedule data to display.")
        return

    # --- 1. Prepare and Standardize Data ---
    
    # Use today's date for reference
    today_date = datetime.date.today()
    
    # Convert fixed calendar events into the same format as schedule_entries
    all_entries: List[Dict[str, Any]] = schedule_data["schedule_entries"]
    
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
                continue # Skip events outside today/tomorrow
                
            # Determine phase
            phase_name = get_phase_by_time(start_dt)
            
            all_entries.append({
                "title": f"**FIXED**: {event['summary']}",
                "start_time": start_dt.strftime("%H:%M"),
                "end_time": datetime.datetime.fromisoformat(event["end"].replace('Z', '+00:00')).strftime("%H:%M"),
                "phase": phase_name,
                "date": date_key,
                "is_fixed": True # Add a flag for sorting/identification
            })
        except Exception as e:
            # Handle potential parsing errors if dates/times are not standard
            print(f"⚠️ Skipping calendar event due to parsing error: {event.get('summary', 'Unknown Event')}. Error: {e}")

    # --- 2. Sort All Entries ---
    
    # Define a custom sort key: (date index, start time string)
    def sort_key(e):
        date_index = 0 if e["date"] == "today" else 1
        return (date_index, e["start_time"])

    all_entries.sort(key=sort_key)
    
    # --- 3. Group and Print ---
    
    print("\n" + "="*60)
    print("       🌿 GENERATED HARMONIOUS DAY SCHEDULE (Fixed Events Included)")
    print("="*60)

    # Separate by date for final printing
    today_combined = [e for e in all_entries if e["date"] == "today"]
    tomorrow_combined = [e for e in all_entries if e["date"] == "tomorrow"]
    
    phase_order = ["Wood", "Fire", "Earth", "Metal", "Water"]

    def print_schedule_block(entries: List[Dict[str, Any]], day_label: str):
        if not entries:
            return

        print(f"\n📅 {day_label}:")
        print("-" * 60)
        
        # Group entries by phase
        day_phases = {}
        for entry in entries:
            phase = entry.get("phase", "Unknown")
            day_phases.setdefault(phase, []).append(entry)
        
        # Print grouped entries in phase order
        for phase in phase_order:
            if phase in day_phases:
                print(f"\n{phase.upper()} PHASE:")
                # Entries inside each phase are already sorted by time
                for e in day_phases[phase]:
                    # Determine styling based on fixed status
                    title_style = e['title']
                    
                    print(f"  {e['start_time']} - {e['end_time']}: {title_style}")

    # Print today's schedule
    print_schedule_block(today_combined, "TODAY")
    
    # Print tomorrow's schedule
    print_schedule_block(tomorrow_combined, "TOMORROW")
    
    # --- 4. Final Summary ---
    total_generated = len(schedule_data["schedule_entries"])
    total_fixed = len(calendar_events)
    
    print("\n" + "="*60)
    print(f"Total Entries Displayed: {len(today_combined) + len(tomorrow_combined)}")
    print(f"Generated Entries: {total_generated} | Fixed Calendar Events: {total_fixed}")
    print("="*60 + "\n")