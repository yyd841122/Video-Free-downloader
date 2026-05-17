from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services.ytdlp_service import safe_file_response_path

router = APIRouter(prefix="/files")


@router.get("/{task_id}")
def download_file(task_id: str) -> FileResponse:
    file_path = safe_file_response_path(task_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="文件不存在或任务未完成")
    return FileResponse(path=file_path, filename=file_path.name)
