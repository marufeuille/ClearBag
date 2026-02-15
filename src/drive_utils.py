import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from config import get_credentials

def get_drive_service():
    """Returns an authenticated Drive service."""
    creds = get_credentials()
    return build('drive', 'v3', credentials=creds)

def list_files_in_folder(folder_id):
    """Lists files in the specified Google Drive folder."""
    service = get_drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="nextPageToken, files(id, name, mimeType, webViewLink)",
        pageSize=100
    ).execute()
    items = results.get('files', [])
    return items

def download_file_content(file_id):
    """Downloads the content of a file."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh.getvalue()

def rename_and_move_file(file_id, new_name, target_folder_id):
    """Renames a file and moves it to a new folder."""
    service = get_drive_service()
    
    # 1. Get current parents to remove them
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    
    # 2. Update file: add new parent, remove old parents, update name
    service.files().update(
        fileId=file_id,
        addParents=target_folder_id,
        removeParents=previous_parents,
        body={'name': new_name},
        fields='id, parents'
    ).execute()
