from urllib.parse import quote

from shared.config import settings
from shared.models import Database

DB_PREFIX = "/db"


def tenant_api_url(username: str, password: str) -> str:
    return (
        f"http://{settings.host}:{settings.admin_port}"
        f"/api/{quote(username, safe='')}/{quote(password, safe='')}"
    )


def url_context(database: Database | None = None, password: str | None = None) -> dict[str, str]:
    admin_url = f"{settings.admin_base_url}{DB_PREFIX}"
    placeholder = f"http://{settings.host}:{settings.admin_port}/api/<username>/<password>"

    if database and password:
        api_url = tenant_api_url(database.username, password)
        local_api = (
            f"http://localhost:{settings.admin_port}"
            f"/api/{quote(database.username, safe='')}/{quote(password, safe='')}"
        )
    else:
        api_url = placeholder
        local_api = f"http://localhost:{settings.admin_port}/api/<username>/<password>"

    return {
        "api_url": api_url,
        "admin_url": admin_url,
        "base_path": DB_PREFIX,
        "host": settings.host,
        "localhost_api_url": local_api,
        "localhost_admin_url": f"http://localhost:{settings.admin_port}{DB_PREFIX}",
    }
