Harmonious Day - Mobile AI Life Manager

"Your day, harmoniously organized by AI. Offline. Private. Yours."

https://img.shields.io/badge/React%20Native-0.72-blue.svg
https://img.shields.io/badge/Expo-49-orange.svg
https://img.shields.io/badge/AI-Local%20Only-green.svg
https://img.shields.io/badge/License-MIT-purple.svg

A beautiful mobile app that uses local AI to schedule your day around your habits, tasks, and spiritual rhythm using Wu Xing philosophy and prayer times.

https://via.placeholder.com/800x400?text=Harmonious+Day+App+Screens

🎯 Why Harmonious Day?

· 🔄 AI-Powered Scheduling: One-tap daily planning using local AI
· 📱 100% Offline: No subscriptions, no cloud costs, no data mining
· 🌅 Wu Xing Integration: Schedule tasks according to natural energy phases
· 🕌 Multi-Tradition Support: Islamic prayers, Christian hours, Secular rhythms
· ✅ Habit Tracking: Build streaks with optimal timing
· 🗣️ AI Chat: Get coaching and schedule adjustments

🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/Jelterminator/Harmonious-Day-Life-Manager
cd harmonious-day-mobile

# Install dependencies
npm install

# Start development
npm start
```

Scan the QR code with Expo Go to run on your device.

📱 Core Features

1. Habit Tracker

· Track daily habits with optimal Wu Xing timing
· Visual streak counter and completion stats
· Habit grouping and priority settings

2. Journal

· Daily reflections with mood tracking
· AI-powered insights based on your entries
· Export and backup capabilities

3. Calendar View

· Beautiful daily schedule visualization
· Wu Xing phase indicators
· Drag-and-drop rescheduling

4. To-Do List

· Google Tasks integration
· Priority-based task management
· AI scheduling suggestions

5. AI Chat

· Local AI coach for daily guidance
· Schedule optimization conversations
· Habit formation advice

🏗️ Architecture

```
harmonious-day-mobile/
├── src/
│   ├── components/          # Reusable UI components
│   ├── screens/            # Five main app screens
│   ├── services/           # Business logic & APIs
│   ├── stores/             # State management (Zustand)
│   ├── utils/              # Helper functions
│   └── assets/             # Images, fonts, etc.
├── docs/                   # Documentation
└── tests/                  # Test suites
```

🧠 Local AI Integration

Model Architecture

```javascript
// Using Transformers.js for on-device inference
import { pipeline } from '@xenova/transformers';

class LocalAIService {
  async generateSchedule(events, tasks, habits, phases) {
    const prompt = this.buildSchedulingPrompt(events, tasks, habits, phases);
    const generator = await pipeline('text-generation', 'Xenova/t5-small');
    const output = await generator(prompt, { max_length: 512 });
    return this.parseSchedule(output[0].generated_text);
  }
  
  async chat(message, context) {
    const prompt = this.buildChatPrompt(message, context);
    const generator = await pipeline('text-generation', 'Xenova/gpt2');
    const response = await generator(prompt, { max_length: 256 });
    return response[0].generated_text;
  }
}
```

Model Choices

· Scheduling: Fine-tuned T5-small (~150MB)
· Chat: DistilGPT-2 (~350MB)
· Total App Size: <100MB with models

🔧 Setup for Development

Prerequisites

· Node.js 18+
· npm or yarn
· Expo CLI
· Android Studio / Xcode (for emulators)

Installation

```bash
# 1. Clone repository
git clone https://github.com/Jelterminator/Harmonious-Day-Life-Manager
cd harmonious-day-mobile

# 2. Install dependencies
npm install

# 3. Setup environment
cp .env.example .env
# Configure your environment variables

# 4. Start development
npm start
```

Environment Configuration

```env
# Google APIs (optional)
GOOGLE_OAUTH_CLIENT_ID=your_google_client_id
GOOGLE_CALENDAR_API_KEY=your_calendar_api_key

# App Settings
APP_ENV=development
AI_MODEL_PATH=./models/scheduling-model
```

📁 Project Structure Deep Dive

Screens Architecture

```javascript
// Each screen follows this structure:
screens/
├── HabitTracker/
│   ├── HabitListScreen.js     // Main list view
│   ├── HabitFormScreen.js     // Add/edit a habit
│   ├── HabitStatsScreen.js    // Analytics
│   └── components/            // Screen-specific components
```

Services Layer

```javascript
services/
├── ai/
│   ├── LocalAIService.js      // AI model management
│   ├── PromptBuilder.js       // Construct AI prompts
│   └── ResponseParser.js      // Parse AI responses
├── google/
│   ├── CalendarService.js     // Google Calendar integration
│   ├── TasksService.js        // Google Tasks integration
│   └── AuthService.js         // OAuth authentication
├── storage/
│   ├── SecureStorage.js       Encrypted local storage
│   ├── HabitRepository.js     // Habit data management
│   └── JournalRepository.js   // Journal entry management
└── notifications/
    ├── Scheduler.js           // Local notifications
    └── ReminderService.js     // Smart reminders
```

🎨 UI/UX Design System

Color Palette

```javascript
const colors = {
  primary: '#6366F1',      // Indigo
  secondary: '#10B981',    // Emerald
  background: '#F8FAFC',   // Slate 50
  surface: '#FFFFFF',      // White
  error: '#EF4444',        // Red
  warning: '#F59E0B',      // Amber
  wuXing: {
    wood: '#22C55E',       // Green
    fire: '#DC2626',       // Red
    earth: '#D97706',      // Amber
    metal: '#6B7280',      // Gray
    water: '#3B82F6'       // Blue
  }
};
```

Component Library

We use NativeBase for consistent, accessible components:

```bash
npm install native-base
npm install react-native-svg
npm install react-native-safe-area-context
```

🔌 Integration Points

Google APIs

```javascript
// src/services/google/CalendarService.js
import { GoogleSignin } from '@react-native-google-signin/google-signin';

export class CalendarService {
  async getEvents(date) {
    await this.ensureAuth();
    const response = await fetch(
      `https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin=${date}T00:00:00Z&timeMax=${date}T23:59:59Z`
    );
    return await response.json();
  }
}
```

Local AI Models

```javascript
// Models are downloaded on first use and cached locally
// src/services/ai/ModelManager.js
export class ModelManager {
  async loadModel(modelName) {
    const modelPath = await this.downloadModelIfNeeded(modelName);
    return await pipeline('text-generation', modelPath);
  }
}
```

🧪 Testing

```bash
# Unit tests
npm test

# E2E tests (with Maestro)
npx @maestro-io/cli test maestro/

# AI model testing
npm run test:ai
```

📦 Building for Production

```bash
# Build for Android
npm run build:android

# Build for iOS
npm run build:ios

# Generate APK/IPA
npm run build:production
```

🔒 Security & Privacy

· Data Storage: All data stored locally with React Native MMKV
· Encryption: AES-256 encryption for sensitive data
· Permissions: Minimal required permissions
· Analytics: Optional, anonymized usage data

🤝 Contributing

We love contributions! Please see our Contributing Guide for details.

Development Workflow

1. Fork the repository
2. Create a feature branch (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch (git push origin feature/amazing-feature)
5. Open a Pull Request

📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments

· Wu Xing philosophy integration
· Local AI models from Hugging Face Transformers.js
· React Native community for excellent tools
· Contributors and testers

---

Built with ❤️ by Jelterminator

---

Documentation

📚 Additional Documentation

· 🚀 Getting Started Guide
· 🏗️ Architecture Deep Dive
· 🧠 AI Integration Guide
· 📱 Screen Specifications
· 🔌 API Reference
· 🎨 Design System
· 🧪 Testing Guide
· 🚀 Deployment Guide

🆘 Support

· Discord Community
· GitHub Issues
· Documentation

---

<div align="center">

⭐ Don't forget to star this repo if you find it helpful!

</div>