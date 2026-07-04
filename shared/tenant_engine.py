import json
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from shared.config import TENANTS_DIR
from shared.models import ColumnDefinition, ColumnType, TableDefinition

SQLITE_TYPE_MAP = {
    ColumnType.TEXT.value: "TEXT",
    ColumnType.INTEGER.value: "INTEGER",
    ColumnType.FLOAT.value: "REAL",
    ColumnType.BOOLEAN.value: "INTEGER",
    ColumnType.DATETIME.value: "TEXT",
    ColumnType.JSON.value: "TEXT",
}


def tenant_db_path(slug: str) -> Path:
    return TENANTS_DIR / f"{slug}.db"


def get_tenant_engine(sqlite_path: str) -> Engine:
    path = Path(sqlite_path).as_posix()
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def create_tenant_file(slug: str) -> str:
    path = tenant_db_path(slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = get_tenant_engine(str(path))
    engine.dispose()
    return str(path)


def delete_tenant_file(sqlite_path: str) -> None:
    path = Path(sqlite_path)
    if path.exists():
        path.unlink()


def _column_sql(col: ColumnDefinition) -> str:
    sql_type = SQLITE_TYPE_MAP.get(col.type, "TEXT")
    parts = [f'"{col.name}"', sql_type]
    if col.is_primary_key:
        parts.append("PRIMARY KEY")
        if col.type == ColumnType.INTEGER.value:
            parts.append("AUTOINCREMENT")
    if not col.nullable and not col.is_primary_key:
        parts.append("NOT NULL")
    if col.default_value is not None and not col.is_primary_key:
        parts.append(f"DEFAULT {col.default_value}")
    return " ".join(parts)


def create_table_ddl(table: TableDefinition) -> None:
    engine = get_tenant_engine(table.database.sqlite_path)
    cols_sql = ", ".join(_column_sql(c) for c in table.columns)
    ddl = f'CREATE TABLE IF NOT EXISTS "{table.name}" ({cols_sql})'
    with engine.begin() as conn:
        conn.execute(text(ddl))


def drop_table_ddl(sqlite_path: str, table_name: str) -> None:
    engine = get_tenant_engine(sqlite_path)
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))


def reflect_table(engine: Engine, table_name: str) -> Table:
    metadata = MetaData()
    return Table(table_name, metadata, autoload_with=engine)


def get_primary_key_column(table: TableDefinition) -> ColumnDefinition:
    for col in table.columns:
        if col.is_primary_key:
            return col
    raise ValueError("No primary key defined")


def validate_row_values(table: TableDefinition, data: dict[str, Any], for_update: bool = False) -> dict[str, Any]:
    col_map = {c.name: c for c in table.columns}
    validated: dict[str, Any] = {}

    for key, value in data.items():
        if key not in col_map:
            raise ValueError(f"Unknown column: {key}")
        col = col_map[key]
        if col.is_primary_key and for_update:
            raise ValueError("Primary key cannot be updated")
        validated[key] = coerce_value(col, value)

    if not for_update:
        for col in table.columns:
            if col.is_primary_key:
                continue
            if col.name not in validated and not col.nullable and col.default_value is None:
                raise ValueError(f"Missing required column: {col.name}")

    return validated


def coerce_value(col: ColumnDefinition, value: Any) -> Any:
    if value is None:
        if not col.nullable and not col.is_primary_key:
            raise ValueError(f"Column {col.name} cannot be null")
        return None

    col_type = col.type
    try:
        if col_type == ColumnType.TEXT.value:
            return str(value)
        if col_type == ColumnType.INTEGER.value:
            return int(value)
        if col_type == ColumnType.FLOAT.value:
            return float(value)
        if col_type == ColumnType.BOOLEAN.value:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, str):
                return 1 if value.lower() in ("true", "1", "yes") else 0
            return int(bool(value))
        if col_type == ColumnType.DATETIME.value:
            return str(value)
        if col_type == ColumnType.JSON.value:
            if isinstance(value, (dict, list)):
                return json.dumps(value)
            if isinstance(value, str):
                json.loads(value)
                return value
            return json.dumps(value)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid value for column {col.name}") from exc

    return value


def serialize_row(table: TableDefinition, row: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    col_map = {c.name: c for c in table.columns}
    for key, value in row.items():
        col = col_map.get(key)
        if col and col.type == ColumnType.JSON.value and isinstance(value, str):
            try:
                result[key] = json.loads(value)
            except json.JSONDecodeError:
                result[key] = value
        elif col and col.type == ColumnType.BOOLEAN.value:
            result[key] = bool(value)
        else:
            result[key] = value
    return result


def list_rows(
    table: TableDefinition,
    sqlite_path: str,
    limit: int = 50,
    offset: int = 0,
    sort: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    engine = get_tenant_engine(sqlite_path)
    inspector = inspect(engine)
    if table.name not in inspector.get_table_names():
        return [], 0

    pk = get_primary_key_column(table)
    order_col = sort if sort and sort in {c.name for c in table.columns} else pk.name

    with engine.connect() as conn:
        count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table.name}"'))
        total = count_result.scalar() or 0
        result = conn.execute(
            text(f'SELECT * FROM "{table.name}" ORDER BY "{order_col}" LIMIT :limit OFFSET :offset'),
            {"limit": limit, "offset": offset},
        )
        rows = [dict(r._mapping) for r in result]

    return [serialize_row(table, r) for r in rows], total


def get_row(table: TableDefinition, sqlite_path: str, row_id: Any) -> dict[str, Any] | None:
    engine = get_tenant_engine(sqlite_path)
    pk = get_primary_key_column(table)
    pk_value = coerce_value(pk, row_id)

    with engine.connect() as conn:
        result = conn.execute(
            text(f'SELECT * FROM "{table.name}" WHERE "{pk.name}" = :id'),
            {"id": pk_value},
        )
        row = result.mappings().first()
        if row is None:
            return None
        return serialize_row(table, dict(row))


def insert_row(table: TableDefinition, sqlite_path: str, data: dict[str, Any]) -> dict[str, Any]:
    validated = validate_row_values(table, data)
    engine = get_tenant_engine(sqlite_path)
    cols = list(validated.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    col_names = ", ".join(f'"{c}"' for c in cols)
    stmt = text(f'INSERT INTO "{table.name}" ({col_names}) VALUES ({placeholders})')

    with engine.begin() as conn:
        conn.execute(stmt, validated)
        if any(c.is_primary_key and c.type == ColumnType.INTEGER.value for c in table.columns):
            pk = get_primary_key_column(table)
            if pk.name not in validated:
                new_id = conn.execute(text("SELECT last_insert_rowid()")).scalar()
                validated[pk.name] = new_id

    pk = get_primary_key_column(table)
    row_id = validated.get(pk.name)
    if row_id is not None:
        row = get_row(table, sqlite_path, row_id)
        if row:
            return row
    return validated


def update_row(table: TableDefinition, sqlite_path: str, row_id: Any, data: dict[str, Any]) -> dict[str, Any] | None:
    validated = validate_row_values(table, data, for_update=True)
    if not validated:
        return get_row(table, sqlite_path, row_id)

    engine = get_tenant_engine(sqlite_path)
    pk = get_primary_key_column(table)
    pk_value = coerce_value(pk, row_id)
    set_clause = ", ".join(f'"{k}" = :{k}' for k in validated.keys())
    params = {**validated, "pk": pk_value}
    stmt = text(f'UPDATE "{table.name}" SET {set_clause} WHERE "{pk.name}" = :pk')

    with engine.begin() as conn:
        result = conn.execute(stmt, params)
        if result.rowcount == 0:
            return None

    return get_row(table, sqlite_path, row_id)


def delete_row(table: TableDefinition, sqlite_path: str, row_id: Any) -> bool:
    engine = get_tenant_engine(sqlite_path)
    pk = get_primary_key_column(table)
    pk_value = coerce_value(pk, row_id)
    stmt = text(f'DELETE FROM "{table.name}" WHERE "{pk.name}" = :id')

    with engine.begin() as conn:
        result = conn.execute(stmt, {"id": pk_value})
        return result.rowcount > 0
