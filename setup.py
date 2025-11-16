# File: setup.py

import sys
import subprocess
from pathlib import Path
import re

# Ensure Google dependencies are installed before importing auth
GOOGLE_DEPENDENCIES = [
    'google-auth>=2.20.0',
    'google-auth-oauthlib>=1.0.0',
    'google-api-python-client>=2.70.0'
]

for package in GOOGLE_DEPENDENCIES:
    subprocess.run([sys.executable, '-m', 'pip', 'install', package], check=True)

from auth import create_initial_token, get_google_services

REQUIREMENTS_FILE = Path('requirements.txt')
ENV_FILE = Path('.env')
MAIN_PY = Path('main.py')
DEFAULT_SHEET_TITLE = 'Harmonious Day: Habit Database'

# -------------------- Helper Functions --------------------

def install_dependencies():
    if not REQUIREMENTS_FILE.exists():
        print(f"❌ {REQUIREMENTS_FILE} not found.")
        return False
    print("📦 Installing project dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(REQUIREMENTS_FILE)], check=True)
        print("✅ Project dependencies installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ pip failed: {e}")
        return False


def setup_groq_api():
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    print("✓ Existing Groq API key detected.")
                    return True
    key = input("Enter your Groq API key (https://console.groq.com/keys): ").strip()
    if not key or len(key) < 20:
        print("❌ Invalid API key.")
        return False
    ENV_FILE.write_text(f"GROQ_API_KEY={key}\n")
    print("✅ Groq API key saved.")
    return True


def create_default_habits_sheet(sheets_service):
    headers = ['id','title','duration_min','frequency','ideal_phase','task_type','due_day','active']
    default_habits = [
        ['H01', 'Morning Meditation', '15', 'Daily', 'WOOD', 'spiritual', 'Every Day', 'Yes'],
        ['H02', 'Morning Stretch', '10', 'Daily', 'WOOD', 'light_exercise', 'Every Day', 'Yes'],
        ['H03', 'Morning Reading', '30', 'Daily', 'WOOD', 'learning', 'Every Day', 'Yes'],
        ['H04', 'Light Exercise', '20', 'Daily', 'WOOD', 'light_exercise', 'Every Day', 'Yes'],
        ['H05', 'Lunch Break', '30', 'Daily', 'EARTH', 'nourishment', 'Every Day', 'Yes'],
        ['H06', 'Afternoon Walk', '15', 'Daily', 'EARTH', 'light_exercise', 'Every Day', 'Yes'],
        ['H07', 'Mindful Break', '10', 'Daily', 'EARTH', 'spiritual', 'Every Day', 'Yes'],
        ['H08', 'Organize Workspace', '15', 'Daily', 'METAL', 'admin', 'Every Day', 'Yes'],
        ['H09', 'Review Tasks', '10', 'Daily', 'METAL', 'planning', 'Every Day', 'Yes'],
        ['H10', 'Evening Exercise', '30', 'Daily', 'WATER', 'heavy_exercise', 'Every Day', 'No'],
        ['H11', 'Evening Walk', '20', 'Daily', 'WATER', 'light_exercise', 'Every Day', 'Yes'],
        ['H12', 'Evening Reading', '45', 'Daily', 'WATER', 'learning', 'Every Day', 'Yes'],
        ['H13', 'Evening Meditation', '15', 'Daily', 'WATER', 'spiritual', 'Every Day', 'Yes'],
        ['H14', 'Journal Entry', '15', 'Daily', 'WATER', 'reflection', 'Every Day', 'Yes'],
        ['H15', 'Weekly Review', '30', 'Weekly', 'METAL', 'reflection', 'Sunday', 'Yes'],
        ['H16', 'Monday Exercise', '30', 'Weekly', 'WATER', 'heavy_exercise', 'Monday', 'No'],
        ['H17', 'Wednesday Exercise', '30', 'Weekly', 'WATER', 'heavy_exercise', 'Wednesday', 'No'],
        ['H18', 'Friday Exercise', '30', 'Weekly', 'WATER', 'heavy_exercise', 'Friday', 'No'],
    ]
    try:
        spreadsheet = {'properties':{'title':DEFAULT_SHEET_TITLE},'sheets':[{'properties':{'title':'Habits'}}]}
        spreadsheet = sheets_service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
        sheet_id = spreadsheet.get('spreadsheetId')
        sheet_url = spreadsheet.get('spreadsheetUrl')
        all_data = [headers] + default_habits
        sheets_service.spreadsheets().values().update(spreadsheetId=sheet_id, range='Habits!A1', valueInputOption='RAW', body={'values': all_data}).execute()
        # Make header bold
        sheets_service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={'requests':[{'repeatCell':{'range':{'sheetId':0,'startRowIndex':0,'endRowIndex':1},'cell':{'userEnteredFormat':{'textFormat':{'bold':True},'backgroundColor':{'red':0.9,'green':0.9,'blue':0.9}}},'fields':'userEnteredFormat(textFormat,backgroundColor)'}}]}).execute()
        print(f"✅ Habit sheet created: {sheet_url}")
        return sheet_id
    except Exception as e:
        print(f"❌ Could not create sheet: {e}")
        return None


def update_main_py_sheet_id(sheet_id):
    if not MAIN_PY.exists():
        print(f"⚠️ {MAIN_PY} not found, please update SHEET_ID manually.")
        return
    content = MAIN_PY.read_text()
    pattern = r'SHEET_ID = ["\'][^"\']+["\']'
    replacement = f'SHEET_ID = "{sheet_id}"'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
    else:
        content += f'\n{replacement}\n'
    MAIN_PY.write_text(content)
    print("✅ main.py updated with new sheet ID.")


def main():
    print("🌿 Setting up Harmonious Day Orchestrator...")

    # Dependencies
    if not install_dependencies():
        sys.exit(1)

    # Groq API
    if not setup_groq_api():
        print("⚠️ Groq API key setup skipped.")

    # Google Auth
    creds_ok = create_initial_token() if not Path('token.json').exists() else True
    if not creds_ok:
        print("❌ Google authentication failed.")
        sys.exit(1)

    # Google Services
    calendar_service, sheets_service, tasks_service = get_google_services()
    if not sheets_service:
        print("❌ Could not get Google Sheets service.")
        sys.exit(1)

    # Habit Sheet
    sheet_id = create_default_habits_sheet(sheets_service)
    if sheet_id:
        update_main_py_sheet_id(sheet_id)

    # Verification
    print("\n🎉 Setup complete! Run 'python plan.py' to start your daily planner.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
