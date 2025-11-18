# 🗺️ Harmonious Day - Product Roadmap

**Vision:** An intelligent, universal daily planner that works anywhere, offline, and respects diverse spiritual traditions while optimizing for flow and wellbeing.

---

## 📍 Current State (v1.0.0)

### ✅ Completed Features

**Core Functionality:**
- Python-based orchestration system
- Google Calendar/Tasks/Sheets integration
- Groq powered GPT-OSS-20B schedule generation
- Wu Xing phase-based scheduling
- Islamic prayer time anchors
- Priority-based task allocation
- Conflict detection and resolution
- Type-safe dataclass architecture
- 89% test coverage

**User Experience:**
- Command-line interface
- One-time setup wizard
- Daily schedule generation
- Manual configuration editing
- Detailed logging

**Technical Infrastructure:**
- Service-oriented architecture
- Comprehensive testing suite
- CI/CD pipelines (GitHub Actions)
- Type checking with MyPy
- Professional documentation

---

## 🎯 Strategic Goals

### Near-Term (6 Months)
1. **Flexibility** - Dynamic configuration for any tradition/location
2. **Privacy & Costs** - Use a local LLM
3. **Accessibility** - Mobile app for daily use
4. LAUNCH!!!

### Medium-Term (12 Months)
4. **Intelligence** - Learn from usage patterns, rescheduling, etc.
5. **Universality** - Compatibility with all major calendar/task platforms
6. **Community** - Plugin ecosystem and templates

### Long-Term (24 Months)
7. **AI chat integration** - AI as a dedicated life coach and manager

---

## 🚀 Version 1.1 (Q1 2026) - Configuration Automation

**Theme:** Eliminate manual configuration

### Features

#### 1. Dynamic `config.json` Generation
**Problem:** Users must manually edit JSON for their location and spiritual tradition.

**Solution:** Setup wizard generates configuration automatically.

**Implementation:**
```python
# New module: src/core/config_generator.py

class ConfigGenerator:
    def generate_config(
        self,
        location: str,
        tradition: str,
        work_hours: tuple,
        timezone: str
    ) -> dict:
        """Generate complete config based on user inputs."""
        
        # Get prayer times from API
        prayer_times = self._get_prayer_times(location, tradition)
        
        # Generate phase boundaries
        phases = self._generate_phases(work_hours, tradition)
        
        # Create anchors
        anchors = self._create_anchors(prayer_times, tradition)
        
        return {
            'phases': phases,
            'anchors': anchors,
            'timezone': timezone,
            'generated_at': datetime.now().isoformat(),
            'location': location,
            'tradition': tradition
        }
```

**Features:**
- **Location Detection** - Auto-detect via IP or manual input
- **Prayer Time computation** - Based on some calculation using dawn and dusk
- **Tradition Selector** - Islamic (Sunni/Shia), Christian, Buddhist, Hindu, Jewish, Secular
- **Custom Schedules** - Work hours, sleep schedule, preferred phase times
- **Timezone Handling** - Automatic daylight saving adjustments

**UI Flow:**
```
$ python scripts/setup.py

Welcome to Harmonious Day!

1. Location Setup
   Enter city: [Delft, Netherlands]
   Detected timezone: Europe/Amsterdam ✓

2. Spiritual Tradition
   Choose: [1] Islamic  [2] Christian  [3] Buddhist
           [4] Hindu    [5] Jewish     [6] Secular  [7] Custom
   Selection: 1
 
   Fetching prayer times for Delft...
   ✓ Fajr: 05:31  ✓ Zuhr: 13:15  ✓ Asr: 15:45
   ✓ Maghrib: 18:03  ✓ Isha: 20:47

4. Work Schedule
   Work start: [09:00]
   Work end: [17:00]
   Lunch break: [12:30-13:30]

5. Preview Generated Config
   [Shows config.json preview]
   
   Looks good? [Y/n]: Y
   
✓ Configuration saved to config/config.json
✓ Setup complete! Run: python scripts/plan.py
```

## 🏠 Version 1.2 (Q4 2026) - Local LLM Support

**Theme:** Privacy-first offline capability

### Features

#### 1. On-Device LLM Integration
**Problem:** Cloud dependency, privacy concerns, API costs and rate limits.

**Solution:** Run fine-tuned model locally.

**Implementation:**
```python
# New module: src/llm/local_model.py

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

class LocalLLM:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.float16,
            device_map="auto"
        )
    
    def generate_schedule(
        self,
        system_prompt: str,
        world_prompt: str
    ) -> dict:
        """Generate schedule using local model."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": world_prompt}
        ]
        
        inputs = self.tokenizer.apply_chat_template(
            messages,
            return_tensors="pt"
        )
        
        outputs = self.model.generate(
            inputs,
            max_new_tokens=2048,
            temperature=0.0,
            do_sample=False
        )
        
        response = self.tokenizer.decode(outputs[0])
        return self._parse_json_response(response)
```

**Fine-Tuning Dataset:**
Create 1,000+ examples of:
- System prompt + world prompt → valid schedule JSON
- Various constraint scenarios
- Edge cases (overbooked days, no tasks, urgent deadlines)

**Model Selection UI:**

Settings → AI Provider
  ○ Cloud (Groq) - Fast, requires internet but has token limits
  ● Local (GPT-OSS-20B) - Private, offline capable, unlimited


---

## 📱 Version 1.3 (Q2-Q3 2026) - Mobile Application

**Theme:** Harmonious Day in your pocket

### Features

#### 1. React Native Mobile App
**Problem:** Command-line interface not accessible on-the-go.

**Solution:** Native iOS and Android app.

**Core Features:**
- **Dashboard View** - Today's schedule at a glance
- **TO-DO List** - Import from Google, modify after
- **Manage Habits** - Interface for the sheets file
- **Notifications** - Upcoming tasks, prayer times
- **Offline Mode** - View schedules without internet
- **Sync** - Bidirectional sync with Google Calendar

**Screen Flow:**
```
Splash → Auth → Dashboard → Settings
           ↓
    [Today's Schedule]
    - Current phase indicator
    - Next 3 activities
    - Quick regenerate button
           ↓
    [Week View]
    - 7-day overview
    - Habit completion tracking
           ↓
    [Settings]
    - Edit phase times
    - Manage habits
    - Toggle features
```

**Tech Stack:**
- **Framework:** React Native + Expo
- **State:** Redux Toolkit or Zustand
- **UI:** Native Base or React Native Paper
- **Calendar:** `react-native-calendars`
- **Notifications:** Firebase Cloud Messaging
- **Backend:** Firebase or Supabase for sync

**API Design:**
```typescript
// New REST API endpoints

POST /api/schedule/generate
{
  "userId": "user123",
  "date": "2026-03-15",
  "preferences": {
    "urgentOnly": false,
    "skipHabits": false
  }
}

GET /api/schedule/{date}
Response: {
  "entries": [...],
  "generatedAt": "2026-03-15T06:00:00Z",
  "conflicts": []
}

PATCH /api/schedule/{date}/entry/{id}
{
  "startTime": "10:30",
  "endTime": "11:30"
}
```

---

#### 2. Simplified Mobile Orchestrator
**Problem:** Full Python stack too heavy for mobile.

**Solution:** Lightweight TypeScript orchestrator.

**Architecture:**
```
Mobile App (React Native)
    ↓
Backend API (Node.js/Python FastAPI)
    ↓
LLM Service (Groq Cloud or Local)
    ↓
Google APIs
```

**Optimization:**
- Reduce token usage (compress prompts)
- Cache frequent queries
- Background generation (before user wakes)
- Progressive loading (show skeleton → fill data)

---

## 🌍 Version 2.0 (Q1 2027) - Launch In Appstore

**Theme:** Works with everything, everywhere

### Features

#### 1. Multi-Platform Calendar Support
**Problem:** Locked into Google ecosystem.

**Solution:** Support all major platforms.

**Integrations:**
- **Apple Calendar** - iCloud CalDAV
- **Outlook** - Microsoft Graph API
- **Nextcloud** - CalDAV/CardDAV
- **Fastmail** - JMAP
- **Notion** - Notion API
- **Todoist** - Todoist API
- **TickTick** - TickTick API
- **Local .ics** - File-based sync

**Architecture:**
```python
# New abstraction layer

class CalendarAdapter(ABC):
    @abstractmethod
    def get_events(self, start: date, end: date) -> List[CalendarEvent]:
        pass
    
    @abstractmethod
    def create_event(self, event: CalendarEvent) -> str:
        pass

class GoogleCalendarAdapter(CalendarAdapter):
    """Implementation for Google Calendar"""
    
class AppleCalendarAdapter(CalendarAdapter):
    """Implementation for iCloud"""

class NotionAdapter(CalendarAdapter):
    """Implementation for Notion databases"""
```

**Setup Flow:**
```
$ python scripts/setup.py

Choose calendar provider:
  [1] Google Calendar (recommended)
  [2] Apple iCloud
  [3] Microsoft Outlook
  [4] Nextcloud
  [5] Local .ics file
  
Choose task provider:
  [1] Google Tasks
  [2] Todoist
  [3] TickTick
  [4] Notion
  [5] Local CSV
```

---

#### 2. Self-Hosted Backend
**Problem:** Some users want full control.

**Solution:** Docker-based self-hosted version.

**Components:**
```yaml
# docker-compose.yml

services:
  harmonious-api:
    image: harmonious/api:latest
    environment:
      - DB_URL=postgresql://...
      - LLM_PROVIDER=local
    volumes:
      - ./models:/app/models
    ports:
      - "8000:8000"
  
  harmonious-scheduler:
    image: harmonious/scheduler:latest
    depends_on:
      - harmonious-api
    environment:
      - SCHEDULE_TIME=06:00
  
  postgres:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
```

**Features:**
- Web-based dashboard
- Multi-user support
- API access
- Backup/restore
- Health monitoring

**Timeline:** 12 weeks
**Priority:** MEDIUM

---

## 🧠 Version 2.5 (Q2-Q3 2027) - Intelligent Adaptation

**Theme:** Learn from your patterns

### Features

#### 1. Pattern Recognition
**Problem:** AI doesn't learn from past schedules.

**Solution:** ML-based optimization.

**Data Collection:**
```python
class ScheduleMetrics:
    """Track schedule effectiveness"""
    
    def record_completion(
        self,
        task_id: str,
        scheduled_time: datetime,
        actual_time: Optional[datetime],
        completed: bool,
        energy_level: int  # 1-5 user rating
    ):
        """Record task completion data"""
```

**Insights:**
- **Peak Performance Times** - When you complete most tasks
- **Phase Accuracy** - Which phases work best for you
- **Duration Estimates** - Actual vs estimated task times
- **Habit Adherence** - Which habits stick
- **Energy Patterns** - When you rate energy highest

**Personalization:**
```
After 30 days, Harmonious Day learns:

✓ You're most productive 08:00-11:00 (not 09:00-13:00)
✓ Exercise works better in evening for you
✓ You underestimate coding tasks by 30%
✓ Friday afternoons are low-energy
✓ Morning meditation completion: 95%

Apply learned preferences? [Y/n]
```

**Privacy:**
- All learning happens locally
- Opt-in feature
- Export/delete data anytime

**Timeline:** 8-10 weeks
**Priority:** MEDIUM

---

#### 2. Predictive Scheduling
**Problem:** Manual task entry still required.

**Solution:** AI suggests tasks before you add them.

**Features:**
- **Recurring Pattern Detection** - "You usually review PRs on Monday morning"
- **Project Phase Prediction** - "Project Alpha entering testing phase, schedule QA time?"
- **Deadline Warnings** - "Task X likely needs 2 more days, not 1"
- **Energy Optimization** - "Schedule creative work earlier based on your patterns"

**Timeline:** 6 weeks (after pattern recognition)
**Priority:** LOW-MEDIUM

---

## 🔧 Version 3.0 (Q4 2027) - Ecosystem & Polish

**Theme:** Community, integrations, excellence

### Features

#### 1. Plugin System
**Problem:** Can't customize without forking.

**Solution:** Plugin architecture.

**Plugin Types:**
- **Calendar Providers** - Add new calendar services
- **Task Sources** - Pull from custom tools
- **LLM Providers** - Swap AI backends
- **Notification Channels** - Custom alerts (Slack, Discord, SMS)
- **Phase Definitions** - Custom energy models
- **Visualizations** - Custom schedule views

**Example Plugin:**
```python
# plugins/toggl_integration.py

from harmonious.plugin import Plugin

class TogglIntegration(Plugin):
    """Import time tracking data from Toggl"""
    
    def get_tasks(self) -> List[Task]:
        """Fetch recent Toggl entries"""
        entries = self.toggl_api.get_entries(days=7)
        return [self._convert_to_task(e) for e in entries]
```

---

## 🎨 Design & UX Improvements (Ongoing)

### Web Dashboard (Q2 2026)
- Visual schedule editor
- Drag-and-drop rescheduling
- Analytics dashboard
- Habit tracking charts
- Configuration UI

### Voice Integration (Q3 2027)
- "Hey Siri/Google, generate my schedule"
- "Alexa, what's my next task?"
- Voice task entry
- Schedule summaries

### Wearable Support (Q4 2027)
- Apple Watch complications
- Android Wear tiles
- Phase change notifications
- Quick task completion

---

## Business
- We sell the whole app for $1.

---

## 🚧 Technical Debt & Infrastructure

### Immediate (Q1 2026)
- [ ] Migrate to FastAPI for better async support
- [ ] Add database layer (PostgreSQL) for schedule history
- [ ] Implement proper error tracking (Sentry)
- [ ] Set up analytics (PostHog or Mixpanel)
- [ ] Create comprehensive API documentation (OpenAPI)

### Q2-Q3 2026
- [ ] Containerization (Docker) for all components
- [ ] Kubernetes deployment configs
- [ ] Implement caching layer (Redis)
- [ ] Add rate limiting and abuse prevention
- [ ] Create monitoring dashboard (Grafana)

### Q4 2026 - 2027
- [ ] Microservices architecture for scale
- [ ] Event-driven architecture (message queues)
- [ ] Multi-region deployment
- [ ] CDN for model distribution
- [ ] Load balancing and auto-scaling

---

## 🌟 Community & Ecosystem

### Documentation
- [ ] Video tutorials
- [ ] Community cookbook (use cases)
- [ ] Developer guide for plugins
- [ ] Troubleshooting wiki
- [ ] Translation to 10+ languages

### Community Building
- [ ] Discord server
- [ ] Monthly community calls
- [ ] Contributor recognition program
- [ ] Bug bounty program
- [ ] Annual conference/meetup

### Partnerships
- [ ] Productivity tool integrations
- [ ] Religious organizations
- [ ] University research partnerships
- [ ] Corporate wellness programs

---

## 💡 Future Research Areas

### Advanced AI
- Multi-day optimization (week-long planning)
- Collaborative filtering for habit suggestions
- Natural language task input
- Contextual awareness (weather, location, health data)

### Novel Scheduling Approaches
- Circadian rhythm optimization
- Seasonal energy patterns
- Group flow state detection
- Adaptive difficulty scaling

### Wellness Integration
- Sleep quality correlation
- Stress level tracking
- Physical health metrics (HR, HRV)
- Mental health indicators

---

## 📅 Release Schedule Summary

| Version | Release | Focus | Key Features |
|---------|---------|-------|--------------|
| **1.1** | Q1 2026 | Config Automation | Dynamic config generation, tradition templates |
| **1.2** | Q4 2026 | Privacy | Local LLM support, offline mode |
| **1.3** | Q2-Q3 2026 | Mobile | React Native app, push notifications |
| **2.0** | Q1 2027 | Universal | Multi-platform, self-hosted |
| **2.5** | Q2-Q3 2027 | Intelligence | Pattern learning, predictive scheduling |
| **3.0** | Q4 2027 | Ecosystem | Plugins, polish, community |

---

## 🤝 How to Contribute

### Priority Areas for Contributors

**High Priority:**
1. Mobile app development (React Native)
2. Local LLM integration
3. Calendar adapter implementations
4. Translation to new languages

**Medium Priority:**
5. UI/UX design for web dashboard
6. Documentation and tutorials
7. Template creation for traditions
8. Testing and bug reports

**Nice to Have:**
9. Plugin development
10. Voice assistant integration
11. Wearable support
12. Advanced analytics

### Getting Involved
1. Join [Discord community](#)
2. Check [Good First Issues](https://github.com/yourusername/harmonious-day/labels/good%20first%20issue)
3. Read [Contributing Guide](CONTRIBUTING.md)
4. Attend monthly community calls

---

## 📝 Notes & Considerations

### Design Philosophy
- **Privacy First** - Local processing whenever possible
- **Universal** - Works for all traditions and none
- **Sustainable** - Balance features with maintainability
- **Open** - Core remains open source always

### Technical Decisions
- **Python Core** - Mature, stable, good ML ecosystem
- **Mobile Native** - React Native for code reuse
- **API-First** - Enable third-party integrations
- **Modular** - Each feature can work independently

### Risks & Mitigation
- **LLM Costs** - Mitigated by local models
- **API Rate Limits** - Cached, batched requests
- **User Adoption** - Focus on specific niches first
- **Maintenance Burden** - Strong architecture, good tests

---

**Last Updated:** November 2025  
**Next Review:** March 2026  
**Roadmap Owner:** Core Team

*This roadmap is a living document and will evolve based on user feedback, technical constraints, and community contributions.*
