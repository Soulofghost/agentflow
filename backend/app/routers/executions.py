import uuid
import json
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
from app.database import get_db_connection
from app.schemas import ExecutionCreate, ExecutionDetailResponse, AgentLogItem
from app.engine.runner import run_workflow_execution

router = APIRouter(prefix="/executions", tags=["Executions"])

@router.post("", status_code=202)
async def launch_execution(payload: ExecutionCreate, background_tasks: BackgroundTasks):
    execution_id = "exec_" + str(uuid.uuid4())[:8]

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM workflows WHERE id = ?", (payload.workflow_id,))
        wf = cursor.fetchone()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        dag = json.loads(wf["dag_json"])

        cursor.execute("""
            INSERT INTO executions (id, workflow_id, status, input_prompt)
            VALUES (?, ?, 'pending', ?)
        """, (execution_id, payload.workflow_id, payload.input_prompt))
        conn.commit()

    # Launch background async DAG execution
    background_tasks.add_task(
        run_workflow_execution,
        get_db_connection,
        execution_id,
        dag,
        payload.input_prompt
    )

    return {
        "execution_id": execution_id,
        "workflow_id": payload.workflow_id,
        "status": "pending",
        "message": "Agent DAG execution scheduled"
    }

@router.get("/{exec_id}", response_model=ExecutionDetailResponse)
def get_execution_detail(exec_id: str):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM executions WHERE id = ?", (exec_id,))
        exec_row = cursor.fetchone()
        if not exec_row:
            raise HTTPException(status_code=404, detail="Execution not found")

        cursor.execute("""
            SELECT * FROM agent_logs WHERE execution_id = ? ORDER BY timestamp ASC
        """, (exec_id,))
        log_rows = cursor.fetchall()

        steps = [
            AgentLogItem(
                id=r["id"],
                execution_id=r["execution_id"],
                step_name=r["step_name"],
                agent_role=r["agent_role"],
                status=r["status"],
                input_context=r["input_context"],
                output_artifact=r["output_artifact"],
                tool_calls_json=r["tool_calls_json"],
                duration_ms=r["duration_ms"],
                timestamp=r["timestamp"]
            ) for r in log_rows
        ]

        return ExecutionDetailResponse(
            id=exec_row["id"],
            workflow_id=exec_row["workflow_id"],
            status=exec_row["status"],
            input_prompt=exec_row["input_prompt"],
            final_output=exec_row["final_output"],
            started_at=exec_row["started_at"],
            completed_at=exec_row["completed_at"],
            steps=steps
        )

@router.get("")
def list_executions():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.id, e.workflow_id, e.status, e.input_prompt, e.started_at, e.completed_at,
                   w.name as workflow_name
            FROM executions e
            JOIN workflows w ON e.workflow_id = w.id
            ORDER BY e.started_at DESC
            LIMIT 30
        """)
        return cursor.fetchall()
