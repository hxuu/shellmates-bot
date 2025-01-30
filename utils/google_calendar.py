from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
import pickle
import logging
from typing import List, Optional
from datetime import datetime

class GoogleCalendarManager:
    """A manager class for Google Calendar operations with better error handling and typing."""
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    
    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.pickle'):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.creds = None
        self.service = None
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure logging for the calendar manager."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger('GoogleCalendarManager')
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Calendar API.
        
        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        try:
            if os.path.exists(self.token_path):
                with open(self.token_path, 'rb') as token:
                    self.creds = pickle.load(token)
            
            if not self.creds or not self.creds.valid:
                if self.creds and self.creds.expired and self.creds.refresh_token:
                    self.creds.refresh(Request())
                else:
                    if not os.path.exists(self.credentials_path):
                        self.logger.error(f"Credentials file not found at {self.credentials_path}")
                        return False
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    self.creds = flow.run_local_server(port=0)
                
                with open(self.token_path, 'wb') as token:
                    pickle.dump(self.creds, token)
            
            self.service = build('calendar', 'v3', credentials=self.creds)
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    async def create_event(self, 
                          title: str,
                          start_time: datetime,
                          end_time: datetime,
                          description: Optional[str] = None,
                          attendees: Optional[List[str]] = None,
                          timezone: str = 'Europe/Paris',
                          send_updates: str = 'all') -> Optional[str]:
        """
        Create a calendar event with improved error handling and input validation.
        
        Args:
            title: Event title
            start_time: Event start time
            end_time: Event end time
            description: Optional event description
            attendees: Optional list of attendee email addresses
            timezone: Timezone for the event (default: 'Europe/Paris')
            send_updates: Notification preference ('all', 'externalOnly', 'none')
            
        Returns:
            Optional[str]: Event ID if successful, None if failed
        """
        if not self.service:
            self.logger.error("Calendar service not initialized. Call authenticate() first.")
            return None
            
        # Validate inputs
        if end_time <= start_time:
            self.logger.error("End time must be after start time")
            return None
            
        event = {
            'summary': title,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
        }
        
        if description:
            event['description'] = description
            
        if attendees:
            # Validate email addresses (basic check)
            valid_attendees = [
                {'email': email.strip()} 
                for email in attendees 
                if '@' in email and '.' in email
            ]
            if valid_attendees:
                event['attendees'] = valid_attendees
                
        try:
            result = await self._execute_with_retry(
                lambda: self.service.events().insert(
                    calendarId='primary',
                    body=event,
                    sendUpdates=send_updates
                ).execute()
            )
            return result.get('id')
            
        except HttpError as e:
            self.logger.error(f"Failed to create event: {str(e)}")
            if e.resp.status == 401:
                # Token might be expired, try to refresh
                if self.authenticate():
                    return await self.create_event(
                        title, start_time, end_time, description, 
                        attendees, timezone, send_updates
                    )
            return None
            
        except Exception as e:
            self.logger.error(f"Unexpected error creating event: {str(e)}")
            return None
    
    async def _execute_with_retry(self, operation, max_retries: int = 3):
        """Execute an operation with retries on transient failures."""
        for attempt in range(max_retries):
            try:
                return operation()
            except HttpError as e:
                if e.resp.status in {500, 503} and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise