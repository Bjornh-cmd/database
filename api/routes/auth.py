from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.deps import get_current_database
from shared.auth import create_database_token, verify_password
from shared.meta_db import get_db
from shared.models import Database
from shared.schemas import AuthMeResponse, DatabaseInfo, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    database = db.scalar(select(Database).where(Database.username == body.username))
    if database is None or not verify_password(body.password, database.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_database_token(database.id, database.slug, database.username)
    return {
        "access_token": token,
        "token_type": "bearer",
        "database": DatabaseInfo(id=database.id, name=database.name, slug=database.slug),
    }


@router.get("/me", response_model=AuthMeResponse)
def me(database: Database = Depends(get_current_database)):
    return AuthMeResponse(
        database=DatabaseInfo(id=database.id, name=database.name, slug=database.slug)
    )
