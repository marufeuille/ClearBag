import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# You should set these in your environment variables or config
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

def get_slack_client():
    if not SLACK_BOT_TOKEN:
        print("Warning: SLACK_BOT_TOKEN is not set.")
        return None
    return WebClient(token=SLACK_BOT_TOKEN)

def send_slack_message(message, channel_id=SLACK_CHANNEL_ID):
    """
    Sends a message to a Slack channel.
    """
    client = get_slack_client()
    if not client:
        return

    if not channel_id:
        print("Warning: SLACK_CHANNEL_ID is not set.")
        return

    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        print(f"Message sent to Slack: {response['ts']}")
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")

def send_slack_file_notification(filename, summary, tasks, events, file_link=None, channel_id=SLACK_CHANNEL_ID):
    """
    Sends a rich notification about the processed file.
    """
    message = f"*Processed File:* {filename}\n"
    if file_link:
        message += f"*Link:* {file_link}\n"
    message += "\n"
    message += f"*Summary:*\n{summary}\n\n"
    
    if events:
        message += "*Events Created:*\n"
        for e in events:
            message += f"- {e.get('summary')} ({e.get('start')})\n"
        message += "\n"
        
    if tasks:
        message += "*Tasks Created:*\n"
        for t in tasks:
            message += f"- {t.get('title')} (Due: {t.get('due_date')})\n"
            
    send_slack_message(message, channel_id)


