from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import auth, data
from shared.config import settings
from shared.meta_db import init_meta_db

app = FastAPI(title="DB API", docs_url="/docs", redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(data.router)


@app.on_event("startup")
def startup() -> None:
    init_meta_db()


@app.get("/")
def root():
    return {
        "service": "database-api",
        "login": "POST /auth/login",
        "docs": "/docs",
    }
