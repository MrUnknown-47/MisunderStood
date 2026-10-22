import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.integrations.ai_client import get_ai_client, MockAIClient


# In-memory SQLite database for isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh in-memory database for each test function."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provide a FastAPI TestClient with database and AI mocks wired in."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_ai():
        return MockAIClient()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_ai_client] = override_get_ai
    
    with TestClient(app) as test_client:
        yield test_client
        
    app.dependency_overrides.clear()
