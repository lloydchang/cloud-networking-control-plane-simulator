import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure we don't try to write to /app/data during local tests
# Set these BEFORE importing any project modules
os.environ["DB_DIR"] = "."
os.environ["DB_PATH"] = "./network_test.db"
os.environ["VERCEL"] = "1"  # Prevent directory creation during tests

# Add the control-plane and api directories to sys.path
# Required for gRPC generated stubs to find each other
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "api"))

from api.models import Base

# Setup in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./network_test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


@pytest.fixture
def db_factory():
    return TestingSessionLocal
