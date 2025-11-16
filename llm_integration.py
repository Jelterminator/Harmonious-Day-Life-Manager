import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Groq API endpoint (OpenAI-compatible)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT_FILE = Path("system_prompt.txt")
CURRENT_GROQ_MODEL = "moonshotai/kimi-k2-instruct-0905"  # Or "openai/gpt-oss-20b"


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

def call_groq_llm(world_prompt, api_key, system_prompt_path=SYSTEM_PROMPT_FILE, groq_model=CURRENT_GROQ_MODEL):
    """Send the world prompt to Groq and return parsed JSON schedule with robust error handling."""
    
    # Load system prompt text from file
    try:
        system_prompt = Path(system_prompt_path).read_text(encoding="utf-8").strip()
    except Exception as e:
        print(f"ERROR: Could not read system prompt from {system_prompt_path}: {e}")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": groq_model,  # Consider "llama-3.3-70b-versatile" for potentially better JSON adherence
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": 0.1,  # Lower for more deterministic JSON output
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}  # This enforces JSON mode
    }

    try:
        print("Sending request to Groq API with JSON mode enforced...")
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", 
                               headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        # Validate JSON structure
        schedule_data = json.loads(content)
        
        if "schedule_entries" not in schedule_data:
            print("ERROR: Missing 'schedule_entries' key in response")
            return None

        print(f"✓ Successfully parsed {len(schedule_data['schedule_entries'])} schedule entries")
        return schedule_data

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response details: {e.response.text}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON response: {e}")
        print(f"Raw content received: {content[:500]}...")
        return None

def pretty_print_schedule(schedule_data):
    """Print a readable version of the schedule with today/tomorrow separation."""
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("⚠️ No schedule data to display.")
        return

    print("\n" + "="*60)
    print("       🌿 GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)

    entries = schedule_data["schedule_entries"]
    
    # Separate entries by date
    today_entries = [entry for entry in entries if entry.get("date") == "today"]
    tomorrow_entries = [entry for entry in entries if entry.get("date") == "tomorrow"]
    
    phase_order = ["Wood", "Fire", "Earth", "Metal", "Water"]
    
    # Print today's schedule
    if today_entries:
        print(f"\n📅 TODAY:")
        print("-" * 60)
        
        today_phases = {}
        for entry in today_entries:
            today_phases.setdefault(entry.get("phase", "Unknown"), []).append(entry)
        
        for phase in phase_order:
            if phase in today_phases:
                print(f"\n{phase.upper()} PHASE:")
                for e in today_phases[phase]:
                    print(f"  {e['start_time']} - {e['end_time']}: {e['title']}")
    
    # Print tomorrow's schedule
    if tomorrow_entries:
        print(f"\n📅 TOMORROW:")
        print("-" *60)
        
        tomorrow_phases = {}
        for entry in tomorrow_entries:
            tomorrow_phases.setdefault(entry.get("phase", "Unknown"), []).append(entry)
        
        for phase in phase_order:
            if phase in tomorrow_phases:
                print(f"\n{phase.upper()} PHASE:")
                for e in tomorrow_phases[phase]:
                    print(f"  {e['start_time']} - {e['end_time']}: {e['title']}")

    print("\n" + "="*60)
    print(f"Total entries: {len(entries)} (Today: {len(today_entries)}, Tomorrow: {len(tomorrow_entries)})")
    print("="*60 + "\n")
