from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from admin.context import url_context
from admin.deps import get_current_admin
from shared.config import settings
from shared.integration import build_integration_prompt, build_table_api_examples
from shared.meta_db import get_db
from shared.models import Admin, Database, TableDefinition
from shared.secrets import decrypt_password

router = APIRouter(tags=["pages"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))
templates.env.globals["base_path"] = "/db"


def _optional_admin(request: Request, db: Session) -> Admin | None:
    from admin.deps import ADMIN_COOKIE
    from shared.auth import ADMIN_TOKEN_TYPE, decode_token

    token = request.cookies.get(ADMIN_COOKIE)
    if not token:
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") != ADMIN_TOKEN_TYPE:
            return None
        return db.scalar(select(Admin).where(Admin.id == int(payload["sub"])))
    except (ValueError, KeyError):
        return None


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if _optional_admin(request, db):
        return RedirectResponse("/db/", status_code=303)
    return templates.TemplateResponse(request, "login.html")


@router.get("/", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
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

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "admin": admin,
            "databases": rows,
            **url_context(),
        },
    )


@router.get("/databases/new", response_class=HTMLResponse)
def new_database_page(request: Request, admin: Admin = Depends(get_current_admin)):
    return templates.TemplateResponse(request, "database_new.html", {"admin": admin})


@router.get("/databases/{database_id}", response_class=HTMLResponse)
def database_detail(
    database_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    database = db.scalar(
        select(Database)
        .where(Database.id == database_id)
        .options(selectinload(Database.tables).selectinload(TableDefinition.columns))
    )
    if database is None:
        return RedirectResponse("/db/", status_code=303)

    client_password = decrypt_password(database.password_encrypted or "", settings.jwt_secret)
    ctx = url_context(database, client_password)
    table_examples = [
        {"table": t, "examples": build_table_api_examples(ctx["api_url"], t)}
        for t in database.tables
    ]
    integration_prompt = build_integration_prompt(ctx["api_url"], database, client_password, ctx["admin_url"])

    return templates.TemplateResponse(
        request,
        "database_detail.html",
        {
            "admin": admin,
            "database": database,
            "client_password": client_password,
            "integration_prompt": integration_prompt,
            "table_examples": table_examples,
            "prompt_ready": client_password is not None,
            **ctx,
        },
    )


@router.get("/databases/{database_id}/tables/new", response_class=HTMLResponse)
def new_table_page(
    database_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    database = db.get(Database, database_id)
    if database is None:
        return RedirectResponse("/db/", status_code=303)

    client_password = decrypt_password(database.password_encrypted or "", settings.jwt_secret)
    return templates.TemplateResponse(
        request,
        "table_new.html",
        {"admin": admin, "database": database, **url_context(database, client_password)},
    )


@router.get("/tables/{table_id}", response_class=HTMLResponse)
def table_detail(
    table_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: Admin = Depends(get_current_admin),
):
    table = db.scalar(
        select(TableDefinition)
        .where(TableDefinition.id == table_id)
        .options(selectinload(TableDefinition.columns), selectinload(TableDefinition.database))
    )
    if table is None:
        return RedirectResponse("/db/", status_code=303)

    database = table.database
    client_password = decrypt_password(database.password_encrypted or "", settings.jwt_secret)
    ctx = url_context(database, client_password)
    examples = build_table_api_examples(ctx["api_url"], table)

    return templates.TemplateResponse(
        request,
        "table_detail.html",
        {"admin": admin, "table": table, "examples": examples, **ctx},
    )
