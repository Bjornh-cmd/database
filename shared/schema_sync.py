import json
import re
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from shared.models import IDENTIFIER_PATTERN, ColumnDefinition, ColumnType, Database, TableDefinition
from shared.tenant_engine import SQLITE_TYPE_MAP, create_table_ddl, get_tenant_engine

ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?)?$"
)


def infer_column_type(value: Any) -> str:
    if value is None:
        return ColumnType.TEXT.value
    if isinstance(value, bool):
        return ColumnType.BOOLEAN.value
    if isinstance(value, int):
        return ColumnType.INTEGER.value
    if isinstance(value, float):
        return ColumnType.FLOAT.value
    if isinstance(value, (dict, list)):
        return ColumnType.JSON.value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith(("{", "[")):
            try:
                json.loads(stripped)
                return ColumnType.JSON.value
            except json.JSONDecodeError:
                pass
        if ISO_DATETIME_RE.match(stripped):
            return ColumnType.DATETIME.value
    return ColumnType.TEXT.value


def _column_exists_in_sqlite(sqlite_path: str, table_name: str, column_name: str) -> bool:
    engine = get_tenant_engine(sqlite_path)
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {c["name"] for c in inspector.get_columns(table_name)}


def add_column_ddl(sqlite_path: str, table_name: str, col: ColumnDefinition) -> None:
    if _column_exists_in_sqlite(sqlite_path, table_name, col.name):
        return
    sql_type = SQLITE_TYPE_MAP.get(col.type, "TEXT")
    nullable_sql = "" if col.nullable else " NOT NULL"
    ddl = f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {sql_type}{nullable_sql}'
    engine = get_tenant_engine(sqlite_path)
    with engine.begin() as conn:
        conn.execute(text(ddl))


def ensure_columns_from_data(
    db: Session,
    table: TableDefinition,
    sqlite_path: str,
    data: dict[str, Any],
) -> list[str]:
    """Add missing columns to metadata + tenant SQLite based on request body keys."""
    existing = {c.name for c in table.columns}
    added: list[str] = []

    for key, value in data.items():
        if key in existing:
            continue
        if not IDENTIFIER_PATTERN.match(key):
            raise ValueError(f"Invalid column name: {key}")

        col_type = infer_column_type(value)
        col_def = ColumnDefinition(
            table_id=table.id,
            name=key,
            type=col_type,
            nullable=True,
            is_primary_key=False,
        )
        db.add(col_def)
        db.flush()
        add_column_ddl(sqlite_path, table.name, col_def)
        table.columns.append(col_def)
        existing.add(key)
        added.append(key)

    if added:
        db.commit()

    return added


def find_table(database: Database, table_name: str) -> TableDefinition | None:
    for table in database.tables:
        if table.name == table_name:
            return table
    return None


def ensure_table_from_data(
    db: Session,
    database: Database,
    table_name: str,
    data: dict[str, Any],
) -> TableDefinition:
    """Create table metadata + SQLite table when it does not exist yet."""
    existing = find_table(database, table_name)
    if existing is not None:
        return existing

    if not IDENTIFIER_PATTERN.match(table_name):
        raise ValueError(f"Invalid table name: {table_name}")

    table = TableDefinition(database_id=database.id, name=table_name)
    table.columns.append(
        ColumnDefinition(
            name="id",
            type=ColumnType.INTEGER.value,
            nullable=False,
            is_primary_key=True,
        )
    )

    for key, value in data.items():
        if key == "id":
            continue
        if not IDENTIFIER_PATTERN.match(key):
            raise ValueError(f"Invalid column name: {key}")
        table.columns.append(
            ColumnDefinition(
                name=key,
                type=infer_column_type(value),
                nullable=True,
                is_primary_key=False,
            )
        )

    db.add(table)
    db.flush()
    table.database = database
    create_table_ddl(table)
    db.commit()
    db.refresh(table, attribute_names=["columns"])
    database.tables.append(table)
    return table
