from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.auth import hash_password
from shared.config import DATA_DIR, META_DB_PATH, TENANTS_DIR, settings
from shared.models import Admin, Base

engine = create_engine(f"sqlite:///{META_DB_PATH.as_posix()}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _migrate_meta_db() -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    if "databases" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("databases")}
    if "password_encrypted" not in columns:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE databases ADD COLUMN password_encrypted TEXT"))


def init_meta_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TENANTS_DIR.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    _migrate_meta_db()

    from sqlalchemy import select

    with SessionLocal() as session:
        admin = session.scalar(select(Admin).where(Admin.username == settings.admin_username))
        if admin is None:
            admin = session.scalar(select(Admin).limit(1))
            if admin is None:
                session.add(
                    Admin(
                        username=settings.admin_username,
                        password_hash=hash_password(settings.admin_password),
                    )
                )
            else:
                admin.username = settings.admin_username
                admin.password_hash = hash_password(settings.admin_password)
        else:
            admin.password_hash = hash_password(settings.admin_password)
        session.commit()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
