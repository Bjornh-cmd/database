from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from shared.auth import ADMIN_TOKEN_TYPE, decode_token
from shared.meta_db import get_db
from shared.models import Admin

ADMIN_COOKIE = "admin_token"


def get_current_admin(
    admin_token: str | None = Cookie(default=None, alias=ADMIN_COOKIE),
    db: Session = Depends(get_db),
) -> Admin:
    if not admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(admin_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if payload.get("type") != ADMIN_TOKEN_TYPE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    admin_id = int(payload["sub"])
    admin = db.scalar(select(Admin).where(Admin.id == admin_id))
    if admin is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin
