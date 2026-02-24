"""タスク API ルート

GET   /api/tasks?completed=false  → 200 [TaskData...]
PATCH /api/tasks/{id}             → 200 { completed: true }
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreDocumentRepository
from v2.entrypoints.api.deps import get_current_uid, get_document_repo

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    title: str
    due_date: str
    assignee: str
    note: str


class TaskUpdateRequest(BaseModel):
    completed: bool


class TaskUpdateResponse(BaseModel):
    completed: bool


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    completed: bool | None = None,
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> list[TaskResponse]:
    """
    全ドキュメントをまたいだタスク一覧を返す。

    クエリパラメータ:
        completed: true/false でフィルター（省略時は全件）
    """
    tasks = doc_repo.list_tasks(uid, completed=completed)
    return [
        TaskResponse(
            title=t.title,
            due_date=t.due_date,
            assignee=t.assignee,
            note=t.note,
        )
        for t in tasks
    ]


@router.patch("/{task_id}", response_model=TaskUpdateResponse)
async def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    uid: str = Depends(get_current_uid),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> TaskUpdateResponse:
    """タスクの完了状態を更新する"""
    doc_repo.update_task_completed(uid, task_id, body.completed)
    return TaskUpdateResponse(completed=body.completed)
