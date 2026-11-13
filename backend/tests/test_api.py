import time
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_list_workflows():
    res = client.get("/api/v1/workflows")
    assert res.status_code == 200
    wfs = res.json()
    assert len(wfs) >= 2
    assert any(w["id"] == "wf-code-audit" for w in wfs)

def test_create_custom_workflow_and_execute():
    # 1. Create Workflow
    payload = {
        "name": "Quick Synthetic Check",
        "description": "Simple 2-node planner and verifier",
        "dag": {
            "nodes": [
                {"id": "planner", "role": "Strategic Planner", "tool": "none", "dependencies": []},
                {"id": "verifier", "role": "Fact Checker", "tool": "search_mock", "dependencies": ["planner"]}
            ]
        }
    }
    create_res = client.post("/api/v1/workflows", json=payload)
    assert create_res.status_code == 201
    wf_id = create_res.json()["id"]

    # 2. Launch Execution
    exec_res = client.post("/api/v1/executions", json={
        "workflow_id": wf_id,
        "input_prompt": "Audit the security boundaries of microservices architecture."
    })
    assert exec_res.status_code == 202
    exec_id = exec_res.json()["execution_id"]

    # 3. Poll Execution Status
    time.sleep(0.3)
    detail_res = client.get(f"/api/v1/executions/{exec_id}")
    assert detail_res.status_code == 200
    data = detail_res.json()
    assert data["workflow_id"] == wf_id
    assert len(data["steps"]) >= 1
