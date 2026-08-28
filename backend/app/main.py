from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db as db_module
from app.db import Base
from app.errors import register_error_handlers
from app import models as _models  # noqa: F401 — register metadata
from app.routers import comparisons, files, profiles
from app.seed import seed_profiles
from app.services.storage import ensure_data_dirs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
    Base.metadata.create_all(bind=db_module.engine)
    session = db_module.SessionLocal()
    try:
        seed_profiles(session)
    finally:
        session.close()
    yield


app = FastAPI(title='Kosztomator', lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        'http://localhost:4200',
        'http://127.0.0.1:4200',
    ],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(files.router, prefix='/api')
app.include_router(profiles.router, prefix='/api')
app.include_router(comparisons.router, prefix='/api')


@app.get('/api/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}
