import os.path
import json
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURATION ---

# These are the scopes. Notice tasks.readonly as you requested.
SCOPES = [
    "https://www.googleapis.com/auth/calendar", # Read/Write Calendar
    "https://www.googleapis.com/auth/spreadsheets", # Read/Write Sheets
    "https://www.googleapis.com/auth/tasks.readonly" # Read-Only Tasks
]

# --- HELLO WORLD! TEST PARAMETERS ---
# 1. Create a new Google Sheet
# 2. Get its ID from the URL: httpss://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
# 3. Put "Hello" in cell A1
SHEET_ID = "1nxoDqm_NMHNMgCM0UZxgXI3OXA6r0_hRkC5SrQv6t0M" 
SHEET_RANGE = "Sheet1!A1" # The cell you want to read

# ===================================================================
# DO NOT EDIT BELOW THIS LINE
# ===================================================================

def get_google_services():
    """
    Handles the entire OAuth2 flow and returns authenticated
    service objects for Calendar, Sheets, and Tasks.
    """
    creds = None
    token_path = Path("token.json")
    creds_path = Path("credentials.json")

    # Load existing token if it exists
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If no (valid) creds, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not creds_path.exists():
                print(f"Error: '{creds_path}' not found.")
                print("Please download it from Google Cloud Console.")
                return None, None, None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(creds_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    try:
        # Build the service objects
        calendar_service = build("calendar", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)
        tasks_service = build("tasks", "v1", credentials=creds)
        
        print("Successfully authenticated and built services.")
        return calendar_service, sheets_service, tasks_service

    except HttpError as err:
        print(f"An error occurred: {err}")
        return None, None, None

# --- "HELLO, WORLD!" TEST FUNCTIONS ---

def test_read_tasks(service):
    """Test 1: Reads task lists from Google Tasks."""
    print("\n--- Testing Google Tasks (Read-Only) ---")
    try:
        results = service.tasklists().list(maxResults=10).execute()
        items = results.get("items", [])
        
        if not items:
            print("No task lists found.")
        else:
            print(f"Found {len(items)} task lists:")
            for item in items:
                print(f"* {item['title']} (ID: {item['id']})")
        print("Tasks API: Read test SUCCESSFUL.")
    except HttpError as err:
        print(f"Tasks API Error: {err}")

def test_read_sheet(service, sheet_id, sheet_range):
    """Test 2: Reads a cell from Google Sheets."""
    print("\n--- Testing Google Sheets (Read) ---")
    if sheet_id == "YOUR_SPREADSHEET_ID_HERE":
        print("Please update the SHEET_ID variable in the script.")
        return
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=sheet_id, range=sheet_range)
            .execute()
        )
        values = result.get("values", [])
        if not values:
            print(f"No data found in {sheet_range}.")
        else:
            print(f"Read from {sheet_range}: '{values[0][0]}'")
        print("Sheets API: Read test SUCCESSFUL.")
    except HttpError as err:
        print(f"Sheets API Error: {err}")

def test_write_calendar(service):
    """Test 3: Writes and deletes a test event in Google Calendar."""
    print("\n--- Testing Google Calendar (Write) ---")
    try:
        # Get the current time for the event
        import datetime
        now = datetime.datetime.utcnow()
        start_time = now.isoformat() + "Z"  # 'Z' indicates UTC time
        end_time = (now + datetime.timedelta(minutes=15)).isoformat() + "Z"

        event = {
            "summary": "Orchestrator Auth Test",
            "description": "If you see this, the write test was successful.",
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }

        # 1. Write the event
        created_event = (
            service.events()
            .insert(calendarId="primary", body=event)
            .execute()
        )
        print(f"Created test event: '{created_event.get('summary')}'")
        event_id = created_event["id"]

        # 2. Delete the event to clean up
        service.events().delete(
            calendarId="primary", eventId=event_id
        ).execute()
        print("Cleaned up test event.")
        print("Calendar API: Write test SUCCESSFUL.")
    
    except HttpError as err:
        print(f"Calendar API Error: {err}")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    
    # Authenticate and get services
    calendar_service, sheets_service, tasks_service = get_google_services()
    
    if all([calendar_service, sheets_service, tasks_service]):
        # Run the "Hello, World!" tests
        test_read_tasks(tasks_service)
        test_read_sheet(sheets_service, SHEET_ID, SHEET_RANGE)
        test_write_calendar(calendar_service)
        
        print("\nAll tests complete. Step 1 is done!")
