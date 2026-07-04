from urllib.parse import quote

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from shared.auth import verify_password
from shared.meta_db import get_db
from shared.models import Database, TableDefinition


def get_database_by_credentials(
    username: str,
    password: str,
    db: Session = Depends(get_db),
) -> Database:
    database = db.scalar(
        select(Database)
        .where(Database.username == username)
        .options(selectinload(Database.tables).selectinload(TableDefinition.columns))
    )
    if database is None or not verify_password(password, database.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return database


def get_table_by_name(database: Database, table_name: str) -> TableDefinition:
    for table in database.tables:
        if table.name == table_name:
            return table
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
