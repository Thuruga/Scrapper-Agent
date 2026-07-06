"""Rotas da central de notificações."""

from fastapi import APIRouter, HTTPException, Query

from services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["Notificações"])


@router.get("")
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
):
    notifications = notification_service.list(unread_only=unread_only, limit=limit)
    return {
        "notifications": [n.model_dump() for n in notifications],
        "unread_count": notification_service.unread_count(),
    }


@router.post("/read-all")
async def mark_all_notifications_read():
    count = notification_service.mark_all_read()
    return {"status": "ok", "count": count}


@router.delete("")
async def clear_notifications():
    count = notification_service.clear()
    return {"status": "ok", "count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: str):
    if not notification_service.mark_read(notification_id):
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    return {"status": "ok"}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    if not notification_service.delete(notification_id):
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    return {"status": "ok"}
