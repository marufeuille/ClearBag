"""iCal フィード API ルート

GET /api/ical/{token}  → text/calendar（認証不要、トークンベース）

iPhone のカレンダーアプリや Google Calendar からこの URL を登録すると
自動同期が可能になる。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import PlainTextResponse
from google.cloud import firestore

from v2.adapters.firestore_repository import FirestoreDocumentRepository
from v2.adapters.ical_renderer import ICalRenderer
from v2.entrypoints.api.deps import get_document_repo, get_ical_renderer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ical", tags=["ical"])


@router.get("/{token}", response_class=PlainTextResponse)
async def get_ical_feed(
    token: str,
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
    renderer: ICalRenderer = Depends(get_ical_renderer),
) -> str:
    """
    iCal フィードを返す（認証不要、トークンベース）。

    1. icalToken で users コレクションからユーザーを特定
    2. そのユーザーの全イベントを取得
    3. iCal 形式の文字列をレスポンス
    """
    # icalToken で uid を検索
    uid = _find_uid_by_ical_token(doc_repo._db, token)
    if uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid iCal token"
        )

    events = doc_repo.list_events(uid)
    ical_content = renderer.render(events)

    return PlainTextResponse(
        content=ical_content,
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="clearbag.ics"'},
    )


def _find_uid_by_ical_token(db: firestore.Client, token: str) -> str | None:
    """icalToken フィールドでユーザーを検索して uid を返す"""
    snaps = db.collection("users").where("ical_token", "==", token).limit(1).stream()
    for snap in snaps:
        return snap.id
    return None
