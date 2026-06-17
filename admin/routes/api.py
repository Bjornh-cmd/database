from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from admin.deps import ADMIN_COOKIE, get_current_admin
from shared.auth import create_admin_token, hash_password, verify_password
from shared.config import settings
from shared.meta_db import get_db
from shared.models import Admin, ColumnDefinition, Database, TableDefinition
from shared.secrets import encrypt_password
from shared.sql_parser import parse_create_table
from shared.schemas import (
    DatabaseCreate,
    DatabaseListItem,
    DatabaseOut,
    DatabaseUpdate,
    TableCreate,
    TableOut,
)
from shared.tenant_engine import (
    create_table_ddl,
    create_tenant_file,
    delete_tenant_file,
    drop_table_ddl,
    list_rows,
)

router = APIRouter(prefix="/api", tags=["admin-api"])


@router.post("/login")
def api_login(body: dict, db: Session = Depends(get_db)):
    username = body.get("username", "")
    password = body.get("password", "")
    admin = db.scalar(select(Admin).where(Admin.username == username))
    if admin is None or not verify_password(password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_admin_token(admin.id, admin.username)
    resp = JSONResponse({"access_token": token, "token_type": "bearer"})
    resp.set_cookie(ADMIN_COOKIE, token, httponly=True, samesite="lax", max_age=86400)
    return resp


@router.post("/logout")
def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(ADMIN_COOKIE)
    return resp


@router.get("/databases", response_model=list[DatabaseListItem])
def list_databases(
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    rows = db.execute(
        select(
            Database.id,
            Database.name,
            Database.slug,
            Database.username,
            Database.created_at,
            func.count(TableDefinition.id).label("table_count"),
        )
        .outerjoin(TableDefinition, TableDefinition.database_id == Database.id)
        .group_by(Database.id)
        .order_by(Database.created_at.desc())
    ).all()
    return [
        DatabaseListItem(
            id=r.id,
            name=r.name,
            slug=r.slug,
            username=r.username,
            created_at=r.created_at,
            table_count=r.table_count,
        )
        for r in rows
    ]


@router.post("/databases", response_model=DatabaseOut, status_code=status.HTTP_201_CREATED)
def create_database(
    body: DatabaseCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    if db.scalar(select(Database).where(Database.slug == body.slug)):
        raise HTTPException(status_code=400, detail="Slug already exists")
    if db.scalar(select(Database).where(Database.username == body.username)):
        raise HTTPException(status_code=400, detail="Username already exists")

    sqlite_path = create_tenant_file(body.slug)
    database = Database(
        name=body.name,
        slug=body.slug,
        username=body.username,
        password_hash=hash_password(body.password),
        password_encrypted=encrypt_password(body.password, settings.jwt_secret),
        sqlite_path=sqlite_path,
    )
    db.add(database)
    db.commit()
    db.refresh(database)
    return DatabaseOut.model_validate(database)


@router.get("/databases/{database_id}", response_model=DatabaseOut)
def get_database(
    database_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    database = db.scalar(
        select(Database)
        .where(Database.id == database_id)
        .options(selectinload(Database.tables).selectinload(TableDefinition.columns))
    )
    if database is None:
        raise HTTPException(status_code=404, detail="Database not found")
    return DatabaseOut.model_validate(database)


@router.patch("/databases/{database_id}", response_model=DatabaseOut)
def update_database(
    database_id: int,
    body: DatabaseUpdate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    database = db.scalar(
        select(Database)
        .where(Database.id == database_id)
        .options(selectinload(Database.tables).selectinload(TableDefinition.columns))
    )
    if database is None:
        raise HTTPException(status_code=404, detail="Database not found")

    if body.name is not None:
        database.name = body.name
    if body.password is not None:
        database.password_hash = hash_password(body.password)
        database.password_encrypted = encrypt_password(body.password, settings.jwt_secret)

    db.commit()
    db.refresh(database)
    return DatabaseOut.model_validate(database)


@router.delete("/databases/{database_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_database(
    database_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    database = db.get(Database, database_id)
    if database is None:
        raise HTTPException(status_code=404, detail="Database not found")

    sqlite_path = database.sqlite_path
    db.delete(database)
    db.commit()
    delete_tenant_file(sqlite_path)


@router.post("/databases/{database_id}/tables", response_model=TableOut, status_code=status.HTTP_201_CREATED)
def create_table(
    database_id: int,
    body: TableCreate,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    database = db.scalar(
        select(Database)
        .where(Database.id == database_id)
        .options(selectinload(Database.tables))
    )
    if database is None:
        raise HTTPException(status_code=404, detail="Database not found")

    if any(t.name == body.name for t in database.tables):
        raise HTTPException(status_code=400, detail="Table already exists")

    table = TableDefinition(database_id=database.id, name=body.name)
    for col in body.columns:
        table.columns.append(
            ColumnDefinition(
                name=col.name,
                type=col.type.value,
                nullable=col.nullable,
                is_primary_key=col.is_primary_key,
                default_value=col.default_value,
            )
        )

    db.add(table)
    db.flush()
    db.refresh(table, attribute_names=["columns"])
    table.database = database
    create_table_ddl(table)
    db.commit()
    db.refresh(table)
    return TableOut.model_validate(table)


@router.delete("/tables/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    table = db.scalar(
        select(TableDefinition)
        .where(TableDefinition.id == table_id)
        .options(selectinload(TableDefinition.database), selectinload(TableDefinition.columns))
    )
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    sqlite_path = table.database.sqlite_path
    table_name = table.name
    db.delete(table)
    db.commit()
    drop_table_ddl(sqlite_path, table_name)


@router.get("/tables/{table_id}/rows")
def preview_rows(
    table_id: int,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: Admin = Depends(get_current_admin),
):
    table = db.scalar(
        select(TableDefinition)
        .where(TableDefinition.id == table_id)
        .options(selectinload(TableDefinition.columns), selectinload(TableDefinition.database))
    )
    if table is None:
        raise HTTPException(status_code=404, detail="Table not found")

    rows, total = list_rows(table, table.database.sqlite_path, limit=limit, offset=offset)
    return {"rows": rows, "total": total, "limit": limit, "offset": offset}


@router.post("/parse-create-table")
def parse_create_table_endpoint(body: dict, _: Admin = Depends(get_current_admin)):
    sql = body.get("sql", "")
    if not sql.strip():
        raise HTTPException(status_code=422, detail="SQL is leeg")
    try:
        parsed = parse_create_table(sql)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "name": parsed.name,
        "columns": [
            {
                "name": c.name,
                "type": c.type,
                "nullable": c.nullable,
                "is_primary_key": c.is_primary_key,
            }
            for c in parsed.columns
        ],
    }
