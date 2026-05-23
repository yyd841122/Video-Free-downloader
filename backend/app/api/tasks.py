from fastapi import APIRouter, HTTPException

from app.models.schemas import TaskStatusResponse
from app.services.task_store import task_store

router = APIRouter(prefix="/tasks")


@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task(task_id: str) -> TaskStatusResponse:
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    eta = int(round(task.eta)) if task.eta is not None else None
    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        progress=task.progress,
        speed=task.speed,
        eta=eta,
        filename=task.filename,
        download_url=f"/api/files/{task.task_id}" if task.status == "completed" else None,
        error=task.error,
    )
