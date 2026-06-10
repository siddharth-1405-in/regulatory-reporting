"""Pytest fixtures — isolated SQLite DB for integration tests.

DATABASE_URL is set before any app import so the engine binds to the test DB.
"""
import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.gettempdir(), "car_test.db")

import pytest  # noqa: E402

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.services import ownership_service, report_instance_service  # noqa: E402
from scripts.seed_db import seed_canonical_elements, seed_circular_changes  # noqa: E402


@pytest.fixture
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    report_instance_service.get_or_create_pack(session)
    seed_canonical_elements(session)
    ownership_service.seed_assignments(session)
    seed_circular_changes(session)
    session.commit()
    try:
        yield session
    finally:
        session.close()
