import os
import time
from .config import load_config_from_sheet, SPREADSHEET_ID, INBOX_FOLDER_ID, ARCHIVE_FOLDER_ID, PROJECT_ID
from .drive_utils import list_files_in_folder, download_file_content, rename_and_move_file
from .gemini_client import init_vertex_ai, analyze_document
from .calendar_client import add_calendar_event
from .todoist_client import create_todoist_task
from .slack_client import send_slack_file_notification

def main():
    print("=== School Agent Started ===")
    
    # 1. Initialize & Load Config
    print("Loading configuration...")
    try:
        profiles, rules = load_config_from_sheet(SPREADSHEET_ID)
        print(f"Loaded {len(profiles)} profiles and {len(rules)} rules.")
    except Exception as e:
        print(f"Failed to load config: {e}")
        return

    # Initialize Gemini
    init_vertex_ai(project_id=PROJECT_ID)

    # 2. Scan Inbox
    print("Scanning Inbox...")
    files = list_files_in_folder(INBOX_FOLDER_ID)
    if not files:
        print("No files found in Inbox.")
        return

    print(f"Found {len(files)} files to process.")

    # 3. Process Loop
    for file in files:
        file_id = file['id']
        file_name = file['name']
        mime_type = file['mimeType']
        
        print(f"\n--- Processing: {file_name} ---")
        file_link = file.get('webViewLink', '')
        
        # Download content
        try:
            content = download_file_content(file_id)
            print(f"Downloaded {len(content)} bytes.")
        except Exception as e:
            print(f"Error downloading file: {e}")
            continue

        # Analyze with Gemini
        print("Analyzing with Gemini...")
        try:
            result = analyze_document(content, mime_type, profiles, rules)
            if not result:
                print("Failed to analyze document (no result).")
                continue
        except Exception as e:
            print(f"Error during analysis: {e}")
            continue

        print("Analysis Result:")
        print(f"Summary: {result.get('summary')}")
        
        # Execute Actions
        
        # Calendar Events
        events = result.get('events', [])
        events = [e for e in events if e.get('confidence') != 'LOW']
        for event in events:
            # Determine calendar ID based on profile? 
            # For now, we use the default logic or map from profiles if implemented.
            # The spec says:
            # ELDER -> c_12345...
            # YOUNGER -> c_67890...
            # PARENTS -> primary
            
            # We need to find which calendar to use.
            # The result has 'related_profile_ids'.
            # If multiple, maybe add to all? Or just primary?
            # Let's try to map the first related profile's calendar_id.
            
            target_calendar_id = 'primary' # Default fallback
            related_ids = result.get('related_profile_ids', [])
            if related_ids:
                first_id = related_ids[0]
                if first_id in profiles:
                    cal_id = profiles[first_id].get('calendar_id')
                    if cal_id:
                        target_calendar_id = cal_id
            
            print(f"DEBUG: Using Calendar ID: {target_calendar_id} for event: {event.get('summary')}")
            print(f"Adding event to calendar ({target_calendar_id}): {event.get('summary')}")
            add_calendar_event(target_calendar_id, event, file_link=file_link)

        # Tasks (Todoist)
        tasks = result.get('tasks', [])
        for task in tasks:
            print(f"Adding task to Todoist: {task.get('title')}")
            create_todoist_task(task, file_link=file_link)

        # Notifications (Slack)
        print("Sending Slack notification...")
        send_slack_file_notification(
            notification=result.get('notification'),
            file_link=file_link,
            filename=file_name,
            summary=result.get('summary', ''),
            tasks=tasks,
            events=events,
        )

        # Archive
        new_name = result.get('archive_filename')
        if not new_name:
            # Fallback if Gemini didn't provide a name
            new_name = f"PROCESSED_{file_name}"
        
        # Ensure extension is preserved or added
        # Gemini might output "20251010_Title.pdf" but if original was image, we should be careful.
        # For now, trust Gemini or append original extension if missing?
        # Let's trust Gemini but ensure it doesn't fail if extension mismatch.
        
        print(f"Archiving file as: {new_name}")
        try:
            rename_and_move_file(file_id, new_name, ARCHIVE_FOLDER_ID)
            print("File archived.")
        except Exception as e:
            print(f"Error archiving file: {e}")

    print("\n=== All files processed ===")

if __name__ == '__main__':
    main()
