"""Google API認証の一元管理

既存 src/config.py:get_credentials() を移植。
シングルトンパターンで認証情報をキャッシュし、各Adapterで再利用する。

Cloud Functions環境ではApplication Default Credentials (ADC)を使用。
"""

import os
import pickle
from functools import lru_cache
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
import google.auth

# Google API のスコープ
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/chat.messages',
    'https://www.googleapis.com/auth/chat.spaces.readonly',
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/cloud-platform'
]


def _is_cloud_function_environment() -> bool:
    """Cloud Functions環境かどうかを判定"""
    # Cloud Functionsでは K_SERVICE 環境変数が設定される
    return os.getenv('K_SERVICE') is not None or os.getenv('FUNCTION_TARGET') is not None


@lru_cache(maxsize=1)
def get_google_credentials(
    token_pickle_path: str = 'token.pickle',
    credentials_json_path: str = 'credentials.json',
    service_account_path: str = 'service_account.json',
) -> Credentials:
    """
    Google API認証情報を取得（シングルトン）。

    優先順位:
    1. Cloud Functions環境: Application Default Credentials (ADC)
    2. ローカル環境:
       a. token.pickle（既存のOAuth認証情報）
       b. credentials.json（OAuthクライアント設定）
       c. service_account.json（サービスアカウント）

    Args:
        token_pickle_path: OAuth トークンキャッシュのパス
        credentials_json_path: OAuth クライアント設定ファイルのパス
        service_account_path: サービスアカウント鍵ファイルのパス

    Returns:
        Credentials: Google API認証情報

    Raises:
        FileNotFoundError: 認証ファイルが見つからない場合
    """
    # Cloud Functions環境ではApplication Default Credentialsを使用
    if _is_cloud_function_environment():
        creds, project = google.auth.default(scopes=SCOPES)
        return creds

    # ローカル環境: 既存のロジック
    creds = None

    # 1. 既存のOAuth認証情報を読み込み
    if os.path.exists(token_pickle_path):
        with open(token_pickle_path, 'rb') as token:
            creds = pickle.load(token)

    # 2. 認証情報の有効性チェック
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # リフレッシュトークンで更新
            creds.refresh(Request())
        else:
            # 新規認証
            if os.path.exists(credentials_json_path):
                # OAuth認証フロー
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_json_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            elif os.path.exists(service_account_path):
                # サービスアカウント認証
                creds = service_account.Credentials.from_service_account_file(
                    service_account_path, scopes=SCOPES
                )
            else:
                raise FileNotFoundError(
                    f"認証ファイルが見つかりません: "
                    f"{credentials_json_path} または {service_account_path}"
                )

        # 3. OAuth認証情報をキャッシュ（サービスアカウントの場合は不要）
        if not isinstance(creds, service_account.Credentials):
            with open(token_pickle_path, 'wb') as token:
                pickle.dump(creds, token)

    return creds
