from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ContentProposal, WorkflowRun


client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "seo-agent-mvp"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield session
    finally:
        app.dependency_overrides.clear()
        session.close()
        Base.metadata.drop_all(bind=engine)


def create_proposal(db_session) -> ContentProposal:
    workflow_run = WorkflowRun(category_name="Test category", status="needs_review")
    db_session.add(workflow_run)
    db_session.commit()
    db_session.refresh(workflow_run)

    proposal = ContentProposal(
        workflow_run_id=workflow_run.id,
        proposal_type="create_new_page",
        target_title="Test proposal",
        summary="Test summary",
        outline="Test outline",
        suggested_schema="Article",
        status="needs_review",
    )
    db_session.add(proposal)
    db_session.commit()
    db_session.refresh(proposal)
    return proposal


def test_proposal_status_can_be_updated(db_session):
    proposal = create_proposal(db_session)

    response = client.patch(
        f"/proposals/{proposal.id}/status",
        json={"status": "approved"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == proposal.id
    assert data["status"] == "approved"


def test_proposal_status_filter_rejects_invalid_status(db_session):
    response = client.get("/proposals", params={"status": "published"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid proposal status"
