"""
One-time setup wizard for Harmonious Day.
Guides users through dependency installation, API key configuration,
and Google Cloud authentication.
"""

import sys
import subprocess
import re
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure Google dependencies are installed before importing
GOOGLE_DEPENDENCIES = [
    'google-auth>=2.20.0',
    'google-auth-oauthlib>=1.0.0',
    'google-api-python-client>=2.70.0'
]

DEFAULT_SHEET_TITLE = 'Harmonious Day: Habit Database'


def install_dependencies() -> bool:
    """
    Install project dependencies from requirements.txt.
    
    Returns:
        True if successful, False otherwise
    """
    print("Installing project dependencies...")
    
    requirements_file = PROJECT_ROOT / 'requirements.txt'
    if not requirements_file.exists():
        print(f"requirements.txt not found at {requirements_file}")
        return False
    
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', str(requirements_file)],
            check=True,
            capture_output=True
        )
        print("Project dependencies installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"pip failed: {e}")
        return False


def setup_groq_api() -> bool:
    """
    Set up Groq API key in .env file.
    
    Returns:
        True if successful, False otherwise
    """
    # Import inside function to ensure Config is available after initial dependency check
    from src.core.config_manager import Config
    
    print("Groq API Key Setup")
    
    # Check if already configured
    if Config.ENV_FILE.exists():
        with open(Config.ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith('GROQ_API_KEY='):
                    print("✓ Existing Groq API key detected.")
                    return True
    
    print("Visit: https://console.groq.com/keys")
    print("Sign up (free), create an API key, and paste it below.\n")
    
    key = input("Enter your Groq API key: ").strip()
    
    if not key or len(key) < 20:
        print("Invalid API key.")
        return False
    
    try:
        # Check if .env exists, if so, append, otherwise write new
        current_content = Config.ENV_FILE.read_text() if Config.ENV_FILE.exists() else ""
        new_content = current_content.strip() + f"\nGROQ_API_KEY={key}\n"
        Config.ENV_FILE.write_text(new_content)
        print("Groq API key saved.")
        return True
    except Exception as e:
        print(f"Failed to save API key: {e}")
        return False
    

def find_existing_habits_sheet(drive_service, title: str):
    """
    Searches the user's Google Drive for a spreadsheet with given title, 
    excluding trashed files.
    
    Returns:
        (spreadsheet_id) or (None)
    """
    # Added 'and trashed = false' for robustness
    query = f"name = '{title}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
    
    try:
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields="files(id, name)"
        ).execute()

        files = results.get('files', [])
        if files:
            spreadsheet_id = files[0]['id']
            return spreadsheet_id
        return None
    except Exception as e:
        print(f"Error while searching for existing sheet: {e}")
        return None


def create_default_habits_sheet(sheets_service) -> str:
    """
    Create a default habits sheet in Google Sheets.
    
    Args:
        sheets_service: Authenticated Google Sheets API service
    
    Returns:
        Sheet ID if successful, None otherwise
    """
    # NOTE: The default habits must align with the src/models/models.py `Phase` enum
    headers = ['id', 'title', 'duration_min', 'frequency', 'ideal_phase', 
               'task_type', 'due_day', 'active']
    
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
        spreadsheet = {
            'properties': {'title': DEFAULT_SHEET_TITLE},
            'sheets': [{'properties': {'title': 'Habits'}}]
        }

        result = sheets_service.spreadsheets().create(
            body=spreadsheet,
            fields='spreadsheetId,sheets(properties(sheetId,title))'
        ).execute()

        spreadsheet_id = result['spreadsheetId']
        habits_sheet = next(
            s for s in result['sheets']
            if s['properties']['title'] == 'Habits'
        )
        sheet_id = habits_sheet['properties']['sheetId']

        # Upload data
        all_data = [headers] + default_habits
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Habits!A1',
            valueInputOption='RAW',
            body={'values': all_data}
        ).execute()

        # Apply formatting to header row
        sheets_service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={
                'requests': [{
                    'repeatCell': {
                        'range': {
                            'sheetId': sheet_id,
                            'startRowIndex': 0,
                            'endRowIndex': 1
                        },
                        'cell': {
                            'userEnteredFormat': {
                                'textFormat': {'bold': True},
                                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                            }
                        },
                        'fields': 'userEnteredFormat(textFormat,backgroundColor)'
                    }
                }]
            }
        ).execute()

        print(f"Habit sheet created. Spreadsheet ID: {spreadsheet_id}")
        return spreadsheet_id

    except Exception as e:
        print(f"Could not create sheet: {e}")
        return None


def update_env_with_sheet_id(sheet_id: str) -> bool:
    """
    Update .env file with the sheet ID.
    
    Args:
        sheet_id: Google Sheets ID to save
    
    Returns:
        True if successful, False otherwise
    """
    # Import inside function to ensure Config is available after initial dependency check
    from src.core.config_manager import Config
    
    try:
        # Read existing .env content
        env_content = ""
        if Config.ENV_FILE.exists():
            env_content = Config.ENV_FILE.read_text()
        
        # Check if SHEET_ID already exists
        if "SHEET_ID=" in env_content:
            # Replace existing
            env_content = re.sub(
                r'SHEET_ID=.*',
                f'SHEET_ID={sheet_id}',
                env_content
            )
        else:
            # Append new
            # Ensure it's on a new line if content exists
            env_content = env_content.strip() + f"\nSHEET_ID={sheet_id}\n"
        
        Config.ENV_FILE.write_text(env_content)
        print("Sheet ID saved to .env")
        return True
        
    except Exception as e:
        print(f"Could not update .env: {e}")
        print(f"Please manually add to .env: SHEET_ID={sheet_id}")
        return False


def main() -> None:
    """Main setup wizard."""
    print("Setting up Harmonious Day Orchestrator...")
    print("="*60)
    
    # Step 1: Install dependencies
    print("\nStep 1: Installing Dependencies")
    if not install_dependencies():
        sys.exit(1)
    
    # Now we can import after installing dependencies
    try:
        from src.auth.google_auth import create_initial_token, get_google_services
        from src.core.config_manager import Config
        from src.utils.logger import setup_logger
        
        logger = setup_logger(__name__)
        logger.info("Starting setup wizard")
        
    except ImportError as e:
        print(f"Failed to import required modules: {e}")
        print("Make sure all files are in the correct directories:")
        print("  - src/auth/google_auth.py")
        print("  - src/core/config_manager.py")
        print("  - src/utils/logger.py")
        sys.exit(1)
    
    # Step 2: Groq API Key
    print("\nStep 2: Groq API Configuration")
    if not setup_groq_api():
        print("Groq API key setup skipped.")
    
    # Step 3: Google Authentication
    print("\nStep 3: Google Cloud Authentication")
    if not Config.TOKEN_FILE.exists():
        if not create_initial_token():
            print("Google authentication failed.")
            sys.exit(1)
    else:
        print("Existing token.json found")

    # Step 4: Setting up Habit Sheet (Database)
    print("\nStep 4: Setting Up Google Sheets (Habit Database)")
    # Get services with drive access to search for existing sheets
    calendar_service, sheets_service, tasks_service, drive_service = get_google_services(include_drive=True)
    
    final_sheet_id = None
    
    # Check if sheet already exists
    existing_sheet = find_existing_habits_sheet(drive_service, DEFAULT_SHEET_TITLE)
    
    if existing_sheet:
        print(f"Existing Habit Database detected. Using ID: {existing_sheet}")
        final_sheet_id = existing_sheet
    else:
        print("No existing Habit Database found. Creating a new one...")
        new_sheet_id = create_default_habits_sheet(sheets_service)
        if new_sheet_id:
            final_sheet_id = new_sheet_id
        else:
            print("Habit sheet creation failed.")
    
    if final_sheet_id:
        # Save the confirmed sheet ID to the environment file
        update_env_with_sheet_id(final_sheet_id)
    else:
        print("WARNING: Could not determine the Habit Database ID. Please check Google Sheets setup.")
    
    # Final verification
    print("\nStep 5: Verification")
    if Config.validate():
        logger.info("Setup completed successfully")
        print("="*60)
        print("Setup complete!")
        print("="*60)
        print("\nYou can now run: python scripts/plan.py")
        print("\nTo customize:")
        print("  - Edit your habit sheet in Google Sheets")
        print("  - Adjust config/config.json for phase times")
        print("  - Modify config/system_prompt.txt for AI behavior")
    else:
        print("="*60)
        print("Setup completed with some warnings")
        print("="*60)
        print("\nPlease check the logs and fix any missing configuration")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)