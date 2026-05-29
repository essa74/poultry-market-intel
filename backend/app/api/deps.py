from fastapi import HTTPException, Request
from app.core.config import get_settings


def require_admin_token(request: Request) -> None:
    settings = get_settings()
    if not settings.admin_token:
        return
    token = request.headers.get("Authorization", "")
    if token.startswith("Bearer "):
        token = token[len("Bearer "):]
    else:
        token = request.headers.get("X-Admin-Token", "")
    if not token or token != settings.admin_token:
        raise HTTPException(
            status_code=401,
            detail={
                "en": "Admin token required",
                "ar": "هذه العملية تتطلب صلاحية مدير",
            },
        )
