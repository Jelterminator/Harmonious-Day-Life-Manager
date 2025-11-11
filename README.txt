AI Life Orchestrator: The Harmonious Day Planner

Project Goal

To create an intelligent orchestration service that uses the Harmonious Day Philosophy (Deen & Dao) to gather all of the user's digital data (tasks, habits, appointments) and generate an optimal, fully scheduled daily plan, which is then written back to the user's Google Calendar.

1. The Core Philosophy: The Harmonious Day

The scheduling logic is governed by the Five Element Theory (Dao) overlaid with Islamic anchors (Deen), prioritizing balance (Mizan) and flow (Wu Wei).

| Phase | Time Block | Elemental Quality | Anchor | Ideal Tasks |
| WOOD | 05:30 – 09:00 | Growth, Vitality | Fajr | Spiritual, Planning, Growth |
| FIRE | 09:00 – 12:00 | Peak Energy, Focus | Deep Work Start | Deep Work, Pomodoro (High-Focus) |
| EARTH | 12:00 – 15:00 | Stability, Nourishment | Zuhr, Lunch | Spiritual, Integration, Rest |
| METAL | 15:00 – 17:00 | Precision, Organization | Asr | Admin, Planning, Refinement |
| WATER | 17:00 – 21:30 | Rest, Wisdom, Transition | Maghrib, Isha | Training, Reflection, Deep Rest |

2. Current State (Step 2 Complete)

We have successfully built the data collection and authentication layer, resulting in the comprehensive "World Prompt."

A. Technical Assets

credentials.json & token.json: Full OAuth 2.0 authentication is complete and persistent.

auth.py: Handles Google API authorization.

config.json: The machine-readable "Rules Engine" containing the phases, anchors, and the specific daily "Harde Sport" schedule.

orchestrator.py: The main script that performs all data aggregation.

B. Functionality Achieved

Google Authentication: Successful read/write access to Calendar and Sheets, and readonly access to Tasks.

Data Fetching: Successfully pulls:

Today's schedule from Google Calendar (Anchor Events).

All open tasks from Google Tasks (Task List).

The core philosophy and specific daily sport from config.json.

The Habit Database from Google Sheets is now loading successfully.

Prompt Assembly: A massive, structured "World Prompt" is generated, containing all constraints and data, ready to be sent to the AI model.

3. Key Challenges and Design Decisions

A. Persistent Bug (Sheets 400 Error) - RESOLVED

The initial error (HttpError 400: Unable to parse range: Habits!A1:G100) is RESOLVED. The Google Sheet tab was successfully renamed to "Habits," ensuring the habit data is now correctly loaded into the World Prompt.

B. Scheduling Philosophy: The "Bending" Rule

The core design challenge identified is the need for a flexible schedule that can handle large, splittable creative projects. The philosophy: "The schedule should be able to bend, bend, bend and never break."

Solution Design: We agreed to structure the AI prompt with explicit rules on priority (P1-P4), task splitting (long tasks must be broken into max 90-minute chunks), and phase flexibility (allowing high-priority tasks to shift one phase boundary if necessary). This ensures the AI makes realistic and robust schedules.

4. Next Steps (Roadmap)

| Step | Title | Action | Status |
| 3 | Integrate DeepSeek API | Build the function in orchestrator.py to send the World Prompt to the DeepSeek API, receive the schedule as a JSON array, and handle structured output. | CURRENT FOCUS |
| 4 | Execution Phase | Implement the logic to read the resulting JSON schedule and write the new entries (tasks and habits) back into the user's Google Calendar. | Upcoming |
| 5 | Maintenance | Clean up code, add robust error handling, and plan the long-term HAY-Planner database. | Final Stage |