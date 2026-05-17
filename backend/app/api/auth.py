from fastapi import APIRouter, HTTPException

from app.models.schemas import BiliQrCreateResponse, BiliQrStatusResponse
from app.services.bilibili_auth_store import bili_auth_store

router = APIRouter(prefix="/auth")


@router.post("/bilibili/qrcode", response_model=BiliQrCreateResponse)
def create_bili_qrcode() -> BiliQrCreateResponse:
    try:
        auth, qrcode_image = bili_auth_store.create()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生成 Bilibili 登录二维码失败：{exc}") from exc
    return BiliQrCreateResponse(
        session_id=auth.session_id,
        login_url=auth.login_url,
        qrcode_image=qrcode_image,
    )


@router.get("/bilibili/qrcode/{session_id}", response_model=BiliQrStatusResponse)
def get_bili_qrcode_status(session_id: str) -> BiliQrStatusResponse:
    try:
        auth = bili_auth_store.poll(session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"检查 Bilibili 登录状态失败：{exc}") from exc
    if not auth:
        raise HTTPException(status_code=404, detail="登录会话不存在或已过期")
    return BiliQrStatusResponse(
        status="logged_in" if auth.is_logged_in else "pending",
        message=auth.message,
        is_logged_in=auth.is_logged_in,
    )
