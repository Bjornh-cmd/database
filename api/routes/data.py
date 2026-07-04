from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_database
from shared.meta_db import get_db
from shared.models import Database
from shared.schema_sync import ensure_columns_from_data, ensure_table_from_data, find_table
from shared.schemas import ColumnOut, RowListResponse, TableSchemaOut
from shared.tenant_engine import (
    delete_row,
    get_row,
    insert_row,
    list_rows,
    update_row,
)

router = APIRouter(tags=["data"])


@router.get("/tables", response_model=list[TableSchemaOut])
def list_tables(database: Database = Depends(get_current_database)):
    return [
        TableSchemaOut(
            name=table.name,
            columns=[ColumnOut.model_validate(c) for c in table.columns],
        )
        for table in database.tables
    ]


@router.get("/{table_name}", response_model=RowListResponse)
def list_table_rows(
    table_name: str,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort: str | None = None,
    database: Database = Depends(get_current_database),
):
    table = find_table(database, table_name)
    if table is None:
        return RowListResponse(rows=[], total=0, limit=limit, offset=offset)
    rows, total = list_rows(table, database.sqlite_path, limit=limit, offset=offset, sort=sort)
    return RowListResponse(rows=rows, total=total, limit=limit, offset=offset)


@router.get("/{table_name}/{row_id}")
def get_table_row(
    table_name: str,
    row_id: str,
    database: Database = Depends(get_current_database),
):
    table = find_table(database, table_name)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    row = get_row(table, database.sqlite_path, row_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Row not found")
    return row


@router.post("/{table_name}", status_code=status.HTTP_201_CREATED)
def create_row(
    table_name: str,
    body: dict[str, Any],
    db: Session = Depends(get_db),
    database: Database = Depends(get_current_database),
):
    try:
        table = ensure_table_from_data(db, database, table_name, body)
        ensure_columns_from_data(db, table, database.sqlite_path, body)
        return insert_row(table, database.sqlite_path, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("/{table_name}/{row_id}")
def patch_row(
    table_name: str,
    row_id: str,
    body: dict[str, Any],
    db: Session = Depends(get_db),
    database: Database = Depends(get_current_database),
):
    table = find_table(database, table_name)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    try:
        ensure_columns_from_data(db, table, database.sqlite_path, body)
        row = update_row(table, database.sqlite_path, row_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Row not found")
    return row


@router.delete("/{table_name}/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_row(
    table_name: str,
    row_id: str,
    database: Database = Depends(get_current_database),
):
    table = find_table(database, table_name)
    if table is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    if not delete_row(table, database.sqlite_path, row_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Row not found")
