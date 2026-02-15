import os
from todoist_api_python.api import TodoistAPI

# You should set this in your environment variables
TODOIST_API_TOKEN = os.environ.get("TODOIST_API_TOKEN")

def get_todoist_client():
    if not TODOIST_API_TOKEN:
        print("Warning: TODOIST_API_TOKEN is not set.")
        return None
    return TodoistAPI(TODOIST_API_TOKEN)

def create_todoist_task(task_data, project_id=None, file_link=None):
    """
    Creates a task in Todoist.
    
    Args:
        task_data (dict): Task details (title, due_date, assignee, note).
        project_id (str): Optional project ID.
        file_link (str): Optional URL to the source file.
    """
    api = get_todoist_client()
    if not api:
        return None

    # Todoist expects 'due_date' as 'YYYY-MM-DD' or 'due_string' (e.g. 'tomorrow')
    # We use 'due_date' if available.
    
    content = task_data.get('title')
    description = f"Assignee: {task_data.get('assignee')}\n{task_data.get('note')}"
    
    if file_link:
        description += f"\n\n[Original File]({file_link})"
    
    due_date = task_data.get('due_date') # YYYY-MM-DD
    
    try:
        task = api.add_task(
            content=content,
            description=description,
            due_string=due_date, # Use due_string for YYYY-MM-DD string inputs to avoid library trying to call .isoformat()
            project_id=project_id
        )
        print(f"Created Todoist Task: {task.content}")
        return task
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error creating Todoist Task: {e}")
        return None


