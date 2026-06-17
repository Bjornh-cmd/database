from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from admin.routes import api as admin_api
from admin.routes import pages
from api.routes import tenant
from shared.config import settings
from shared.meta_db import init_meta_db

STATIC_DIR = Path(__file__).resolve().parent / "static"
DB_PREFIX = "/db"

app = FastAPI(title="DB Platform", docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root_not_found():
    return PlainTextResponse("ERROR not found", status_code=404)


app.mount(f"{DB_PREFIX}/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(pages.router, prefix=DB_PREFIX)
app.include_router(admin_api.router, prefix=f"{DB_PREFIX}/api")
app.include_router(tenant.router, prefix="/api/{username}/{password}")


@app.on_event("startup")
def startup() -> None:
    init_meta_db()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    path = request.url.path
    if exc.status_code == 401 and path.startswith(DB_PREFIX) and not path.startswith(f"{DB_PREFIX}/api"):
        return RedirectResponse(f"{DB_PREFIX}/login", status_code=303)
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
