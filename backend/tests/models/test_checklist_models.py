"""
Tests for WAF checklist models.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.checklist import (
    Checklist,
    ChecklistItem,
    ChecklistItemEvaluation,
    ChecklistStatus,
    ChecklistTemplate,
    EvaluationStatus,
    SeverityLevel,
)
from app.models.project import Base, Project


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_checklist_template_creation(db_session):
    """Test creating a checklist template."""
    template = ChecklistTemplate(
        slug="waf-2026-v1",
        title="Azure WAF 2026",
        description="Test description",
        version="1.0.0",
        source="microsoft-learn",
        source_url="https://learn.microsoft.com/waf",
        source_version="2026-01-15",
        content={"categories": [], "items": []},
    )
    db_session.add(template)
    db_session.commit()

    saved = db_session.query(ChecklistTemplate).filter_by(slug="waf-2026-v1").first()
    assert saved is not None
    assert saved.title == "Azure WAF 2026"
    assert isinstance(saved.id, uuid.UUID)


def test_checklist_creation_with_project(db_session):
    """Test creating a checklist linked to a project."""
    # 1. Create project
    project = Project(
        id=str(uuid.uuid4()),
        name="Test Project"
    )
    db_session.add(project)
    db_session.commit()

    # 2. Create checklist
    checklist = Checklist(
        project_id=project.id,
        title="WAF Review",
        status=ChecklistStatus.OPEN
    )
    db_session.add(checklist)
    db_session.commit()

    saved = db_session.query(Checklist).filter_by(project_id=project.id).first()
    assert saved is not None
    assert saved.title == "WAF Review"
    assert saved.project.name == "Test Project"


def test_checklist_item_deterministic_id():
    """Test that deterministic IDs are stable."""
    project_id = str(uuid.uuid4())
    template_slug = "waf-v1"
    item_id = "item-001"
    namespace = uuid.uuid4()

    id1 = ChecklistItem.compute_deterministic_id(project_id, template_slug, item_id, namespace)
    id2 = ChecklistItem.compute_deterministic_id(project_id, template_slug, item_id, namespace)

    assert id1 == id2

    # Change project_id, should change result
    id3 = ChecklistItem.compute_deterministic_id(str(uuid.uuid4()), template_slug, item_id, namespace)
    assert id1 != id3


def test_checklist_item_creation(db_session):
    """Test creating checklist items."""
    project = Project(id=str(uuid.uuid4()), name="Test")
    db_session.add(project)
    db_session.commit()

    checklist = Checklist(project_id=project.id, title="Test")
    db_session.add(checklist)
    db_session.commit()

    item_id = ChecklistItem.compute_deterministic_id(
        project.id, "waf", "item-1", uuid.uuid4()
    )

    item = ChecklistItem(
        id=item_id,
        checklist_id=checklist.id,
        template_item_id="item-1",
        title="Secure Storage",
        severity=SeverityLevel.HIGH,
        pillar="Security"
    )
    db_session.add(item)
    db_session.commit()

    saved = db_session.query(ChecklistItem).filter_by(id=item_id).first()
    assert saved is not None
    assert saved.title == "Secure Storage"
    assert saved.checklist.title == "Test"


def test_checklist_item_evaluation(db_session):
    """Test creating an evaluation for an item."""
    project = Project(id=str(uuid.uuid4()), name="Test")
    db_session.add(project)

    checklist = Checklist(project_id=project.id, title="Test")
    db_session.add(checklist)
    db_session.commit()

    item = ChecklistItem(
        id=uuid.uuid4(),
        checklist_id=checklist.id,
        template_item_id="1",
        title="T",
        severity=SeverityLevel.LOW
    )
    db_session.add(item)
    db_session.commit()

    evaluation = ChecklistItemEvaluation(
        item_id=item.id,
        project_id=project.id,
        evaluator="test-agent",
        status=EvaluationStatus.FIXED,
        source_type="agent-validation"
    )
    db_session.add(evaluation)
    db_session.commit()

    assert len(item.evaluations) == 1
    assert item.evaluations[0].status == EvaluationStatus.FIXED


def test_cascade_delete(db_session):
    """Test that deleting a checklist deletes its items."""
    project = Project(id=str(uuid.uuid4()), name="Test")
    db_session.add(project)

    checklist = Checklist(project_id=project.id, title="Test")
    db_session.add(checklist)
    db_session.commit()

    item = ChecklistItem(
        id=uuid.uuid4(),
        checklist_id=checklist.id,
        template_item_id="1",
        title="T",
        severity=SeverityLevel.LOW
    )
    db_session.add(item)
    db_session.commit()

    # Delete checklist
    db_session.delete(checklist)
    db_session.commit()

    # Item should be gone
    assert db_session.query(ChecklistItem).count() == 0
