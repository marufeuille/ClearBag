"""タスク API ルート

GET   /api/tasks?completed=false  → 200 [TaskData...]
PATCH /api/tasks/{id}             → 200 { completed: true }
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from v2.adapters.firestore_repository import FirestoreDocumentRepository
from v2.entrypoints.api.deps import FamilyContext, get_document_repo, get_family_context

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskResponse(BaseModel):
    id: str
    title: str
    due_date: str
    assignee: str
    note: str
    completed: bool


class TaskUpdateRequest(BaseModel):
    completed: bool


class TaskUpdateResponse(BaseModel):
    completed: bool


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    completed: bool | None = None,
    ctx: FamilyContext = Depends(get_family_context),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> list[TaskResponse]:
    """
    全ドキュメントをまたいだタスク一覧を返す。

    クエリパラメータ:
        completed: true/false でフィルター（省略時は全件）
    """
    tasks = doc_repo.list_tasks(ctx.family_id, completed=completed)
    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            due_date=t.due_date,
            assignee=t.assignee,
            note=t.note,
            completed=t.completed,
        )
        for t in tasks
    ]


@router.patch("/{task_id}", response_model=TaskUpdateResponse)
async def update_task(
    task_id: str,
    body: TaskUpdateRequest,
    ctx: FamilyContext = Depends(get_family_context),
    doc_repo: FirestoreDocumentRepository = Depends(get_document_repo),
) -> TaskUpdateResponse:
    """タスクの完了状態を更新する"""
    doc_repo.update_task_completed(ctx.family_id, task_id, body.completed)
    return TaskUpdateResponse(completed=body.completed)
