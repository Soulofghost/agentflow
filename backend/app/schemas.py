from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class DagNode(BaseModel):
    id: str
    role: str
    tool: Optional[str] = "none"
    dependencies: List[str] = []

class DagDefinition(BaseModel):
    nodes: List[DagNode]

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1)
    dag: DagDefinition

class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    dag: Dict[str, Any]
    created_at: str

class ExecutionCreate(BaseModel):
    workflow_id: str
    input_prompt: str = Field(..., min_length=1)

class AgentLogItem(BaseModel):
    id: str
    execution_id: str
    step_name: str
    agent_role: str
    status: str
    input_context: Optional[str] = None
    output_artifact: Optional[str] = None
    tool_calls_json: Optional[str] = None
    duration_ms: Optional[int] = 0
    timestamp: str

class ExecutionDetailResponse(BaseModel):
    id: str
    workflow_id: str
    status: str
    input_prompt: str
    final_output: Optional[str] = None
    started_at: str
    completed_at: Optional[str] = None
    steps: List[AgentLogItem]
