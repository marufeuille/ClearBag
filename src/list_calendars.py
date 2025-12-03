from googleapiclient.discovery import build
from config import get_credentials

def list_accessible_calendars():
    """Lists all calendars the service account has access to."""
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)
    
    print("=== Accessible Calendars ===")
    page_token = None
    while True:
        calendar_list = service.calendarList().list(pageToken=page_token).execute()
        for calendar_list_entry in calendar_list['items']:
            print(f"Summary: {calendar_list_entry.get('summary')}")
            print(f"ID:      {calendar_list_entry.get('id')}")
            print(f"Role:    {calendar_list_entry.get('accessRole')}")
            print("-------------------------")
        page_token = calendar_list.get('nextPageToken')
        if not page_token:
            break

if __name__ == '__main__':
    try:
        list_accessible_calendars()
    except Exception as e:
        print(f"Error: {e}")
