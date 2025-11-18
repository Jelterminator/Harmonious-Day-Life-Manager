# Phase 2: Quick Reference Guide

## File Structure After Phase 2

```
harmonious_day/
├── config_manager.py          # ✅ Phase 1 - Configuration management
├── logger.py                  # ✅ Phase 1 - Logging setup
├── auth.py                    # ✅ Phase 1 - Google authentication
├── services.py                # 🆕 Phase 2 - Service layer
├── prompt_builder.py          # 🆕 Phase 2 - Prompt construction
├── schedule_processor.py      # 🆕 Phase 2 - Schedule processing
├── main.py                    # ♻️  Phase 2 - Refactored orchestrator
├── plan.py                    # ♻️  Phase 2 - Updated entry point
├── task_processor.py          # ✅ Phase 1 - Task processing
├── habit_processor.py         # ✅ Phase 1 - Habit filtering
├── llm_integration.py         # ✅ Phase 1 - LLM API calls
├── setup.py                   # ✅ Phase 1 - Setup wizard
├── config.json                # Configuration file
├── system_prompt.txt          # LLM system prompt
├── .env                       # Environment variables
├── .gitignore                 # ♻️  Phase 1 - Updated
├── requirements.txt           # ♻️  Phase 2 - Updated
└── logs/                      # 🆕 Log files directory
```

---

## What Each Module Does (30-Second Guide)

### Core Infrastructure
| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `config_manager.py` | Central configuration | `Config` |
| `logger.py` | Logging setup | `setup_logger()` |
| `auth.py` | Google OAuth | `get_google_services()` |

### Service Layer (NEW)
| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `services.py` | External API interactions | `GoogleCalendarService`, `GoogleSheetsService`, `GoogleTasksService`, `DataCollector` |
| `prompt_builder.py` | LLM prompt construction | `PromptBuilder` |
| `schedule_processor.py` | Schedule validation & processing | `ScheduleProcessor` |

### Business Logic
| Module | Purpose | Key Classes |
|--------|---------|-------------|
| `main.py` | Pipeline orchestration | `Orchestrator`, `OrchestratorFactory` |
| `task_processor.py` | Task prioritization | `TaskProcessor` |
| `habit_processor.py` | Habit filtering | `filter_habits()` |
| `llm_integration.py` | Groq API calls | `call_groq_llm()` |

### Entry Points
| Module | Purpose |
|--------|---------|
| `setup.py` | One-time setup wizard |
| `plan.py` | Daily planner execution |

---

## Component Responsibilities (One-Liner Each)

```python
# services.py
GoogleCalendarService   # Get/create/delete calendar events
GoogleSheetsService     # Fetch habits from Google Sheets
GoogleTasksService      # Fetch tasks from Google Tasks
DataCollector           # Orchestrates data collection from all services

# prompt_builder.py
PromptBuilder           # Builds LLM prompts with constraints

# schedule_processor.py
ScheduleProcessor       # Validates, filters conflicts, saves schedules

# main.py
Orchestrator            # Coordinates entire pipeline
OrchestratorFactory     # Creates validated orchestrator instances
```

---

## Import Cheat Sheet

```python
# Configuration and Logging
from config_manager import Config
from logger import setup_logger

# Authentication
from auth import get_google_services, create_initial_token

# Services (NEW)
from services import (
    GoogleCalendarService,
    GoogleSheetsService,
    GoogleTasksService,
    DataCollector,
    ServiceFactory
)

# Processors (NEW)
from prompt_builder import PromptBuilder
from schedule_processor import ScheduleProcessor

# Business Logic
from task_processor import TaskProcessor
from habit_processor import filter_habits
from llm_integration import call_groq_llm, pretty_print_schedule

# Orchestration
from main import Orchestrator, OrchestratorFactory
```

---

## Common Usage Patterns

### Pattern 1: Create Services
```python
# Get raw Google API services
raw_services = get_google_services()

# Wrap in service layer
calendar, sheets, tasks = ServiceFactory.create_services(*raw_services)

# Use services
events = calendar.get_upcoming_events(days_ahead=2)
habits = sheets.get_habits()
all_tasks = tasks.get_all_tasks()
```

### Pattern 2: Build Prompts
```python
# Load rules
rules = Config.load_phase_config()

# Create builder
builder = PromptBuilder(rules)

# Build prompt
prompt = builder.build_world_prompt(
    calendar_events=events,
    tasks=processed_tasks,
    habits=filtered_habits
)

# Save for debugging
builder.save_prompt(prompt)
```

### Pattern 3: Process Schedules
```python
# Create processor
processor = ScheduleProcessor()

# Validate entries
valid_entries, errors = processor.validate_schedule_entries(raw_entries)

# Filter conflicts
final_entries = processor.filter_conflicting_entries(
    valid_entries,
    calendar_events
)

# Save result
processor.save_schedule({'schedule_entries': final_entries})
```

### Pattern 4: Run Full Pipeline
```python
# Create orchestrator (with validation)
orchestrator = OrchestratorFactory.create()

# Run daily plan
success = orchestrator.run_daily_plan()

if success:
    print("Schedule created successfully!")
```

---

## Testing Guide

### Unit Testing Individual Components

```python
# Test PromptBuilder (no external dependencies)
def test_prompt_builder():
    rules = {'phases': [], 'anchors': []}
    builder = PromptBuilder(rules)
    prompt = builder.build_world_prompt([], [], [])
    assert "SCHEDULE REQUEST" in prompt
    assert "PHASES:" in prompt

# Test ScheduleProcessor (no external dependencies)
def test_conflict_detection():
    processor = ScheduleProcessor()
    
    entries = [
        {'title': 'Task', 'start_time': '10:00', 'end_time': '11:00', 
         'phase': 'FIRE', 'date': 'today'}
    ]
    events = [
        {'summary': 'Meeting', 'start': '10:30', 'end': '11:30'}
    ]
    
    result = processor.filter_conflicting_entries(entries, events)
    assert len(result) == 0  # Conflict should be filtered

# Test with Mocks
from unittest.mock import Mock

def test_data_collector():
    mock_calendar = Mock(spec=GoogleCalendarService)
    mock_sheets = Mock(spec=GoogleSheetsService)
    mock_tasks = Mock(spec=GoogleTasksService)
    
    mock_calendar.get_upcoming_events.return_value = []
    mock_sheets.get_habits.return_value = []
    mock_tasks.get_all_tasks.return_value = []
    
    collector = DataCollector(mock_calendar, mock_sheets, mock_tasks)
    data = collector.collect_all_data()
    
    assert 'calendar_events' in data
    assert 'raw_tasks' in data
    assert 'raw_habits' in data
```

---

## Debugging Tips

### 1. Check Logs First
```bash
# View today's log
cat logs/harmonious_day_$(date +%Y%m%d).log

# Watch logs in real-time
tail -f logs/harmonious_day_*.log
```

### 2. Enable Debug Logging
```python
# In any module
from logger import setup_logger
logger = setup_logger(__name__, level=logging.DEBUG)
```

### 3. Test Individual Components
```python
# Test services without running full pipeline
from services import ServiceFactory
from auth import get_google_services

services = ServiceFactory.create_services(*get_google_services())
events = services[0].get_upcoming_events()
print(f"Found {len(events)} events")
```

### 4. Validate Schedule JSON
```python
# Load and inspect generated schedule
import json
with open('generated_schedule.json') as f:
    schedule = json.load(f)
    
print(f"Entries: {len(schedule['schedule_entries'])}")
for entry in schedule['schedule_entries']:
    print(f"  {entry['start_time']} - {entry['title']}")
```

---

## Common Modifications

### Change Prompt Format
**File:** `prompt_builder.py`
```python
class PromptBuilder:
    def build_world_prompt(self, ...):
        # Modify prompt structure here
        prompt_lines.append("YOUR NEW SECTION")
```

### Add New Service
**File:** `services.py`
```python
class NewAPIService:
    def __init__(self, api_service):
        self.service = api_service
    
    def get_data(self):
        # Your API call here
        pass

# Add to ServiceFactory
@staticmethod
def create_services(...):
    return (calendar, sheets, tasks, new_service)
```

### Change Conflict Detection Logic
**File:** `schedule_processor.py`
```python
class ScheduleProcessor:
    def filter_conflicting_entries(self, ...):
        # Modify conflict detection here
        pass
```

### Modify Pipeline Steps
**File:** `main.py`
```python
class Orchestrator:
    def run_daily_plan(self):
        # Add/remove/reorder steps here
        self._your_new_step()
```

---

## Performance Profiling

### Profile Full Pipeline
```python
import cProfile
import pstats

# In plan.py
def main():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run pipeline
    orchestrator = OrchestratorFactory.create()
    orchestrator.run_daily_plan()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 slowest functions
```

### Time Individual Components
```python
import time

start = time.time()
data = collector.collect_all_data()
print(f"Data collection: {time.time() - start:.2f}s")

start = time.time()
prompt = builder.build_world_prompt(...)
print(f"Prompt building: {time.time() - start:.2f}s")
```

---

## Environment Variables Reference

```bash
# .env file
GROQ_API_KEY=gsk_...              # Required: Groq API key
SHEET_ID=1rdyK...                 # Required: Google Sheets ID
TIMEZONE=Europe/Amsterdam         # Optional: Default timezone
LOG_LEVEL=INFO                    # Optional: Logging level
MAX_OUTPUT_TASKS=24               # Optional: Max tasks to process
```

---

## Command Reference

```bash
# Setup (run once)
python setup.py

# Daily planning
python plan.py

# Run tests (after writing them)
pytest tests/

# Type checking
mypy src/

# Code formatting
black src/

# View logs
ls -lh logs/
cat logs/harmonious_day_*.log
```

---

## Error Messages and Solutions

| Error | Likely Cause | Solution |
|-------|-------------|----------|
| `ModuleNotFoundError: services` | Missing file | Copy `services.py` to project root |
| `Config.GROQ_API_KEY is None` | Missing API key | Add to `.env`: `GROQ_API_KEY=your_key` |
| `Authentication failed` | Missing/invalid token | Run `python setup.py` |
| `No schedule data to display` | LLM generation failed | Check logs, verify API key |
| `Filtered out all entries` | All tasks conflict | Check calendar events, adjust times |

---

## Quick Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                       plan.py                            │
│                    (Entry Point)                         │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  OrchestratorFactory                     │
│                 (Creates & Validates)                    │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                     Orchestrator                         │
│                  (Pipeline Coordinator)                  │
└───┬────────┬──────────┬──────────┬──────────┬──────────┘
    │        │          │          │          │
    │        │          │          │          │
    ▼        ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
│Data  │ │Task  │  │Prompt│  │Sched │  │LLM   │
│Coll  │ │Proc  │  │Build │  │Proc  │  │API   │
└──┬───┘ └──────┘  └──────┘  └──────┘  └──────┘
   │
   ▼
┌──────────────────────────────────┐
│        Service Layer             │
├──────────┬──────────┬────────────┤
│Calendar  │ Sheets   │  Tasks     │
│Service   │ Service  │  Service   │
└──────────┴──────────┴────────────┘
```

---

## What's Next?

After completing Phase 2, you should:

1. ✅ Test the refactored code
2. ✅ Run the full pipeline end-to-end
3. ✅ Check that calendar events are created correctly
4. 🔜 Write unit tests for new modules
5. 🔜 Add dataclasses for type safety
6. 🔜 Set up CI/CD pipeline

---

## Getting Help

1. **Check logs:** `cat logs/harmonious_day_*.log`
2. **Run with debug:** Set `LOG_LEVEL=DEBUG` in `.env`
3. **Test components individually:** Use patterns above
4. **Check configuration:** Run `python -c "from config_manager import Config; print(Config.validate())"`

---

**Remember:** The refactoring maintains the same user-facing behavior. The improvements are all internal architecture and code quality! 🎉
