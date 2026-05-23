from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.db.models import User
from app.models.schemas import TaskHistoryItem, TaskHistoryListResponse
from app.services.history_service import list_history_for_user

router = APIRouter(prefix="/users")


@router.get("/me/history", response_model=TaskHistoryListResponse)
def get_my_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskHistoryListResponse:
    raw = list_history_for_user(db, user)
    return TaskHistoryListResponse(items=[TaskHistoryItem(**item) for item in raw])
