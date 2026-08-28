from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db import Base
from app import db as db_module
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, 'data_dir', tmp_path)
    (tmp_path / 'uploads').mkdir(parents=True, exist_ok=True)

    test_engine = create_engine(
        f'sqlite:///{tmp_path / "test.db"}',
        connect_args={'check_same_thread': False},
    )

    @event.listens_for(test_engine, 'connect')
    def _enable_fk(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

    TestSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(db_module, 'engine', test_engine)
    monkeypatch.setattr(db_module, 'SessionLocal', TestSession)

    with TestClient(app) as test_client:
        yield test_client

    test_engine.dispose()
    app.dependency_overrides.clear()
