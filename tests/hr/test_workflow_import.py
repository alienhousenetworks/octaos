import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, User, Tenant
from app.services.hr.workflow.import_service import WorkflowImportService
from app.models.hr import HRWorkflowDefinition, TenantDocumentTemplate, TemplateVersion


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def test_tenant_id():
    return str(uuid.uuid4())


@pytest.fixture
def test_user_id():
    return str(uuid.uuid4())


def test_get_all_folders_returns_standard_folders(db, test_tenant_id):
    folders = WorkflowImportService.get_all_folders(db, test_tenant_id)
    assert "/" in folders
    assert "/Engineering" in folders
    assert "/Sales" in folders


def test_clone_workflow_remaps_node_ids_and_preserves_draft_status(db, test_tenant_id, test_user_id):
    # 1. Create source workflow in /Engineering
    source_wf = HRWorkflowDefinition(
        tenant_id=test_tenant_id,
        name="Senior Software Engineer Onboarding",
        folder_path="/Engineering",
        graph_schema={
            "nodes": [
                {"id": "node_1", "name": "Intake", "type": "start", "config": {}},
                {"id": "node_2", "name": "Offer Pack", "type": "generate_document", "config": {}}
            ],
            "edges": [
                {"id": "edge_1", "source": "node_1", "target": "node_2"}
            ]
        },
        version=1,
        is_active=True,
    )
    db.add(source_wf)
    db.commit()
    db.refresh(source_wf)

    # 2. Clone to /Sales
    cloned_wf = WorkflowImportService.clone_workflow(
        db=db,
        tenant_id=test_tenant_id,
        user_id=test_user_id,
        source_definition_id=source_wf.id,
        target_folder_path="/Sales",
        target_name="Account Executive Onboarding",
        clone_templates=False,
    )

    assert cloned_wf.id != source_wf.id
    assert cloned_wf.name == "Account Executive Onboarding"
    assert cloned_wf.folder_path == "/Sales"
    assert cloned_wf.is_active is False  # Must be draft
    assert cloned_wf.version == 1

    # Check nodes remapped
    cloned_nodes = cloned_wf.graph_schema["nodes"]
    assert len(cloned_nodes) == 2
    assert cloned_nodes[0]["id"] != "node_1"
    assert cloned_nodes[1]["id"] != "node_2"

    # Check edge source and target remapped
    cloned_edges = cloned_wf.graph_schema["edges"]
    assert len(cloned_edges) == 1
    assert cloned_edges[0]["source"] == cloned_nodes[0]["id"]
    assert cloned_edges[0]["target"] == cloned_nodes[1]["id"]
