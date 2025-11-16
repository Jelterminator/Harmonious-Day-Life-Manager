# File: auth.py
import os.path
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/tasks.readonly"
]
TOKEN_PATH = Path("token.json")
CREDS_PATH = Path("credentials.json")

def _authenticate():
    """
    Internal helper to load or refresh credentials.
    Returns 'creds' object or None.
    """
    creds = None
    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}. Please re-authenticate.")
                TOKEN_PATH.unlink() # Delete bad token
                return None
        else:
            # No valid token, return None to trigger full auth flow
            return None
        
        # Save the refreshed token
        with open(TOKEN_PATH, "w") as token_file:
            token_file.write(creds.to_json())
    return creds

def create_initial_token():
    """
    Forces the interactive, browser-based auth flow.
    Called by 'init.py'.
    """
    if not CREDS_PATH.exists():
        print(f"ERROR: 'credentials.json' not found.")
        print("Please download it from Google Cloud Console and place it here.")
        return
        
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_PATH, "w") as token_file:
        token_file.write(creds.to_json())

def get_google_services():
    """
    Main function to get authenticated service objects.
    Uses existing 'token.json' if possible.
    Called by 'plan.py' via the Orchestrator.
    """
    creds = _authenticate()
    
    if not creds:
        print("ERROR: 'token.json' is missing or invalid.")
        print("Please run 'init.py' first to authenticate.")
        return None, None, None

    try:
        calendar_service = build("calendar", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)
        tasks_service = build("tasks", "v1", credentials=creds)
        return calendar_service, sheets_service, tasks_service
    except HttpError as err:
        print(f"An error occurred building services: {err}")
        return None, None, None