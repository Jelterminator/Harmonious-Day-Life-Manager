# File: src/auth/google_auth.py
"""
Google API authentication module.
Handles OAuth2 flow and credential management.
"""

from typing import Optional, Tuple
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from src.core.config_manager import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _authenticate() -> Optional[Credentials]:
    """
    Internal helper to load or refresh credentials.
    
    Returns:
        Credentials object or None if authentication fails
    """
    creds = None
    
    if Config.TOKEN_FILE.exists():
        logger.debug(f"Loading existing token from {Config.TOKEN_FILE}")
        creds = Credentials.from_authorized_user_file(
            str(Config.TOKEN_FILE), 
            Config.GOOGLE_SCOPES
        )
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired credentials")
            try:
                creds.refresh(Request())
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Error refreshing token: {e}", exc_info=True)
                logger.warning("Deleting invalid token file")
                Config.TOKEN_FILE.unlink(missing_ok=True)
                return None
        else:
            logger.warning("No valid credentials found")
            return None
        
        # Save the refreshed token
        logger.debug("Saving refreshed credentials")
        with open(Config.TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())
    
    return creds


def create_initial_token() -> bool:
    """
    Forces the interactive, browser-based auth flow.
    Called by 'setup.py' during initial setup.
    
    Returns:
        True if authentication successful, False otherwise
    """
    logger.info("Starting interactive authentication flow")
    
    if not Config.CREDENTIALS_FILE.exists():
        logger.error(f"credentials.json not found at {Config.CREDENTIALS_FILE}")
        logger.error("Please download it from Google Cloud Console and place it in the project root")
        return False
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(Config.CREDENTIALS_FILE), 
            Config.GOOGLE_SCOPES
        )
        logger.info("Opening browser for authentication...")
        creds = flow.run_local_server(port=0)
        
        with open(Config.TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())
        
        logger.info(f"Authentication successful! Token saved to {Config.TOKEN_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Authentication flow failed: {e}", exc_info=True)
        return False


def get_google_services(include_drive=False) -> Tuple[Optional[Resource], Optional[Resource], Optional[Resource]]:
    """
    Main function to get authenticated service objects.
    Uses existing 'token.json' if possible.
    Called by 'plan.py' via the Orchestrator.
    
    Returns:
        Tuple of (calendar_service, sheets_service, tasks_service)
        Returns (None, None, None) if authentication fails
    """
    logger.info("Initializing Google API services")
    
    creds = _authenticate()
    
    if not creds:
        logger.error("Authentication failed")
        logger.error("token.json is missing or invalid")
        logger.error("Please run 'python setup.py' to authenticate")
        return None, None, None
    
    try:
        logger.debug("Building Calendar API service")
        calendar_service = build("calendar", "v3", credentials=creds)
        
        logger.debug("Building Sheets API service")
        sheets_service = build("sheets", "v4", credentials=creds)
        
        logger.debug("Building Tasks API service")
        tasks_service = build("tasks", "v1", credentials=creds)
        
        logger.debug("Building Drive API service")
        drive_service = build('drive', 'v3', credentials=creds)
        
        logger.info("All Google API services initialized successfully")
        if include_drive:
            return calendar_service, sheets_service, tasks_service, drive_service
        else:
            return calendar_service, sheets_service, tasks_service
        
    except HttpError as err:
        logger.error(f"HTTP error occurred building services: {err}", exc_info=True)
        return None, None, None
    except Exception as err:
        logger.error(f"Unexpected error building services: {err}", exc_info=True)
        return None, None, None