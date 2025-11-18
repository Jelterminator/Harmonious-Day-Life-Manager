# 🌿 Harmonious Day - AI-Powered Daily Planner

An intelligent daily planner that generates optimized schedules aligned with natural rhythms (Wu Xing phases) and spiritual practice (Islamic prayer times). Powered by AI to balance productivity, habits, and wellbeing.

---

## 🎯 What It Does

Harmonious Day automatically creates your daily schedule by:

1. **Gathering** your tasks, habits, and calendar events
2. **Prioritizing** tasks by urgency and deadline
3. **Optimizing** with AI to fit everything into natural energy phases
4. **Writing** the schedule directly to Google Calendar

**Result:** A balanced day that respects your fixed commitments, prioritizes urgent work, and includes time for habits and self-care.

---

## ✨ Key Features

- 🤖 **AI-Powered Scheduling** - Uses Groq LLM to intelligently arrange your day
- 📅 **Google Calendar Integration** - Automatically creates events
- ✅ **Google Tasks Integration** - Pulls tasks with deadlines
- 📊 **Priority Management** - Urgent tasks get scheduled first
- 🌊 **Wu Xing Phases** - Aligns activities with natural energy cycles
- 🕌 **Prayer Time Anchors** - Respects spiritual practice (customizable)
- 🎨 **Conflict Detection** - Never overlaps with existing calendar events
- 📝 **Habit Tracking** - Fills spare time with healthy habits

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Account (for Calendar, Tasks, Sheets)
- Groq API Key (free at [console.groq.com](https://console.groq.com))

### Installation (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/harmonious-day.git
cd harmonious-day

# 2. Run setup wizard (installs dependencies, configures APIs)
python setup.py
```

The setup wizard will:
1. ✅ Install Python packages
2. ✅ Prompt for your Groq API key
3. ✅ Open browser to authenticate with Google
4. ✅ Create a habit tracking spreadsheet

### Daily Usage

```bash
# Generate today's schedule
python plan.py
```

That's it! Check your Google Calendar for your optimized schedule.

---

## 📋 What You'll Need

### 1. Groq API Key (2 minutes, FREE)
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up (no credit card required)
3. Create an API key
4. Setup wizard will prompt you for it

### 2. Google Cloud Project (5 minutes, FREE)
The setup wizard guides you through:
1. Creating a Google Cloud project
2. Enabling APIs (Calendar, Tasks, Sheets)
3. Downloading OAuth credentials

**Why?** Google requires this for security - ensures only YOU access YOUR data.

---

## 📂 Project Structure

```
harmonious-day/
├── config_manager.py          # Configuration management
├── logger.py                  # Logging setup
├── auth.py                    # Google authentication
├── services.py                # Service layer (Calendar, Tasks, Sheets)
├── prompt_builder.py          # AI prompt construction
├── schedule_processor.py      # Schedule validation & processing
├── main.py                    # Main orchestrator
├── plan.py                    # Entry point (run this daily)
├── setup.py                   # One-time setup wizard
├── task_processor.py          # Task prioritization
├── habit_processor.py         # Habit filtering
├── llm_integration.py         # Groq API integration
├── config.json                # Phase times & prayer schedule
├── system_prompt.txt          # AI instructions
├── .env                       # Your API keys (created by setup)
├── requirements.txt           # Python dependencies
└── logs/                      # Execution logs
```

---

## ⚙️ Configuration

### Phase Times (config.json)

Customize the Wu Xing phases for your schedule:

```json
{
  "phases": [
    {
      "name": "WOOD",
      "start": "05:30",
      "end": "09:00",
      "qualities": "Growth, Planning, Vitality"
    }
  ]
}
```

**Phases:**
- 🌳 **WOOD (05:30-09:00)** - Morning energy, planning, movement
- 🔥 **FIRE (09:00-13:00)** - Peak focus, deep work
- 🌍 **EARTH (13:00-15:00)** - Grounding, meals, integration
- 🔧 **METAL (15:00-18:00)** - Organization, refinement
- 💧 **WATER (18:00-21:45)** - Rest, reflection, wind-down

### Prayer Times (config.json)

Adjust for your location:

```json
{
  "anchors": [
    {"name": "Fajr", "time": "05:30-05:40", "phase": "Wood"},
    {"name": "Zuhr", "time": "13:00-13:20", "phase": "Earth"}
  ]
}
```

**Note:** These can be customized for any spiritual practice or removed entirely.

### AI Behavior (system_prompt.txt)

Modify how the AI schedules tasks:
- Task chunking strategies
- Habit prioritization
- Break time preferences
- Phase alignment rules

### Environment Variables (.env)

```bash
GROQ_API_KEY=gsk_...           # Your Groq API key
SHEET_ID=1rdyK...              # Google Sheets ID (auto-created)
TIMEZONE=Europe/Amsterdam      # Your timezone
LOG_LEVEL=INFO                 # Logging verbosity
MAX_OUTPUT_TASKS=24            # Max tasks per day
```

---

## 📊 How It Works

### The Pipeline

```
1. GATHER DATA
   ├── Fixed calendar events (Google Calendar)
   ├── Tasks with deadlines (Google Tasks)
   └── Daily habits (Google Sheets)

2. PROCESS & PRIORITIZE
   ├── Calculate task urgency (deadline proximity)
   ├── Filter today's habits
   └── Group parent tasks with subtasks

3. BUILD AI PROMPT
   ├── Time constraints (current time → tomorrow)
   ├── Fixed events (immovable "stones")
   ├── Urgent tasks (important "pebbles")
   └── Habits & chores (gap-filling "sand")

4. GENERATE SCHEDULE (AI)
   ├── Respects fixed events
   ├── Schedules anchors (prayers)
   ├── Fits urgent tasks in optimal phases
   └── Fills gaps with habits

5. VALIDATE & FILTER
   ├── Check for conflicts with calendar
   ├── Validate all required fields
   └── Parse timestamps correctly

6. WRITE TO CALENDAR
   └── Create color-coded events in Google Calendar
```

### Priority System

Tasks are prioritized into tiers based on **hours needed per day** until deadline:

| Tier | Hours/Day | Meaning | Subtasks Scheduled |
|------|-----------|---------|-------------------|
| T1 | >4 hours | CRITICAL - Deadline today/tomorrow | 5 |
| T2 | 2-4 hours | HIGH - Needs daily focus | 3 |
| T3 | 1-2 hours | MEDIUM - Regular attention | 2 |
| T4 | 0.5-1 hour | NORMAL - Flexible scheduling | 2 |
| T5 | 0.25-0.5 hour | LOW - When convenient | 1 |
| T6 | N/A | CHORES - Fill gaps | All |

---

## 🎨 Customization Examples

### Example 1: Change Work Hours

```json
// config.json - Shift to afternoon worker
{
  "phases": [
    {"name": "WATER", "start": "00:00", "end": "10:00"},
    {"name": "WOOD", "start": "10:00", "end": "13:00"},
    {"name": "FIRE", "start": "13:00", "end": "18:00"},
    {"name": "EARTH", "start": "18:00", "end": "20:00"},
    {"name": "METAL", "start": "20:00", "end": "24:00"}
  ]
}
```

### Example 2: Remove Prayer Times

```json
// config.json - Secular version
{
  "anchors": [
    {"name": "Morning Routine", "time": "07:00-07:30", "phase": "Wood"},
    {"name": "Lunch", "time": "12:30-13:00", "phase": "Earth"},
    {"name": "Evening Routine", "time": "21:00-21:30", "phase": "Water"}
  ]
}
```

### Example 3: Add Your Own Habits

Edit the Google Sheet created during setup:
1. Open "Harmonious Day: Habit Database"
2. Add rows with: title, duration, frequency, ideal phase
3. Set `active` to `Yes`

---

## 🔧 Advanced Usage

### Running with Debug Logs

```bash
# Set in .env
LOG_LEVEL=DEBUG

# Then run
python plan.py

# View detailed logs
cat logs/harmonious_day_*.log
```

### Testing Individual Components

```python
# Test services
from services import ServiceFactory
from auth import get_google_services

services = ServiceFactory.create_services(*get_google_services())
events = services[0].get_upcoming_events()
print(f"Found {len(events)} calendar events")

# Test prompt building
from prompt_builder import PromptBuilder
from config_manager import Config

builder = PromptBuilder(Config.load_phase_config())
prompt = builder.build_world_prompt([], [], [])
print(f"Prompt length: {len(prompt)} characters")

# Test task processing
from task_processor import TaskProcessor

processor = TaskProcessor()
tasks = processor.process_tasks([
    {'id': '1', 'title': 'Task (2h)', 'due': '2025-12-31'}
])
print(f"Processed {len(tasks)} tasks")
```

### Modifying AI Behavior

Edit `system_prompt.txt` to change how tasks are scheduled:

```
// Add more break time
After every 2-hour block, schedule a 15-minute break.

// Prefer mornings for creative work
Creative tasks should be scheduled in WOOD or FIRE phases when possible.

// Batch similar tasks
Group similar tasks together (e.g., all emails, all coding).
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError"
**Solution:** Run `python setup.py` to install dependencies

### "GROQ_API_KEY not set"
**Solution:** Add to `.env` file:
```bash
GROQ_API_KEY=your_key_here
```

### "Authentication failed"
**Solution:** Delete `token.json` and run `python setup.py` again

### "App isn't verified" (during Google login)
**Solution:** This is normal for personal apps. Click:
1. "Advanced"
2. "Go to Harmonious Day (unsafe)"
3. It's YOUR app, totally safe

### "No schedule generated"
**Solution:** 
1. Check logs: `cat logs/harmonious_day_*.log`
2. Verify Groq API key is valid
3. Ensure Google Tasks has some tasks
4. Try with LOG_LEVEL=DEBUG

### "All entries filtered out"
**Solution:** Your calendar is full. Either:
1. Remove some calendar events
2. Extend scheduling window
3. Mark some tasks as lower priority

---

## 📈 Performance

- **Setup:** One-time, ~10 minutes
- **Daily run:** ~10-15 seconds
  - 2s - Data collection
  - 1s - Processing
  - 5s - AI generation
  - 2s - Calendar writing

**Optimization tips:**
- Keep habits list under 30 items
- Archive completed tasks regularly
- Limit task list to ~50 active tasks

---

## 🧪 Testing

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run unit tests (after writing them)
pytest tests/ -v

# With coverage report
pytest tests/ --cov=. --cov-report=html

# Test specific module
pytest tests/test_task_processor.py
```

---

## 🔐 Security & Privacy

- ✅ **All data stays local** - No external servers except Google & Groq APIs
- ✅ **OAuth 2.0** - Secure Google authentication
- ✅ **API keys in .env** - Never committed to git
- ✅ **Read-only tasks** - Can't modify your tasks, only read
- ✅ **Calendar isolation** - Can filter AI events by metadata

**Data accessed:**
- Google Calendar: Read all events, create new events
- Google Tasks: Read open tasks (read-only)
- Google Sheets: Read habit sheet

**Data NOT accessed:**
- Email
- Drive files (except habit sheet)
- Contacts
- Photos

---

## 📝 Development

### Code Style

```bash
# Format code
black *.py

# Type checking
mypy *.py

# Linting
pylint *.py
```

### Architecture

The project follows **SOLID principles** with clear separation of concerns:

- **Services Layer** (`services.py`) - External API interactions
- **Business Logic** (`task_processor.py`, `habit_processor.py`) - Processing
- **AI Integration** (`llm_integration.py`, `prompt_builder.py`) - LLM communication
- **Orchestration** (`main.py`) - Coordinates the pipeline
- **Configuration** (`config_manager.py`) - Centralized settings

See `PHASE_2_COMPLETE.md` for detailed architecture documentation.

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

1. **Testing** - Add unit and integration tests
2. **UI** - Web interface for configuration
3. **Plugins** - Support for more calendar/task services
4. **ML** - Learn from past schedules to improve
5. **Mobile** - React Native app

**Before contributing:**
1. Read `BEST_PRACTICES.md`
2. Follow existing code style
3. Add tests for new features
4. Update documentation

---

## 📜 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Wu Xing Philosophy** - Traditional Chinese five-phase theory
- **Islamic Prayer Times** - Inspiration for temporal anchoring
- **Groq** - Fast, efficient LLM inference
- **Google APIs** - Calendar, Tasks, Sheets integration

---

## 📞 Support

- **Documentation:** See `/docs` folder for detailed guides
- **Issues:** [GitHub Issues](https://github.com/yourusername/harmonious-day/issues)
- **Logs:** Check `logs/harmonious_day_*.log` for detailed debugging

---

## 🗺️ Roadmap

### Version 1.0 (Current)
- ✅ Core scheduling pipeline
- ✅ Google integrations
- ✅ AI-powered optimization
- ✅ Phase-based scheduling

### Version 1.1 (Next)
- 🔜 Comprehensive test suite
- 🔜 Web UI for configuration
- 🔜 Schedule history & analytics
- 🔜 Mobile notifications

### Version 2.0 (Future)
- 🔮 Machine learning from past schedules
- 🔮 Multi-user/team scheduling
- 🔮 Todoist, Notion integrations
- 🔮 Voice assistant integration

---

## 💡 Tips & Tricks

1. **Run daily in the morning** - Best results when schedule is fresh
2. **Add effort estimates** - Format: "Task name (2h)" in task title
3. **Set realistic deadlines** - AI prioritizes based on due dates
4. **Review generated schedule** - Check `generated_schedule.json` for AI reasoning
5. **Customize phases** - Adjust times to match your energy patterns
6. **Track habit completion** - Mark habits as done in the Google Sheet
7. **Use task notes** - Add context with `[Effort: 3h]` in notes field
8. **Check logs often** - Logs show exactly what the AI decided

---

## 🌟 Example Day

```
WOOD PHASE (05:30-09:00)
  05:30 - 05:40: Fajr
  05:40 - 06:10: Morning Meditation
  06:10 - 06:40: Morning Reading
  06:40 - 07:00: Stretches
  07:00 - 09:00: Deep Work: Write Report (Chapter 1)

FIRE PHASE (09:00-13:00)
  09:00 - 09:30: [FIXED] Team Standup Meeting
  09:30 - 11:30: Deep Work: Write Report (Chapter 2)
  11:30 - 13:00: Code Review: PR #234

EARTH PHASE (13:00-15:00)
  13:00 - 13:20: Zuhr
  13:20 - 14:00: Lunch & Mindful Eating
  14:00 - 14:30: Light Walk
  14:30 - 15:00: Admin: Respond to emails

METAL PHASE (15:00-18:00)
  15:00 - 15:20: Asr
  15:20 - 16:00: Organize Workspace
  16:00 - 18:00: [FIXED] Client Call

WATER PHASE (18:00-21:45)
  18:00 - 18:15: Maghrib
  18:15 - 19:00: Evening Walk
  19:00 - 20:00: Reading: Fiction Book
  20:00 - 20:30: Meditation
  20:30 - 21:00: Journaling
  21:00 - 21:20: Isha
  21:20 - 21:45: Wind Down
```

---

**Built with ❤️ to create more harmonious, balanced days**

*For detailed technical documentation, see `PHASE_2_COMPLETE.md` and `PHASE_2_QUICK_REFERENCE.md`*
