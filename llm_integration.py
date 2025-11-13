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


def call_groq_llm(world_prompt, api_key, system_prompt_path="system_prompt.txt"):
    """Send the world prompt to Groq and return parsed JSON schedule."""

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
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }

    try:
        print("Sending request to Groq API...")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        schedule_data = json.loads(content)

        if "schedule_entries" not in schedule_data:
            print("ERROR: Missing 'schedule_entries' key in response")
            return None

        print(f"✓ Parsed {len(schedule_data['schedule_entries'])} entries")
        return schedule_data

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return None



def pretty_print_schedule(schedule_data):
    """Print a readable version of the schedule."""
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("⚠️ No schedule data to display.")
        return

    print("\n" + "="*60)
    print("       🌿 GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)

    entries = schedule_data["schedule_entries"]
    phases = {}

    for entry in entries:
        phases.setdefault(entry.get("phase", "Unknown"), []).append(entry)

    phase_order = ["Wood", "Fire", "Earth", "Metal", "Water"]

    for phase in phase_order:
        if phase in phases:
            print(f"\n{phase.upper()} PHASE:")
            print("-" * 60)
            for e in phases[phase]:
                print(f"  {e['start_time']} - {e['end_time']}: {e['title']}")

    print("\n" + "="*60)
    print(f"Total entries: {len(entries)}")
    print("="*60 + "\n")
