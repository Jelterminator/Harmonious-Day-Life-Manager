# 🌿 Harmonious Day - Quick Start

## ⚡ Super Fast Setup (10 minutes total)

### Step 1: Run Setup (Just Once)

```bash
python setup.py
```

The wizard will walk you through **4 simple steps**:

1. ✅ **Auto-install packages** (happens automatically)
2. ✅ **Get Groq API key** (opens website, free signup, paste key)
3. ✅ **Connect Google** (guided 3-minute setup, creates habit sheet)
4. ✅ **Verify** (checks everything works)

---

## 📋 What You'll Need

### A. Groq API Key (2 minutes, FREE)

The wizard will open the website for you. Just:
1. Sign up with email (no credit card)
2. Click "Create API Key"
3. Copy & paste when prompted

### B. Google Cloud Setup (3 minutes, ONE-TIME)

The wizard guides you step-by-step to:

1. **Create a project** (just a container, free forever)
2. **Enable 3 APIs** (Calendar, Tasks, Sheets - wizard opens each page)
3. **Get OAuth credentials** (one file download)

**Why?** Google requires this for security - ensures only YOU can access YOUR data.

**Don't worry!** The wizard shows exactly what to click at each step.

---

## 🎯 Daily Usage

After setup, just run:

```bash
python plan.py
```

This generates your optimized schedule and writes it to Google Calendar!

---

## 📊 Your Habit Sheet

The setup wizard automatically creates:
**"Harmonious Day: Habit Database"** in your Google Sheets

Comes with **18 universal starter habits**:
- Morning meditation & reading
- Light exercise & walks
- Meal breaks
- Evening reflection & journaling
- Weekly review

**Customize anytime!** Edit the sheet to add your own habits.

---

## 🪟 Windows Users

Even easier - just double-click:
1. **SETUP.bat** (first time)
2. **PLAN.bat** (daily)

---

## ❓ Troubleshooting

### "ModuleNotFoundError"
→ Run `python setup.py` - it auto-installs packages

### "credentials.json not found"
→ The wizard will guide you through getting it (Step 3)

### "Authentication failed"
→ During Google login, you'll see "App isn't verified" - this is normal!
→ Click: Advanced → Go to Harmonious Day (unsafe)
→ It's YOUR app, totally safe

### "Can't find habit sheet"
→ The wizard creates it automatically
→ Check your Google Sheets for "Harmonious Day: Habit Database"

### Still stuck?
→ Read [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 🎨 Customize Your Day

### Update Prayer/Anchor Times
Edit `config.json` - adjust times for your location:
```json
{"name": "Fajr", "time": "~05:30-5:40", "phase": "Wood"}
```

### Change Phase Times
Also in `config.json`:
```json
{"name": "🌳 WOOD", "start": "05:30", "end": "09:00"}
```

### Adjust AI Behavior
Edit `system_prompt.txt` to change how tasks are scheduled

---

## 📁 What Gets Created

After setup:
```
✓ .env                    # Your Groq API key
✓ token.json              # Google authentication
✓ credentials.json        # OAuth credentials (you download)
✓ (Google Sheet)          # "Harmonious Day: Habit Database"
```

All secure, all local (except the Google Sheet).

---

## 🚀 Pro Tips

1. **Run daily** - Best results when you run `plan.py` each morning
2. **Track effort** - Add time estimates to tasks: `Task name (2h)`
3. **Set deadlines** - Google Tasks with deadlines get higher priority
4. **Tweak habits** - Edit your habit sheet anytime to fit your routine
5. **Check the output** - Review `generated_schedule.json` to see AI's logic

---

## 🌟 Next Steps

1. Run setup (one time): `python setup.py`
2. Run planner (daily): `python plan.py`
3. Check your calendar for your harmonious day!
4. Customize habits in the Google Sheet
5. Adjust config.json for your schedule

---

**Ready? Run `python setup.py` and let the wizard guide you!** 🌿

*The whole setup takes ~10 minutes and you only do it once.*
