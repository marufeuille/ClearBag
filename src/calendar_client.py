from datetime import datetime, timedelta
from googleapiclient.discovery import build
from config import get_credentials

def get_calendar_service():
    """Returns an authenticated Calendar service."""
    creds = get_credentials()
    return build('calendar', 'v3', credentials=creds)

def add_calendar_event(calendar_id, event_data, file_link=None):
    """
    Adds an event to the specified Google Calendar.
    
    Args:
        calendar_id (str): The ID of the calendar (e.g., 'primary' or specific ID).
        event_data (dict): Event details from Gemini (summary, start, end, location, description).
        file_link (str): Optional URL to the source file.
        
    Returns:
        dict: The created event object.
    """
    service = get_calendar_service()
    
    # Parse ISO format strings to ensure they are valid, though Gemini usually outputs ISO.
    # We pass them directly if they are in correct format.
    
    start_val = event_data.get('start')
    end_val = event_data.get('end')
    
    start_body = {}
    end_body = {}
    
    # Simple check: if length is 10 (YYYY-MM-DD), treat as all-day event
    if start_val and len(start_val) == 10:
        start_body = {'date': start_val}
    else:
        start_body = {'dateTime': start_val, 'timeZone': 'Asia/Tokyo'}
        
    if end_val and len(end_val) == 10:
        end_body = {'date': end_val}
    else:
        end_body = {'dateTime': end_val, 'timeZone': 'Asia/Tokyo'}

    description = event_data.get('description', '')
    if file_link:
        description += f"\n\nOriginal File: {file_link}"

    event = {
        'summary': event_data.get('summary', 'No Title'),
        'location': event_data.get('location', ''),
        'description': description,
        'start': start_body,
        'end': end_body,
    }
    
    try:
        created_event = service.events().insert(calendarId=calendar_id, body=event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        return created_event
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error creating event: {e}")
        return None


