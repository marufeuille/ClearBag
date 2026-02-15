"""Google Sheets Config Source Adapter

ConfigSource ABCの実装。
既存 src/config.py:load_config_from_sheet() を移植し、ABCに準拠。
"""

import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from v2.domain.ports import ConfigSource
from v2.domain.models import Profile, Rule

logger = logging.getLogger(__name__)


class GoogleSheetsConfigSource(ConfigSource):
    """
    Google Sheetsから設定を読み込む実装。

    Sheetsの構造:
    - Profilesシート: ID, Name, Grade, Keywords, Calendar_ID
    - Rulesシート: Rule_ID, Target_Profile, Rule_Type, Content
    """

    def __init__(self, credentials: Credentials, spreadsheet_id: str):
        """
        Args:
            credentials: Google API認証情報
            spreadsheet_id: Google SheetsのID
        """
        if not credentials:
            raise ValueError("credentials is required")
        if not spreadsheet_id:
            raise ValueError("spreadsheet_id is required")

        self._service = build('sheets', 'v4', credentials=credentials)
        self._spreadsheet_id = spreadsheet_id

    def load_profiles(self) -> dict[str, Profile]:
        """
        Profilesシートからプロファイル一覧を読み込む。

        Returns:
            dict[str, Profile]: Profile ID -> Profile のマッピング

        Raises:
            Exception: シート読み込みに失敗した場合
        """
        try:
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range='Profiles!A2:E'
            ).execute()

            rows = result.get('values', [])
            profiles = {}

            for row in rows:
                if len(row) > 0:
                    profile_id = row[0]
                    profiles[profile_id] = Profile(
                        id=profile_id,
                        name=row[1] if len(row) > 1 else '',
                        grade=row[2] if len(row) > 2 else '',
                        keywords=row[3] if len(row) > 3 else '',
                        calendar_id=row[4] if len(row) > 4 else '',
                    )

            logger.info("Loaded %d profiles from Google Sheets", len(profiles))
            return profiles

        except Exception as e:
            logger.exception("Failed to load profiles from Google Sheets")
            raise

    def load_rules(self) -> list[Rule]:
        """
        Rulesシートからルール一覧を読み込む。

        Returns:
            list[Rule]: ルールのリスト

        Raises:
            Exception: シート読み込みに失敗した場合
        """
        try:
            result = self._service.spreadsheets().values().get(
                spreadsheetId=self._spreadsheet_id,
                range='Rules!A2:D'
            ).execute()

            rows = result.get('values', [])
            rules = []

            for row in rows:
                if len(row) > 0:
                    rules.append(Rule(
                        rule_id=row[0],
                        target_profile=row[1] if len(row) > 1 else '',
                        rule_type=row[2] if len(row) > 2 else '',
                        content=row[3] if len(row) > 3 else '',
                    ))

            logger.info("Loaded %d rules from Google Sheets", len(rules))
            return rules

        except Exception as e:
            logger.exception("Failed to load rules from Google Sheets")
            raise
