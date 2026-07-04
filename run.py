"""Start unified server on port 5505."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shared.config import settings  # noqa: E402
from shared.meta_db import init_meta_db  # noqa: E402


def main() -> None:
    import uvicorn

    init_meta_db()
    host = settings.host
    port = settings.admin_port
    print(f"Host IP:  {host}")
    print(f"Root:     http://{host}:{port}/  -> ERROR not found (veiligheid)")
    print(f"Admin:    http://{host}:{port}/db/login")
    print(f"API:      http://{host}:{port}/api/<username>/<password>/...")
    print(f"Default admin: {settings.admin_username}")

    uvicorn.run("admin.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
