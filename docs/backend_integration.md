# Harmonious Day - Complete Architecture

**Single Repository • Local-Only AI • 3-Person Team • Minimal Memory Footprint**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        USERS                                │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
      ┌────▼─────┐                  ┌─────▼─────┐
      │  iOS App │                  │ Android   │
      │(React    │                  │ App (RN)  │
      │ Native)  │                  └─────┬─────┘
      └────┬─────┘                        │
           │         (same binary)        │
           └────────────┬─────────────────┘
                        │
        ┌───────────────▼───────────────┐
        │  Local SQLite Cache           │
        │  + Redux Store                │
        │  (Offline-first)              │
        └───────────────┬───────────────┘
                        │
        ┌───────────────▼────────────────────┐
        │   Mobile AI Inference              │
        │  (Transformers.js)                 │
        │ - Scheduler (T5-Small, 50MB)      │
        │ - Coach (DistilGPT-2, 100MB)      │
        └───────────────┬────────────────────┘
                        │ HTTP
        ┌───────────────▼──────────────────────┐
        │     FastAPI Backend (Python)         │
        │        Port: 8000                    │
        │                                      │
        │ ├─ /api/habits (CRUD)               │
        │ ├─ /api/journal (CRUD)              │
        │ ├─ /api/todos (CRUD)                │
        │ ├─ /api/calendar (CRUD)             │
        │ ├─ /api/chat (POST messages)        │
        │ └─ /api/sync (batch sync)           │
        │                                      │
        │ ├─ Models (load from /models/)      │
        │ │  ├─ scheduler-t5.onnx (50MB)     │
        │ │  └─ coach-distilgpt2.onnx (100MB)│
        │ │                                    │
        │ └─ Google APIs                      │
        │    ├─ Calendar (read/write)         │
        │    ├─ Tasks (read/write)            │
        │    └─ Sheets (read habits)          │
        └───────────────┬──────────────────────┘
                        │
        ┌───────────────▼──────────────────────┐
        │       PostgreSQL Database            │
        │  (Habits, Journal, Todos, Calendar) │
        │  (Sync metadata, user settings)     │
        └──────────────────────────────────────┘
```

---

## Repository Structure (Monorepo)

```
harmonious-day/
├── backend/                    # Person 1: Backend Dev
│   ├── src/
│   │   ├── main.py            # FastAPI app
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   ├── schemas.py         # Pydantic request/response
│   │   ├── api/
│   │   │   ├── habits.py
│   │   │   ├── journal.py
│   │   │   ├── todos.py
│   │   │   ├── calendar.py
│   │   │   ├── chat.py
│   │   │   └── sync.py        # Batch sync endpoint
│   │   ├── services/
│   │   │   ├── ai_service.py  # T5 + DistilGPT2 inference
│   │   │   ├── google_service.py
│   │   │   ├── schedule_service.py
│   │   │   └── sync_service.py
│   │   ├── db/
│   │   │   ├── database.py    # Connection + session
│   │   │   ├── crud.py        # Query helpers
│   │   │   └── alembic/       # Migrations
│   │   ├── utils/
│   │   │   ├── logger.py
│   │   │   └── decorators.py
│   │   └── config.py          # Settings, env vars
│   │
│   ├── models/                # AI models (git-lfs)
│   │   ├── scheduler-t5.onnx  (50MB quantized)
│   │   └── coach-distilgpt2.onnx (100MB quantized)
│   │
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── README.md
│
├── mobile/                     # Persons 2-3: Mobile Dev (2 people)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── navigation/
│   │   │   └── RootNavigator.tsx
│   │   ├── screens/            # 5 screens (Habits, Journal, Calendar, Todo, Chat)
│   │   ├── components/         # Shared UI components
│   │   ├── redux/
│   │   │   ├── store.ts
│   │   │   └── slices/         # habitSlice, journalSlice, etc.
│   │   ├── services/
│   │   │   ├── api/
│   │   │   │   └── apiClient.ts
│   │   │   ├── ai/
│   │   │   │   ├── AIServiceManager.ts
│   │   │   │   └── LocalInference.ts (Transformers.js)
│   │   │   ├── sync/
│   │   │   │   └── SyncEngine.ts
│   │   │   └── storage/
│   │   │       └── dbService.ts  (SQLite)
│   │   ├── db/
│   │   │   ├── schema.ts       # SQLite tables
│   │   │   └── queries.ts      # CRUD helpers
│   │   ├── models/
│   │   │   └── types.ts        # TypeScript interfaces
│   │   ├── theme/
│   │   └── utils/
│   │
│   ├── __tests__/
│   ├── app.json
│   ├── package.json
│   └── README.md
│
├── shared/                     # SHARED DEFINITIONS (both teams)
│   ├── API_SPEC.md            # Request/response formats
│   ├── DATA_MODELS.md         # Schema for all entities
│   ├── SYNC_PROTOCOL.md       # Offline sync format
│   └── constants.ts / .py     # Enums (Phase, Priority, etc.)
│
├── docs/
│   ├── ARCHITECTURE.md        # This file
│   ├── DEVELOPMENT.md         # Setup guide
│   ├── DEPLOYMENT.md
│   └── API.md
│
├── docker-compose.yml         # Local dev: backend + postgres
├── .github/workflows/         # CI/CD
│   ├── backend-tests.yml
│   ├── mobile-tests.yml
│   └── deploy.yml
│
├── .gitignore
├── README.md
└── CONTRIBUTING.md
```

---

## Tech Stack

### Backend (Person 1)
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL + SQLAlchemy ORM
- **AI:** ONNX Runtime (local inference only)
- **APIs:** Google Calendar, Tasks, Sheets
- **Deployment:** Docker + Railway/Render (or VPS)

### Mobile (Persons 2-3)
- **Framework:** React Native 0.72 + Expo SDK 49
- **State:** Redux Toolkit
- **Database:** React Native SQLite
- **UI:** React Native Paper + Reanimated v2
- **AI:** Transformers.js (on-device inference)

### Shared
- **API:** REST + JSON
- **Auth:** JWT (issued by backend)
- **Models:** Git LFS (models tracked with Git, stored efficiently)

---

## Data Models (Single Source of Truth)

All models defined in `shared/DATA_MODELS.md`. Both teams implement from this spec.

### Core Entities

```python
# Python (Backend)
class Habit(Base):
    id: str
    user_id: str
    title: str
    duration_min: int
    frequency: str  # "Daily" | "Weekly"
    ideal_phase: str  # "WOOD" | "FIRE" | "EARTH" | "METAL" | "WATER"
    created_at: datetime
    updated_at: datetime
    sync_status: str  # "pending" | "synced" | "failed"

# TypeScript (Mobile)
export interface Habit {
  id: string;
  userId: string;
  title: string;
  durationMin: number;
  frequency: "Daily" | "Weekly";
  idealPhase: Phase;
  createdAt: Date;
  updatedAt: Date;
  syncStatus: "pending" | "synced" | "failed";
}
```

**Repeat for:** JournalEntry, TodoItem, CalendarEvent, ChatMessage, User

---

## API Contracts (Backend)

All endpoints return `{ success: boolean, data?, error? }`. No pagination initially.

```
GET    /api/habits                    → Habit[]
POST   /api/habits                    → Habit
PATCH  /api/habits/{id}               → Habit
DELETE /api/habits/{id}               → { success }

GET    /api/journal/entries           → JournalEntry[]
POST   /api/journal/entries           → JournalEntry
PATCH  /api/journal/entries/{id}      → JournalEntry

GET    /api/todos                     → TodoItem[]
POST   /api/todos                     → TodoItem
PATCH  /api/todos/{id}                → TodoItem

GET    /api/calendar/events?date=     → CalendarEvent[]
PATCH  /api/calendar/events/{id}      → CalendarEvent

POST   /api/chat                      → { response: string }

POST   /api/sync                      → { synced: 100, failed: 0 }

POST   /api/auth/login                → { token, userId, expiresIn }
```

---

## Offline Sync Protocol

Mobile stores changes locally, queues them, syncs when connected.

```typescript
// Local queue in mobile SQLite
interface QueuedSync {
  id: string;
  action: "CREATE" | "UPDATE" | "DELETE";
  entity: "habit" | "journal" | "todo" | "calendar_event";
  entityId: string;
  payload: any;
  timestamp: number;
  status: "pending" | "synced" | "failed";
}

// Backend receives batch
POST /api/sync
{
  syncs: [
    { action: "CREATE", entity: "habit", payload: {...} },
    { action: "UPDATE", entity: "journal", entityId: "j123", payload: {...} }
  ]
}

// Backend responds
{
  success: true,
  synced: [
    { localId: "h456", serverId: "h789" }  // Map local to server IDs
  ],
  conflicts: []  // Handle if needed
}
```

---

## AI Models: Local Only

**Two quantized ONNX models in `/backend/models/`:**

### Scheduler (T5-Small)
- **Size:** 50MB (quantized int8)
- **Input:** Calendar events, tasks, habits, Wu Xing phases
- **Output:** Time-blocked schedule (JSON)
- **Latency:** 2-3 seconds (backend), 3-5 seconds (mobile)
- **Used:** Daily schedule generation (POST /api/schedule/generate)

### Coach (DistilGPT-2)
- **Size:** 100MB (quantized int8)
- **Input:** User message + context (recent journal, habit stats)
- **Output:** Coaching response (text)
- **Latency:** 1-2 seconds (backend), 2-3 seconds (mobile)
- **Used:** Chat window (POST /api/chat)

**Backend:** Loads models at startup. Uses ONNX Runtime (CPU inference).

**Mobile:** Downloads on first launch. Uses Transformers.js for inference. Cached locally.

---

## Development Workflow (3-Person Team)

### Person 1: Backend Developer
1. **Day 1-2:** Setup FastAPI, PostgreSQL, Google OAuth
2. **Day 3-5:** Implement CRUD endpoints (habits, journal, todos, calendar)
3. **Day 6-7:** Add AI service (load T5 + DistilGPT2, test inference)
4. **Day 8-10:** Integrate Google APIs (Calendar, Tasks, Sheets)
5. **Day 11:** Deploy to Railway/Render, setup CI/CD
6. **Ongoing:** Review mobile API calls, fix bugs, optimize

### Persons 2-3: Mobile Developers (Parallel)
1. **Day 1-3:** Setup React Native, navigation, Redux store
2. **Day 4-5:** Build Habit screen (list, detail, add/edit)
3. **Day 6-7:** Build Journal screen (editor, mood, AI insights)
4. **Day 8-9:** Build Calendar screen (time blocks, phase progress)
5. **Day 10:** Build Todo + Chat screens
6. **Day 11-12:** Connect to backend API, test offline sync
7. **Day 13-14:** Fix bugs, performance, polish
8. **Ongoing:** Mobile testing, device compatibility

### All Together
- **Daily standup:** 15 min (async in Slack or sync in Discord)
- **Code review:** GitHub PRs before merge
- **Integration testing:** Test together every 2 days

---

## Memory Footprint

**Backend (Server):**
- Python + FastAPI: ~100MB
- PostgreSQL: ~200MB (for typical user dataset)
- T5 model: 50MB
- DistilGPT2 model: 100MB
- **Total: ~500MB** (can run on $5/month VPS)

**Mobile:**
- App: 30MB (APK/IPA)
- T5 model: 50MB (downloaded on first launch)
- DistilGPT2 model: 100MB (downloaded on first launch)
- Local SQLite: 5-20MB (cached data)
- **Total: ~200MB app + 150MB models** (fits on any modern device)

---

## Deployment Architecture

### Backend (Production)

**Simple Option: Railway.app**
```yaml
# railway.toml
[build]
builder = "dockerfile"

[deploy]
startCommand = "uvicorn src.main:app --host 0.0.0.0 --port $PORT"
```

```bash
railway login
railway init
railway add postgres
git push  # Auto-deploys
```

**Environment Variables:**
```
DATABASE_URL=postgresql://...
GOOGLE_CREDENTIALS_JSON={...}
GOOGLE_SHEET_ID=...
JWT_SECRET=...
```

### Mobile (Production)

**EAS Build (Expo):**
```bash
eas build --platform ios --auto-submit
eas build --platform android --auto-submit
```

**App Store:** TestFlight (iOS) → App Store
**Play Store:** Internal testing → Production release

---

## Data Flow Example: User Completes a Habit

```
1. User taps ☐ checkbox in mobile app

2. Mobile:
   ├─ Update Redux store (optimistic)
   ├─ Insert into local SQLite
   ├─ Add to sync queue
   └─ If online: immediately POST /api/sync

3. Network (if online):
   └─ POST /api/sync { action: "UPDATE", entity: "habit", ... }

4. Backend:
   ├─ Update PostgreSQL
   ├─ Update calendar event (if exists)
   └─ Return { success: true, synced: [...] }

5. Mobile:
   ├─ Mark queue item as "synced"
   ├─ Show success animation
   └─ Increment streak display

6. If offline:
   ├─ Queue stays "pending"
   ├─ Show "⊗ Will sync when online"
   └─ When reconnected, auto-sync
```

---

## Google API Integration

**Only three Google APIs (read/write):**

1. **Google Calendar**
   - Read: Fetch existing calendar events (avoid conflicts)
   - Write: Create/update/delete scheduled time blocks

2. **Google Tasks**
   - Read: Import user's existing tasks
   - Write: Mark tasks complete in our app

3. **Google Sheets**
   - Read: Fetch user's habit list (from a template sheet they create)
   - Fallback: If no sheet, use our local habit database

**Setup:**
- OAuth 2.0 flow in backend
- Store refresh token securely
- Request scopes: `calendar`, `tasks`, `spreadsheets`

---

## Security Notes

**Secrets (backend .env):**
- `DATABASE_URL` (PostgreSQL connection)
- `GOOGLE_CREDENTIALS_JSON` (OAuth key)
- `JWT_SECRET` (token signing)

**Mobile:**
- Stores JWT token in encrypted storage (react-native-keychain)
- All API calls include `Authorization: Bearer {token}`
- No API keys in mobile app

**Data:**
- All user data encrypted at rest (PostgreSQL, mobile SQLite)
- HTTPS only (enforced by backend)
- No sensitive data in logs

---

## Testing Strategy

**Backend (Person 1):**
- Unit tests: 70%+ coverage (pytest)
- Integration tests: API endpoints with mock DB
- Run: `pytest --cov`

**Mobile (Persons 2-3):**
- Component tests: Navigation, screens (React Native Testing Library)
- Integration tests: API client, sync queue (Jest)
- E2E tests: Full user flows (Detox, optional)
- Run: `npm test`

**Together:**
- Manual testing: Full flow (create habit → sync → verify on server)
- Device testing: iOS + Android, old + new devices

---

## Key Decision Rationale

| Decision | Why |
|----------|-----|
| Monorepo | Shared types, easier team coordination, single CI/CD |
| Local AI only | No cloud costs, privacy, offline-capable, <200MB memory |
| PostgreSQL | Persistent, supports complex queries, easy migrations |
| SQLite mobile | Works offline, no sync issues, lightweight |
| ONNX quantized | 50-100MB models fit on device, fast inference |
| Railway/Render | Cheap ($5-10/mo), easy for small team, auto-deploy |
| Expo | Managed React Native, no native build complexity |
| JWT auth | Stateless, simple, no session management |

---

## Success Metrics

- **Backend:** Handles 100 concurrent users, <500ms response time, 99% uptime
- **Mobile:** <2s app startup, 60fps scrolling, offline works, <150MB memory
- **AI:** Scheduler accuracy 85%+, Coach responses relevant, latency <3s
- **Sync:** 100% data integrity, conflicts resolved correctly, offline queue works

---

## GitHub Page Summary

```markdown
# Harmonious Day Architecture

## Quick Links
- [Development Setup](docs/DEVELOPMENT.md)
- [API Specification](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Data Models](shared/DATA_MODELS.md)

## Tech Stack
- Backend: FastAPI + PostgreSQL + ONNX
- Mobile: React Native + SQLite + Transformers.js
- Deployment: Railway + EAS Build

## Repository Structure
- `backend/` - FastAPI server (Person 1)
- `mobile/` - React Native app (Persons 2-3)
- `shared/` - API specs, data models, constants
- `docs/` - Documentation

## Key Facts
- 3-person team, 4-week sprint to MVP
- ~500MB server memory, ~200MB mobile + models
- Local AI only (no cloud), Google APIs only
- Offline-first with batch sync

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.
```

---

## Next Steps to Start

1. **Person 1:** Clone repo → `cd backend` → `cp .env.example .env` → `docker-compose up`
2. **Persons 2-3:** Clone repo → `cd mobile` → `npm install` → `npx expo start`
3. **All:** Read `shared/DATA_MODELS.md` together (5 min)
4. **All:** Daily standup (Day 1)
5. **Person 1:** Push first API endpoint by Day 2
6. **Persons 2-3:** Push first screen by Day 3

---

**Architecture Document Last Updated:** 2024
**Team:** 1 Backend Dev + 2 Mobile Devs
**Target Completion:** 4 weeks MVP