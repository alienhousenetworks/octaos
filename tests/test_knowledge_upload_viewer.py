import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = create_access_token("05b64b1b-9e56-4b60-9a94-403714bb7c58", tenant_id="45c055fd-1e60-478d-b789-62a2c8d87967")
    return {"Authorization": f"Bearer {token}"}


def test_knowledge_upload_file_chunks_workflow(client, auth_headers):
    # 1. Prepare sample text document
    doc_content = (
        "--- Page 1 ---\n"
        "# Executive Summary\n"
        "OctaOS is an autonomous enterprise execution platform.\n\n"
        "--- Page 2 ---\n"
        "# System Architecture\n"
        "Hybrid RAG with pgvector dense embeddings and BM25 sparse retrieval."
    )
    file_bytes = io.BytesIO(doc_content.encode("utf-8"))

    # 2. Upload document
    files = {"file": ("test_architecture.md", file_bytes, "text/markdown")}
    data = {"department": "Engineering", "doc_type": "Architecture"}
    res = client.post("/api/v1/commands/knowledge/upload", headers=auth_headers, files=files, data=data)
    assert res.status_code == 200, res.text
    res_data = res.json()
    assert "document_id" in res_data
    doc_id = res_data["document_id"]
    assert res_data["chunks_indexed"] >= 1

    try:
        # 3. Retrieve original file via file endpoint
        file_res = client.get(f"/api/v1/commands/knowledge/{doc_id}/file", headers=auth_headers)
        assert file_res.status_code == 200
        assert len(file_res.content) > 0

        # 4. Retrieve chunks
        chunks_res = client.get(f"/api/v1/commands/knowledge/{doc_id}/chunks", headers=auth_headers)
        assert chunks_res.status_code == 200
        chunks = chunks_res.json()
        assert len(chunks) >= 1
        first_chunk = chunks[0]
        assert "content" in first_chunk
        assert "section_title" in first_chunk
        assert "page_start" in first_chunk
        assert "token_estimate" in first_chunk

        # 5. Verify list endpoint contains metadata_json
        list_res = client.get("/api/v1/commands/knowledge", headers=auth_headers)
        assert list_res.status_code == 200
        docs = list_res.json()
        matching = [d for d in docs if d["id"] == doc_id]
        assert len(matching) == 1
        assert "metadata_json" in matching[0]
        assert matching[0]["metadata_json"].get("file_name") == "test_architecture.md"

    finally:
        # 6. Clean up
        del_res = client.delete(f"/api/v1/commands/knowledge/{doc_id}", headers=auth_headers)
        assert del_res.status_code == 200
