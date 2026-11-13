import uuid
import json
from fastapi import APIRouter, HTTPException
from typing import List
from app.database import get_db_connection
from app.schemas import WorkflowCreate, WorkflowResponse
from app.engine.dag import DagEngine, CyclicDependencyError, InvalidNodeDependencyError

router = APIRouter(prefix="/workflows", tags=["Workflows"])

@router.get("", response_model=List[WorkflowResponse])
def list_workflows():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflows ORDER BY created_at ASC")
        rows = cursor.fetchall()
        return [
            WorkflowResponse(
                id=r["id"],
                name=r["name"],
                description=r["description"],
                dag=json.loads(r["dag_json"]),
                created_at=r["created_at"]
            ) for r in rows
        ]

@router.post("", response_model=WorkflowResponse, status_code=201)
def create_workflow(wf: WorkflowCreate):
    # Validate DAG before saving
    node_dicts = [n.model_dump() for n in wf.dag.nodes]
    try:
        DagEngine.validate_and_sort(node_dicts)
    except (CyclicDependencyError, InvalidNodeDependencyError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    wf_id = "wf_" + str(uuid.uuid4())[:8]
    dag_json = json.dumps(wf.dag.model_dump())

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO workflows (id, name, description, dag_json)
            VALUES (?, ?, ?, ?)
        """, (wf_id, wf.name, wf.description, dag_json))
        conn.commit()

        cursor.execute("SELECT * FROM workflows WHERE id = ?", (wf_id,))
        saved = cursor.fetchone()
        return WorkflowResponse(
            id=saved["id"],
            name=saved["name"],
            description=saved["description"],
            dag=json.loads(saved["dag_json"]),
            created_at=saved["created_at"]
        )

@router.get("/{wf_id}", response_model=WorkflowResponse)
def get_workflow(wf_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflows WHERE id = ?", (wf_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return WorkflowResponse(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            dag=json.loads(row["dag_json"]),
            created_at=row["created_at"]
        )
