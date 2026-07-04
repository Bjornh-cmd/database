from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from shared.models import ColumnType, IDENTIFIER_PATTERN, SLUG_PATTERN


class ColumnCreate(BaseModel):
    name: str
    type: ColumnType
    nullable: bool = True
    is_primary_key: bool = False
    default_value: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not IDENTIFIER_PATTERN.match(v):
            raise ValueError("Invalid column name")
        return v


class ColumnOut(BaseModel):
    id: int
    name: str
    type: str
    nullable: bool
    is_primary_key: bool
    default_value: str | None

    model_config = {"from_attributes": True}


class TableCreate(BaseModel):
    name: str
    columns: list[ColumnCreate] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not IDENTIFIER_PATTERN.match(v):
            raise ValueError("Invalid table name")
        return v

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, v: list[ColumnCreate]) -> list[ColumnCreate]:
        pk_count = sum(1 for c in v if c.is_primary_key)
        if pk_count != 1:
            raise ValueError("Exactly one primary key column is required")
        names = [c.name for c in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate column names")
        return v


class TableOut(BaseModel):
    id: int
    name: str
    columns: list[ColumnOut]
    created_at: datetime

    model_config = {"from_attributes": True}


class DatabaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    slug: str
    username: str
    password: str = Field(min_length=4)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.lower().strip()
        if not SLUG_PATTERN.match(v):
            raise ValueError("Invalid slug")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not IDENTIFIER_PATTERN.match(v):
            raise ValueError("Invalid username")
        return v


class DatabaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    password: str | None = Field(default=None, min_length=4)


class DatabaseOut(BaseModel):
    id: int
    name: str
    slug: str
    username: str
    sqlite_path: str
    created_at: datetime
    tables: list[TableOut] = []

    model_config = {"from_attributes": True}


class DatabaseListItem(BaseModel):
    id: int
    name: str
    slug: str
    username: str
    created_at: datetime
    table_count: int = 0

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DatabaseInfo(BaseModel):
    id: int
    name: str
    slug: str


class AuthMeResponse(BaseModel):
    database: DatabaseInfo


class TableSchemaOut(BaseModel):
    name: str
    columns: list[ColumnOut]


class RowQueryParams(BaseModel):
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
    sort: str | None = None


class RowListResponse(BaseModel):
    rows: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
