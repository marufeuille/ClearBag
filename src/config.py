import os
import pickle
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Load environment variables from .env file
load_dotenv()

# Configuration Constants
PROJECT_ID = os.getenv('PROJECT_ID')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')
INBOX_FOLDER_ID = os.getenv('INBOX_FOLDER_ID')
ARCHIVE_FOLDER_ID = os.getenv('ARCHIVE_FOLDER_ID')

# If modifying these scopes, delete the file token.pickle.
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/chat.messages',
    'https://www.googleapis.com/auth/chat.spaces.readonly',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/cloud-platform'
]

SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_credentials():
    """Gets valid user credentials from storage."""
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            elif os.path.exists(SERVICE_ACCOUNT_FILE):
                 creds = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            else:
                raise FileNotFoundError("No 'credentials.json' or 'service_account.json' found.")

        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
            
    return creds

def load_config_from_sheet(spreadsheet_id):
    """Loads Profiles and Rules from the specified Google Sheet."""
    creds = get_credentials()
    service = build('sheets', 'v4', credentials=creds)

    sheet = service.spreadsheets()
    
    # Load Profiles
    result_profiles = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range='Profiles!A2:E').execute()
    profiles_data = result_profiles.get('values', [])
    
    profiles = {}
    for row in profiles_data:
        if len(row) > 0:
            # Assuming columns: ID, Name, Grade, Keywords, Calendar_ID
            p_id = row[0]
            profiles[p_id] = {
                'id': p_id,
                'name': row[1] if len(row) > 1 else '',
                'grade': row[2] if len(row) > 2 else '',
                'keywords': row[3] if len(row) > 3 else '',
                'calendar_id': row[4] if len(row) > 4 else ''
            }

    # Load Rules
    result_rules = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range='Rules!A2:D').execute()
    rules_data = result_rules.get('values', [])
    
    rules = []
    for row in rules_data:
        if len(row) > 0:
             # Assuming columns: Rule_ID, Target_Profile, Rule_Type, Content
            rules.append({
                'rule_id': row[0],
                'target_profile': row[1] if len(row) > 1 else '',
                'rule_type': row[2] if len(row) > 2 else '',
                'content': row[3] if len(row) > 3 else ''
            })

    return profiles, rules


