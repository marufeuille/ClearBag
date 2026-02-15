import json
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models
from config import get_credentials

# Initialize Vertex AI
LOCATION = "us-central1" # or asia-northeast1

def init_vertex_ai(project_id, location=LOCATION):
    creds = get_credentials()
    vertexai.init(project=project_id, location=location, credentials=creds)

def analyze_document(file_content, mime_type, profiles, rules):
    """
    Analyzes a document using Gemini 1.5 Pro/Flash.
    
    Args:
        file_content (bytes): The binary content of the file.
        mime_type (str): The MIME type of the file (e.g., 'application/pdf', 'image/jpeg').
        profiles (dict): The profiles configuration.
        rules (list): The rules configuration.
        
    Returns:
        dict: The structured JSON response from Gemini.
    """
    
    # Construct the System Prompt
    system_prompt = """
    あなたは家庭の事務を司る優秀なAIエージェントです。
    提供される画像/PDFの内容を読み取り、提供された `Profiles` と `Rules` に基づいて、
    適切なツール（カレンダー登録、タスク作成、アーカイブ）を選択・実行するための情報を抽出してください。
    
    出力は必ずJSON形式で行ってください。Markdownのコードブロックは不要です。
    """
    
    # Construct the User Prompt with Context
    profiles_str = json.dumps(profiles, ensure_ascii=False, indent=2)
    rules_str = json.dumps(rules, ensure_ascii=False, indent=2)
    
    user_prompt = f"""
    ## Context Data
    
    ### Profiles (対象者定義)
    {profiles_str}
    
    ### Rules (判断ルール)
    {rules_str}
    
    ## Output Schema
    
    以下のJSON構造で出力してください:
    {{
      "summary": "文書の要約",
      "category": "EVENT" | "TASK" | "INFO" | "IGNORE", 
      "related_profile_ids": ["関連するProfileIDのリスト"],
      "events": [
        {{
          "summary": "カレンダー登録用タイトル (例: [長男] 遠足)",
          "start": "YYYY-MM-DDTHH:MM:SS (ISO8601)",
          "end": "YYYY-MM-DDTHH:MM:SS (ISO8601)",
          "location": "場所",
          "description": "詳細説明"
        }}
      ],
      "tasks": [
        {{
          "title": "タスク名",
          "due_date": "YYYY-MM-DD",
          "assignee": "PARENT" | "CHILD",
          "note": "メモ"
        }}
      ],
      "archive_filename": "リネーム後のファイル名 (例: YYYYMMDD_タイトル_対象.pdf)"
    }}
    
    ## Instructions
    
    1. 文書の日付、イベントの日時を正確に読み取ってください。年は文書内の情報や現在の日付から推測してください。
    2. Rulesにあるルールを適用して、タスクの期限や無視するかどうかを判断してください。
    3. ファイル名は `YYYYMMDD_タイトル` の形式にしてください。
    """

    # Load the model
    # Switching to gemini-1.5-pro for better reasoning capabilities as requested (closest to "Gemini 3" in terms of power currently available/stable)
    # Using the generic tag 'gemini-1.5-pro' to get the latest stable version.
    model = GenerativeModel("gemini-2.5-pro")

    # Create the content parts
    document_part = Part.from_data(data=file_content, mime_type=mime_type)
    
    generation_config = {
        "max_output_tokens": 8192,
        "temperature": 0.2,
        "top_p": 0.95,
        "response_mime_type": "application/json",
    }

    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }

    responses = model.generate_content(
        [document_part, user_prompt],
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=False,
    )
    
    try:
        # Clean up the response text if it contains markdown code blocks
        text = responses.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text)
    except Exception as e:
        print(f"Error parsing JSON response: {e}")
        print(f"Raw response: {responses.text}")
        return None


