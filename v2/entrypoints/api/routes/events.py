"""イベント API ルート

GET /api/events?from=&to=&profile_id=  → 200 [EventData...]
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreDocumentRepository
from v2.entrypoints.api.deps import FamilyContext, get_document_repo, get_family_context

router = APIRouter(prefix="/events", tags=["events"])


class EventResponse(BaseModel):
    summary: str
    start: str
    end: str
    location: str
    description: str
    confidence: str


@router.get("", response_model=list[EventResponse])
def list_events(
    from_date: str | None = None,
    to_date: str | None = None,
    profile_id: str | None = None,
    ctx: FamilyContext = Depends(get_family_context),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> list[EventResponse]:
    """
    全ドキュメントをまたいだイベント一覧を返す。

    クエリパラメータ:
        from_date: 開始日（YYYY-MM-DD）
        to_date: 終了日（YYYY-MM-DD）
        profile_id: プロファイルでフィルター（未実装: 将来拡張）
    """
    events = doc_repo.list_events(
        ctx.family_id, from_date=from_date, to_date=to_date, profile_id=profile_id
    )
    return [
        EventResponse(
            summary=e.summary,
            start=e.start,
            end=e.end,
            location=e.location,
            description=e.description,
            confidence=e.confidence,
        )
        for e in events
    ]
