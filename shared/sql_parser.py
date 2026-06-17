import re
from dataclasses import dataclass

from shared.models import ColumnType, IDENTIFIER_PATTERN

CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r'(?:"([^"]+)"|\'([^\']+)\'|`([^`]+)`|(\w+))\s*\(',
    re.IGNORECASE,
)

SQLITE_TYPE_MAP = {
    "INT": ColumnType.INTEGER.value,
    "INTEGER": ColumnType.INTEGER.value,
    "BIGINT": ColumnType.INTEGER.value,
    "SMALLINT": ColumnType.INTEGER.value,
    "TINYINT": ColumnType.INTEGER.value,
    "REAL": ColumnType.FLOAT.value,
    "FLOAT": ColumnType.FLOAT.value,
    "DOUBLE": ColumnType.FLOAT.value,
    "NUMERIC": ColumnType.FLOAT.value,
    "DECIMAL": ColumnType.FLOAT.value,
    "TEXT": ColumnType.TEXT.value,
    "VARCHAR": ColumnType.TEXT.value,
    "CHAR": ColumnType.TEXT.value,
    "STRING": ColumnType.TEXT.value,
    "CLOB": ColumnType.TEXT.value,
    "BLOB": ColumnType.TEXT.value,
    "BOOLEAN": ColumnType.BOOLEAN.value,
    "BOOL": ColumnType.BOOLEAN.value,
    "DATETIME": ColumnType.DATETIME.value,
    "DATE": ColumnType.DATETIME.value,
    "TIMESTAMP": ColumnType.DATETIME.value,
    "JSON": ColumnType.JSON.value,
}


@dataclass
class ParsedColumn:
    name: str
    type: str
    nullable: bool
    is_primary_key: bool


@dataclass
class ParsedCreateTable:
    name: str
    columns: list[ParsedColumn]


def _split_column_defs(body: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in body:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "," and depth == 0:
            part = "".join(current).strip()
            if part:
                parts.append(part)
            current = []
        else:
            current.append(char)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _is_table_constraint(part: str) -> bool:
    upper = part.strip().upper()
    return upper.startswith(("PRIMARY KEY", "FOREIGN KEY", "UNIQUE", "CHECK", "CONSTRAINT"))


def _parse_column(part: str) -> ParsedColumn | None:
    part = part.strip()
    if not part or _is_table_constraint(part):
        return None

    match = re.match(
        r'^["\']?(\w+)["\']?\s+([A-Z]+(?:\([^)]*\))?)(.*)$',
        part,
        re.IGNORECASE,
    )
    if not match:
        return None

    name, raw_type, constraints = match.group(1), match.group(2), match.group(3).upper()
    base_type = re.match(r"([A-Z]+)", raw_type.upper())
    if not base_type:
        return None

    col_type = SQLITE_TYPE_MAP.get(base_type.group(1), ColumnType.TEXT.value)
    is_pk = "PRIMARY KEY" in constraints or "PRIMARY KEY" in part.upper()
    nullable = "NOT NULL" not in constraints and not is_pk

    if not IDENTIFIER_PATTERN.match(name):
        raise ValueError(f"Ongeldige kolomnaam: {name}")

    return ParsedColumn(name=name, type=col_type, nullable=nullable, is_primary_key=is_pk)


def parse_create_table(sql: str) -> ParsedCreateTable:
    cleaned = sql.strip().rstrip(";").strip()
    match = CREATE_TABLE_RE.search(cleaned)
    if not match:
        raise ValueError("Geen geldige CREATE TABLE statement gevonden")

    table_name = match.group(1) or match.group(2) or match.group(3) or match.group(4)
    if table_name in ("<table>", "table"):
        raise ValueError("Vervang <table> door een echte tabelnaam")

    if not IDENTIFIER_PATTERN.match(table_name):
        raise ValueError(f"Ongeldige tabelnaam: {table_name}")

    start = match.end()
    depth = 1
    end = start
    while end < len(cleaned) and depth > 0:
        if cleaned[end] == "(":
            depth += 1
        elif cleaned[end] == ")":
            depth -= 1
        end += 1

    if depth != 0:
        raise ValueError("Ongeldige CREATE TABLE syntax (haakjes niet gesloten)")

    body = cleaned[start : end - 1]
    columns: list[ParsedColumn] = []
    for part in _split_column_defs(body):
        col = _parse_column(part)
        if col:
            columns.append(col)

    if not columns:
        raise ValueError("Geen kolommen gevonden in CREATE TABLE")

    pk_count = sum(1 for c in columns if c.is_primary_key)
    if pk_count != 1:
        raise ValueError("Precies één PRIMARY KEY kolom is vereist")

    return ParsedCreateTable(name=table_name, columns=columns)
