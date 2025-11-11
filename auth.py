import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    "httpss://www.googleapis.com/auth/calendar",
    "httpss://www.googleapis.com/auth/spreadsheets",
    "httpss://www.googleapis.com/auth/tasks.readonly"
]

def get_google_services():
    creds = None
    token_path = Path("token.json")
    creds_path = Path("credentials.json")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    try:
        calendar_service = build("calendar", "v3", credentials=creds)
        sheets_service = build("sheets", "v4", credentials=creds)
        tasks_service = build("tasks", "v1", credentials=creds)
        print("Successfully authenticated and built services.")
        return calendar_service, sheets_service, tasks_service
    except HttpError as err:
        print(f"An error occurred: {err}")
        return None, None, None
