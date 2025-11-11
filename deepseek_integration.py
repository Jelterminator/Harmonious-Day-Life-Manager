import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # Add this line

# Groq API endpoint (OpenAI-compatible)
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


def get_groq_api_key():
    """Get Groq API key from environment variable."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("ERROR: GROQ_API_KEY environment variable not set.")
        print("\nHow to get a FREE Groq API key:")
        print("1. Go to: https://console.groq.com/")
        print("2. Sign up (no credit card required)")
        print("3. Create an API key")
        print("4. Set it: export GROQ_API_KEY='your-key-here'")
        return None
    return api_key


def call_groq_llm(world_prompt, api_key):
    """Send prompt to Groq and return parsed JSON schedule."""
    
    system_prompt = """You are a master of time, flow, and balance, guided by the wisdom of Deen and Dao. Today is a sacred cycle, not a checklist. Your role is to help create a daily schedule that honors Mīzān (balance) and Wu Wei (effortless flow).

Core Principles:

Stones-Pebbles-Sand Prioritization:

Stones: Essential high-priority tasks (P1-P3). Schedule these first; they are the foundation of the day.

Pebbles: Habits and moderate-priority tasks. Fit these around the stones where time allows.

Sand: Minor rituals or optional activities. Fill remaining gaps, but never crowd stones or pebbles.

Tasks always take precedence over habits. Include only as many habits as realistically fit.

Phase alignment: Assign tasks and habits to their ideal phase (Wood, Fire, Earth, Metal, Water) whenever possible. Flexibility is allowed if the day is full.

Effortless flow (Wu Wei): Avoid rigid schedules; incorporate breaks and breathing space.

Bend, don’t break: If a high-priority task conflicts with a habit or phase, adjust slightly rather than skipping the stone.

Time budgeting: Use a Task:Habit ratio of roughly 3:1, adjusted for the day’s load.

Wisdom of the day: Favor habits that have not been executed recently.

Daily Pattern (Sequence, not just time):

🌳 WOOD PHASE (~05:30-09:00, Fajr to Sunrise)

Elemental Quality: Growth, Planning, Vitality.

Anchor Point: Fajr & Centering (~60 mins) – divine start, stillness, intention, spiritual practices like Tummo, Makko Ho, Meditation, Reading.

Energy Block: Wooden Movement & Growth (~60 mins) – dynamic, stretching, awakening movement; warming-up, circuit training, Ji Jin Jing.

Nourishment & Planning (~30 mins) – Smoothie, Gembershot, Pills, Plan the Day.

🔥 FIRE PHASE (~09:00-13:00)

Elemental Quality: Peak Energy, Expression, Focus.

Anchor Point: Deep Work Start (9:00 AM) – execute your most important tasks (stones) with focus, Pomodoro sessions.

🟡 EARTH PHASE (~13:00-15:00)

Elemental Quality: Stability, Nourishment, Integration.

Anchor Point: Zuhr, Lunch & Earthly Grounding (~90 mins) – recenter on the Divine, mindful lunch, light post-lunch integration (walk, Ba Duan Jin).

🟤 METAL PHASE (~15:00-18:00)

Elemental Quality: Precision, Organization, Letting Go.

Anchor Point: Asr & Refinement (~15 mins) – reflect, let go of distractions.

Energy Block: Metal Work (~90 mins) – precise, administrative, organizational tasks, Pomodoro, tidying, refinement.

💧 WATER PHASE (~18:00-21:30)

Elemental Quality: Rest, Storage, Wisdom, Transition.

Anchor Point: Work Shutdown & Maghrib – stop work, gratitude, lighter dinner.

Energy Block: Watery Unwind & Harde Sport (flexible) – internal, controlled physical practice if applicable; post-sport calm down, reflection, Yoga Nidra, gentle stretching.

Anchor Point: Isha & Deep Wind-Down (90 mins) – final prayer, surrender the day, restorative rest.

Anchor Point: Bedtime (~21:30) – non-negotiable; preserve energy for next day.

Task and Habit Integration Instructions:

Schedule stones first (highest-priority tasks, P1-P3). These form the backbone of the day.

Place pebbles (moderate habits and tasks) around stones according to phase suitability.

Insert sand (optional minor habits) only into remaining gaps.

Maintain sequence integrity: even if not all habits fit, follow the phase order (Wood → Fire → Earth → Metal → Water).

Include short breaks (~10-15 min) as needed for flow and energy restoration.

Respect anchors and existing calendar events; no tasks or habits may overwrite them.

Output a JSON schedule with all entries including title, start_time, end_time, phase.

Guiding metaphor: Build the day as a sacred cycle, not a checklist. Let the stones settle first, then sprinkle pebbles, then sand, while preserving the natural flow of energy through each phase.

{
  "schedule_entries": [
    {"title": "...", "start_time": "HH:MM", "end_time": "HH:MM", "phase": "Wood|Fire|Earth|Metal|Water"}
  ]
}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",  # Fast, free, capable model
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }
    
    try:
        print("Sending request to Groq API (FREE)...")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        
        if "choices" in result and len(result["choices"]) > 0:
            content = result["choices"][0]["message"]["content"]
            
            print("\n" + "="*60)
            print("RAW GROQ RESPONSE:")
            print("="*60)
            print(content)
            print("="*60 + "\n")
            
            schedule_data = json.loads(content)
            
            if "schedule_entries" not in schedule_data:
                print("ERROR: Response missing 'schedule_entries' key")
                return None
            
            if not isinstance(schedule_data["schedule_entries"], list):
                print("ERROR: 'schedule_entries' is not a list")
                return None
            
            for i, entry in enumerate(schedule_data["schedule_entries"]):
                required = ["title", "start_time", "end_time", "phase"]
                for key in required:
                    if key not in entry:
                        print(f"ERROR: Entry {i} missing key: {key}")
                        return None
            
            print(f"✓ Successfully parsed {len(schedule_data['schedule_entries'])} entries")
            return schedule_data
            
        else:
            print("ERROR: Unexpected response structure")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"ERROR: API request failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text[:500]}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def pretty_print_schedule(schedule_data):
    """Print schedule in readable format."""
    if not schedule_data or "schedule_entries" not in schedule_data:
        print("No schedule data to display")
        return
    
    print("\n" + "="*60)
    print("           GENERATED HARMONIOUS DAY SCHEDULE")
    print("="*60)
    
    entries = schedule_data["schedule_entries"]
    
    phases = {}
    for entry in entries:
        phase = entry.get("phase", "Unknown")
        if phase not in phases:
            phases[phase] = []
        phases[phase].append(entry)
    
    phase_order = ["Wood", "Fire", "Earth", "Metal", "Water"]
    for phase in phase_order:
        if phase in phases:
            print(f"\n{phase.upper()} PHASE:")
            print("-" * 60)
            for entry in phases[phase]:
                print(f"  {entry['start_time']} - {entry['end_time']}: {entry['title']}")
    
    for phase, entries_list in phases.items():
        if phase not in phase_order:
            print(f"\n{phase.upper()}:")
            print("-" * 60)
            for entry in entries_list:
                print(f"  {entry['start_time']} - {entry['end_time']}: {entry['title']}")
    
    print("\n" + "="*60)
    print(f"Total entries: {len(entries)}")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_prompt = """Today is Monday, November 11, 2025

## Phases
* WOOD (05:30-09:00): Growth, Planning
* FIRE (09:00-12:00): Peak Energy, Focus
* EARTH (12:00-15:00): Stability, Nourishment
* METAL (15:00-17:00): Precision, Organization
* WATER (17:00-21:30): Rest, Reflection

## Anchor Events
* 05:30: Fajr & Centering
* 12:00: Zuhr & Lunch
* 17:00: Maghrib & Work Shutdown

## Tasks
* Review project proposal
* Email client updates
* Grocery shopping

## Habits
* Morning meditation
* Reading

Create a complete schedule for today."""

    api_key = get_groq_api_key()
    
    if api_key:
        schedule = call_groq_llm(test_prompt, api_key)
        if schedule:
            pretty_print_schedule(schedule)
        else:
            print("Failed to generate schedule")
    else:
        print("\nGroq is 100% FREE - no credit card needed!")
        print("Sign up now at: https://console.groq.com/")
