from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from shared.config import settings

ALGORITHM = "HS256"
ADMIN_TOKEN_TYPE = "admin"
DATABASE_TOKEN_TYPE = "database"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_token(subject: str, token_type: str, extra: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload = {
        "sub": subject,
        "type": token_type,
        "exp": expire,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc


def create_admin_token(admin_id: int, username: str) -> str:
    return create_token(str(admin_id), ADMIN_TOKEN_TYPE, {"username": username})


def create_database_token(database_id: int, slug: str, username: str) -> str:
    return create_token(
        str(database_id),
        DATABASE_TOKEN_TYPE,
        {"database_id": database_id, "slug": slug, "username": username},
    )
