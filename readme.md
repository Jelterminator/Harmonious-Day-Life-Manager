# 🌿 Harmonious Day

**AI-Powered Daily Planner Aligned with Natural Rhythms & Spiritual Practice**

Harmonious Day is an intelligent scheduling system that generates optimized daily plans by harmonizing your tasks, habits, and commitments with natural energy cycles (Wu Xing) and spiritual anchors (customizable prayer times). Built with Python and powered by Groq LLM technology, it automatically creates balanced schedules that respect your productivity needs and wellbeing.

---

## ✨ Core Philosophy

Harmonious Day is built on three foundational principles:

1. **Balance (Mīzān)** - Equilibrium between work, rest, spiritual practice, and personal growth
2. **Flow (Wu Wei)** - Effortless action through alignment with natural rhythms
3. **Sacred Structure** - Regular spiritual anchors that ground daily activities in meaning

The system integrates:
- **Wu Xing (Five Phases)** - Traditional Chinese understanding of natural energy cycles throughout the day
- **Spiritual Discipline** - Regular prayer/meditation times (customizable to any tradition)
- **Modern Productivity** - Task prioritization, deadline management, and intelligent conflict resolution

---

## 🎯 What It Does

### The Daily Workflow

Every morning, Harmonious Day:

1. **Gathers** your commitments from Google Calendar, tasks from Google Tasks, and habits from Google Sheets
2. **Analyzes** task urgency based on effort estimates, deadlines, and available time
3. **Generates** an optimized schedule using AI that:
   - Respects all fixed calendar events
   - Schedules spiritual anchors (prayers/meditation)
   - Prioritizes urgent work during peak energy phases
   - Fills remaining time with healthy habits
   - Prevents scheduling conflicts
4. **Writes** the complete schedule directly to your Google Calendar

**Result:** A balanced day with clear priorities, protected rest time, and integrated spiritual practice.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- Google Account (Calendar, Tasks, Sheets)
- Groq API Key ([free at console.groq.com](https://console.groq.com))

### Installation (5 Minutes)

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/harmonious-day.git
cd harmonious-day

# 2. Run setup wizard
python scripts/setup.py
```

The setup wizard will:
- ✅ Install dependencies
- ✅ Guide you through Google Cloud authentication
- ✅ Create your habit tracking spreadsheet
- ✅ Configure your Groq API key

### Daily Usage

```bash
# Generate today's schedule
python scripts/plan.py

# Clear previous AI-generated events
python scripts/clear.py
```

That's it! Your optimized schedule appears in Google Calendar.

---

## 📋 Key Features

### 🤖 Intelligent Scheduling

- **Priority-Based Allocation** - Urgent tasks get scheduled first in optimal time slots
- **Phase Alignment** - Activities matched to natural energy cycles (creative work during peak hours, admin during low energy)
- **Conflict Resolution** - Never overlaps with existing calendar events
- **Smart Chunking** - Large tasks broken into manageable 30-180 minute blocks
- **Jar Prioritization** - Stones (fixed events) → Anchors (prayers) → Pebbles (urgent tasks) → Sand (habits)

### 🌊 Wu Xing Phases

The day is divided into five natural energy phases:

| Phase | Time | Energy Quality | Best For |
|-------|------|----------------|----------|
| 🌳 **WOOD** | 05:30-09:00 | Growth, Planning, Vitality | Spiritual practice, movement, planning |
| 🔥 **FIRE** | 09:00-13:00 | Peak Energy, Focus | Deep work, creative projects, challenging tasks |
| 🌍 **EARTH** | 13:00-15:00 | Grounding, Integration | Meals, light admin, processing |
| 🔧 **METAL** | 15:00-18:00 | Organization, Refinement | Admin, review, tidying, study |
| 💧 **WATER** | 18:00-21:45 | Rest, Consolidation | Exercise, reading, reflection, wind-down |

### 📊 Priority System

Tasks are automatically prioritized based on **hours needed per day until deadline**:

| Tier | Hours/Day | Urgency | Scheduled |
|------|-----------|---------|-----------|
| **T1** | >4 hours | CRITICAL | 4 subtasks |
| **T2** | 2-4 hours | HIGH | 3 subtasks |
| **T3** | 1-2 hours | MEDIUM | 2 subtasks |
| **T4** | 0.5-1 hour | NORMAL | 1 subtask |
| **T5** | 0.25-0.5 hour | LOW | 1 subtask |
| **T6** | No deadline | CHORES | All (if time) |

### 🎨 Google Calendar Integration

- **Color-Coded Events** - Each phase has distinct colors for quick visual reference
- **Metadata Tracking** - Events tagged with phase and source information
- **Batch Operations** - Efficient API usage for creating/deleting events
- **Timezone Awareness** - Handles multiple timezones correctly

### 📝 Habit Management

- **Daily/Weekly Patterns** - Flexible scheduling based on frequency
- **Phase Preferences** - Habits scheduled near their ideal energy phase
- **Dynamic Adjustment** - Durations can flex ±50% to fit available time
- **Google Sheets Backend** - Easy editing in familiar spreadsheet interface

---

## 🏗️ Architecture

### Project Structure

```
harmonious-day/
├── scripts/
│   ├── plan.py              # Daily planner entry point
│   ├── clear.py             # Clear previous schedules
│   └── setup.py             # One-time setup wizard
├── src/
│   ├── auth/                # Google OAuth authentication
│   ├── core/                # Configuration and orchestration
│   ├── llm/                 # LLM integration (prompt building, API calls)
│   ├── models/              # Type-safe data models
│   ├── processors/          # Task/habit/schedule processing
│   ├── services/            # Google API service layer
│   └── utils/               # Logging and utilities
├── config/
│   ├── config.json          # Phase times and anchors
│   └── system_prompt.txt    # AI scheduling instructions
├── tests/                   # Unit and integration tests (89% coverage)
├── output/                  # Generated schedules and prompts
├── logs/                    # Execution logs
└── requirements.txt
```

### Design Principles

**Type Safety** - Dataclasses with enums throughout for catching errors early
- `Task`, `Habit`, `CalendarEvent`, `ScheduleEntry` models
- `PriorityTier`, `Phase`, `Frequency` enums

**Separation of Concerns** - Each module has a single responsibility
- **Services** - External API interactions
- **Processors** - Business logic (prioritization, filtering)
- **Orchestrator** - Pipeline coordination

**Testability** - 89% test coverage with 60+ unit and integration tests

**Maintainability** - ~200 lines per module, comprehensive documentation

---

## ⚙️ Configuration

### Phase Times (`config/config.json`)

Customize when each phase occurs:

```json
{
  "phases": [
    {
      "name": "WOOD",
      "start": "05:30",
      "end": "09:00",
      "qualities": "Growth, Planning, Vitality",
      "ideal_tasks": ["spiritual", "planning", "movement"]
    }
  ]
}
```

**Common Adjustments:**
- **Night Owl:** Shift all phases 4-6 hours later
- **Early Bird:** Keep WOOD phase, extend FIRE phase
- **Flexible Schedule:** Remove phase constraints entirely

### Spiritual Anchors (`config/config.json`)

Configure prayer/meditation times:

```json
{
  "anchors": [
    {"name": "Fajr", "time": "05:30-05:40", "phase": "WOOD"},
    {"name": "Zuhr", "time": "13:00-13:20", "phase": "EARTH"},
    {"name": "Asr", "time": "15:00-15:20", "phase": "METAL"},
    {"name": "Maghrib", "time": "18:00-18:15", "phase": "WATER"},
    {"name": "Isha", "time": "21:00-21:20", "phase": "WATER"}
  ]
}
```

**Customization Options:**
- **Islamic:** Keep default 5 daily prayers
- **Christian:** Morning prayer, Midday, Compline
- **Buddhist:** Meditation sessions (morning, noon, evening)
- **Secular:** "Morning Routine", "Lunch Break", "Evening Routine"
- **None:** Remove anchors array entirely

### AI Behavior (`config/system_prompt.txt`)

Modify scheduling rules by editing the system prompt file. Key constraints include:
- Phase alignment preferences
- Task chunking strategies
- Break frequency
- Custom business rules

### Environment Variables (`.env`)

```bash
GROQ_API_KEY=gsk_...              # Required: Groq API key
SHEET_ID=1rdyK...                 # Required: Habit tracking sheet ID
TIMEZONE=Europe/Amsterdam         # Optional: Your timezone
LOG_LEVEL=INFO                    # Optional: DEBUG for troubleshooting
MAX_OUTPUT_TASKS=24               # Optional: Max tasks per day
```

---

## 🧪 Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v
```

### Code Quality

```bash
# Type checking
mypy src/

# Code formatting
black src/ tests/

# Import sorting
isort src/ tests/

# Linting
flake8 src/ tests/
```

### Project Statistics

- **Code Quality:** 89% test coverage
- **Architecture:** SOLID principles, service-oriented
- **Type Safety:** Comprehensive type hints with dataclasses
- **Documentation:** Docstrings on all classes and methods
- **Lines of Code:** ~3,500 (excluding tests)
- **Modules:** 20+ focused components

---

## 🐛 Troubleshooting

### Common Issues

**"GROQ_API_KEY not set"**
```bash
# Add to .env file
echo "GROQ_API_KEY=your_key_here" >> .env
```

**"Authentication failed"**
```bash
# Delete token and re-authenticate
rm token.json
python scripts/setup.py
```

**"No schedule generated"**
1. Check logs: `cat logs/harmonious_day_*.log`
2. Verify API key is valid at console.groq.com
3. Ensure Google Tasks has at least one task
4. Try with `LOG_LEVEL=DEBUG`

**"All entries filtered out"**
- Your calendar is fully booked
- Reduce number of fixed events, or
- Adjust `MAX_OUTPUT_TASKS` in `.env`, or
- Mark some tasks as lower priority

### Debug Checklist

- [ ] Groq API key is valid
- [ ] `token.json` exists and is valid
- [ ] `config/config.json` has valid JSON
- [ ] Google Sheets SHEET_ID is correct
- [ ] At least one task exists in Google Tasks
- [ ] Timezone in `.env` matches your location
- [ ] Python version ≥ 3.9

### Performance Tips

- Keep habit list under 30 active items
- Archive completed tasks regularly
- Limit task list to ~50 active tasks
- Run early morning for best results
- Clear old calendar events periodically

---

## 🔐 Security & Privacy

### Data Access

**What We Access:**
- ✅ Google Calendar - Read all, create new events
- ✅ Google Tasks - Read only (cannot modify)
- ✅ Google Sheets - Read habit sheet only

**What We DON'T Access:**
- ❌ Email (Gmail)
- ❌ Drive files (except habit sheet)
- ❌ Contacts
- ❌ Photos
- ❌ Any other Google services

### Data Storage

- **Local Only** - All data processing happens on your machine
- **No Cloud Storage** - We don't store your data anywhere
- **API Keys in .env** - Never committed to version control
- **OAuth Security** - Secure Google authentication
- **Transparent** - All code is open source

### Groq API

- **What's Sent:** Task titles, deadlines, calendar event summaries
- **What's NOT Sent:** Email addresses, personal notes, location data
- **Privacy:** Groq may log requests per their policy

---

## 📜 License

MIT License - See LICENSE file for details.

Free to use, modify, and distribute. We only ask that you:
- Give credit to the original project
- Share improvements back to the community

---

## 🙏 Acknowledgments

**Philosophical Foundations:**
- **Wu Xing Theory** - Traditional Chinese medicine and philosophy
- **Islamic Prayer Tradition** - Structure and spiritual discipline
- **Taoism** - Wu Wei (effortless action) and natural flow

**Technical Stack:**
- **Groq** - Fast, efficient LLM inference
- **Google APIs** - Calendar, Tasks, Sheets integration
- **Python Community** - Excellent libraries and tools

**Inspiration:**
- Cal Newport's "Deep Work"
- The Pomodoro Technique
- GTD (Getting Things Done)
- Atomic Habits

---

## 📞 Support

- **Documentation:** See `/docs` folder for detailed guides
- **Issues:** [GitHub Issues](https://github.com/yourusername/harmonious-day/issues)
- **Logs:** Check `logs/` directory for detailed execution logs

---

## 🌟 Why Harmonious Day?

Modern productivity tools often increase stress by:
- Overpacking schedules
- Ignoring energy levels
- Neglecting spiritual/personal needs
- Creating rigid, inflexible plans

Harmonious Day is different:
- ✅ **Balanced** - 60% work, 40% rest/habits
- ✅ **Flexible** - AI adapts to your constraints
- ✅ **Holistic** - Integrates mind, body, spirit
- ✅ **Sustainable** - Prevents burnout through natural rhythms
- ✅ **Personal** - Customizable to any lifestyle or belief system

**Our Goal:** Help you achieve more while feeling better.

---

**Built with ❤️ to create more harmonious, balanced, meaningful days**

*Current Version: 1.0.0 - Production Ready*