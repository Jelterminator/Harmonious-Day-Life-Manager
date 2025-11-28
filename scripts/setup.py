import sys
import subprocess
import re
import sqlite3
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DB_PATH = PROJECT_ROOT / "src/yyanchors.db"
DEFAULT_SHEET_TITLE = 'Harmonious Day: Habit Database'

# --- SQL SCHEMA & DATA CONSTANTS (UNCHANGED) ---
# ... (Keep SCHEMA_SQL constant as defined previously) ...
SCHEMA_SQL = """
-- Only drop tables related to traditions and practices if needed, 
-- but we will update the setup logic to only execute this block 
-- if the DB is new or reset is requested. 

CREATE TABLE IF NOT EXISTS Traditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT
);

CREATE TABLE IF NOT EXISTS Practices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tradition_id INTEGER NOT NULL,
    roman_hour INTEGER NOT NULL,
    name TEXT NOT NULL,
    duration_minutes INTEGER,
    notes TEXT,
    FOREIGN KEY(tradition_id) REFERENCES Traditions(id)
);

CREATE TABLE IF NOT EXISTS UserSettings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS ActiveTraditions (
    tradition_id INTEGER,
    FOREIGN KEY(tradition_id) REFERENCES Traditions(id)
);
"""

# The data insertion part is now separate.
INITIAL_DATA_SQL = """
-- Traditions
INSERT OR IGNORE INTO Traditions (id, name, category) VALUES
(1, 'Major Prayers', 'Christianity'), (2, 'Office of Readings', 'Christianity'), (3, 'Minor Prayers', 'Christianity'),
(4, 'Core Salah', 'Islam'), (5, 'Complete Salah', 'Islam'),
(6, 'Core Prayers', 'Judaism'), (7, 'Blessings', 'Judaism'),
(8, 'Sandhyavandanam', 'Hinduism'), (9, 'Brahma Murta', 'Hinduism'), (10, 'Puja', 'Hinduism'),
(11, 'Layman''s Practice', 'Buddhism'), (12, 'Kyoto Zen', 'Buddhism'), (13, 'Shaolin Kung Fu', 'Buddhism'),
(14, 'Three Daily Meals', 'Secular'), (15, 'Wake up before dawn', 'Secular'), (16, 'Secular - Sunset winddown', 'Secular');

-- Practices (A sample subset, ensure all 30+ inserts are included here)
INSERT OR IGNORE INTO Practices (tradition_id, roman_hour, name, duration_minutes) VALUES
(1, 0, 'Lauds - Morning Prayer', 20), (1, 12, 'Vespers - Evening Prayer', 20), (1, 15, 'Compline - Night Prayer', 10),
(2, 21, 'Vigils - Office of Readings', 60),
(3, 3, 'Terce', 10), (3, 6, 'Sext', 10), (3, 9, 'None', 10),
(4, 0, 'Fajr', 10), (4, 6, 'Dhuhr', 20), (4, 10, 'Asr', 20), (4, 12, 'Maghrib', 15), (4, 14, 'Isha', 20),
(5, 21, 'Tahajjud', 30), (5, 2, 'Duha', 15), (5, 15, 'Witr', 5),
-- Add all other previous INSERT statements here with INSERT OR IGNORE
(6, 0, 'Shacharit', 45), (6, 9, 'Mincha', 20), (6, 12, 'Ma''ariv / Arvit', 20),
(7, 21, 'Modeh Ani', 5), (7, 6, 'Birkat Hamazon', 10), (7, 15, 'Kriat Shema al Hamita', 5),
(8, 0, 'Pratah Sandhya', 30), (8, 6, 'Madhyahna Sandhya', 30), (8, 12, 'Sayam Sandhya', 30),
(9, 21, 'Brahma Muhurta', 180),
(10, 3, 'Morning Puja', 30), (10, 9, 'Midday Aarti', 10), (10, 15, 'Evening Aarti', 10),
(11, 0, 'Mindfulness practice', 15), (11, 12, '''Just sitting''', 30), (11, 15, 'Metta practice', 10),
(12, 21, 'Early Meditation', 45), (12, 4, 'Morning Meditation', 25), (12, 8, 'Afternoon Meditation', 25),
(13, 1, 'Chi Gong practice', 60), (13, 5, 'Kung Fu - conditioning', 60), (13, 9, 'Kung Fu - martial arts', 60),
(14, 1, 'Breakfast', 20), (14, 7, 'Lunch', 20), (14, 11, 'Dinner', 30),
(15, 23, 'Wake up', 60), (16, 12, 'Winddown', 120);
"""


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
    
# --- LOCAL DATABASE FUNCTIONS ---

def setup_local_database():
    """Initializes SQLite database schema and inserts base data if tables are empty."""
    print("\n--- Initializing Local Anchor Database Schema ---")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Create schema (using IF NOT EXISTS)
        cursor.executescript(SCHEMA_SQL) 
        
        # Check if traditions table is empty
        cursor.execute("SELECT COUNT(*) FROM Traditions")
        if cursor.fetchone()[0] == 0:
            print("Seeding base tradition and practice data...")
            cursor.executescript(INITIAL_DATA_SQL)
            conn.commit()
        else:
            print("Base data already present.")
            
        print(f"Database schema and base data checked at {DB_PATH}")
        return conn
    except Exception as e:
        print(f"Database creation failed: {e}")
        return None

def configure_location(conn):
    """Collects Lat/Long/Timezone only if settings are missing."""
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM UserSettings WHERE key IN ('latitude', 'longitude', 'timezone')")
    existing_settings = [row[0] for row in cursor.fetchall()]
    
    if len(existing_settings) == 3:
        lat, lng, tz = existing_settings
        print("\n--- Location Setup ---")
        choice = input(f"Existing location found ({lat}, {lng}, {tz}). Reconfigure? (y/N): ").lower()
        if choice != 'y':
            print("Location configuration skipped.")
            return

    print("\n--- Location Setup (for Solar Time/Roman Hours) ---")
    lat = input("Enter Latitude (default 52.01): ") or "52.01"
    lng = input("Enter Longitude (default 4.35): ") or "4.35"
    tz = input("Enter Timezone (default Europe/Amsterdam): ") or "Europe/Amsterdam"
    
    cursor.execute("INSERT OR REPLACE INTO UserSettings (key, value) VALUES ('latitude', ?)", (lat,))
    cursor.execute("INSERT OR REPLACE INTO UserSettings (key, value) VALUES ('longitude', ?)", (lng,))
    cursor.execute("INSERT OR REPLACE INTO UserSettings (key, value) VALUES ('timezone', ?)", (tz,))
    conn.commit()
    print("Location settings saved.")

def select_traditions(conn):
    """Interactive selection of traditions, allowing skip if already configured."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ActiveTraditions")
    if cursor.fetchone()[0] > 0:
        print("\n--- Tradition Selection ---")
        choice = input("Active traditions already configured. Reconfigure? (y/N): ").lower()
        if choice != 'y':
            print("Tradition configuration skipped.")
            return
        
        # If user chooses 'y', clear existing selections first
        cursor.execute("DELETE FROM ActiveTraditions")
        conn.commit()

    print("\n--- Tradition Selection ---")
    print("Which traditions do you want to include in your schedule?")
    
    cursor.execute("SELECT id, name, category FROM Traditions")
    traditions = cursor.fetchall()
    
    active_ids = []
    current_category = None
    
    for t_id, name, cat in traditions:
        if cat != current_category:
            print(f"\n--- {cat} ---")
            current_category = cat
        
        choice = input(f"Include {name}? (y/N): ").lower()
        if choice == 'y':
            active_ids.append((t_id,))
            
    if active_ids:
        cursor.executemany("INSERT INTO ActiveTraditions (tradition_id) VALUES (?)", active_ids)
        conn.commit()
        print(f"\nSaved {len(active_ids)} active traditions.")
    else:
        print("No traditions selected. Anchors section in config will be empty.")


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
        
    # Step 5: Creating user config file.
    print("\nStep 5: Anchor Database Setup")
    db_conn = setup_local_database()
    if db_conn:
        configure_location(db_conn)
        select_traditions(db_conn)
        db_conn.close()
    else:
        print("Skipping database configuration due to error.")
    
    # Final verification
    print("\nStep 6 Verification")
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