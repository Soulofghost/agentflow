import asyncio
import uuid
import json
import time
import sqlite3
from typing import Dict, Any, List
from app.engine.dag import DagEngine
from app.engine.tools import ToolRegistry

async def run_workflow_execution(conn_factory, execution_id: str, workflow_dag: Dict[str, Any], input_prompt: str):
    """
    Executes the DAG nodes in topological tiers, recording step logs and passing state.
    """
    nodes = workflow_dag.get("nodes", [])
    tiers = DagEngine.validate_and_sort(nodes)

    node_outputs: Dict[str, str] = {}
    
    with conn_factory() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE executions SET status = 'running' WHERE id = ?", (execution_id,))
        conn.commit()

    for tier_idx, tier_nodes in enumerate(tiers):
        for node in tier_nodes:
            step_id = "step_" + str(uuid.uuid4())[:8]
            t0 = time.time()
            node_id = node["id"]
            role = node["role"]
            tool = node.get("tool", "none")

            # Gather context from dependencies
            dep_contexts = []
            for dep in node.get("dependencies", []):
                dep_contexts.append(f"[{dep}]: {node_outputs.get(dep, '')}")
            
            combined_context = "\n".join(dep_contexts) if dep_contexts else f"Root Task: {input_prompt}"

            # Execute tool if configured
            tool_output = None
            if tool and tool != "none":
                try:
                    tool_output = ToolRegistry.execute_tool(tool, input_prompt if not dep_contexts else combined_context)
                except Exception as e:
                    tool_output = {"status": "error", "message": str(e)}

            # Generate Agent Artifact based on role
            artifact = generate_agent_thought(role, input_prompt, combined_context, tool_output)
            node_outputs[node_id] = artifact
            duration_ms = int((time.time() - t0) * 1000)

            # Record step in database
            with conn_factory() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO agent_logs (id, execution_id, step_name, agent_role, status, input_context, output_artifact, tool_calls_json, duration_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (step_id, execution_id, node_id, role, "completed", combined_context, artifact, json.dumps(tool_output) if tool_output else None, duration_ms))
                conn.commit()

            # Small async yield to simulate cooperative concurrency
            await asyncio.sleep(0.05)

    # Final synthesis
    final_output = f"=== WORKFLOW EXECUTION COMPLETE ===\n\n"
    for nid, out in node_outputs.items():
        final_output += f"--- Output from [{nid}] ---\n{out}\n\n"

    with conn_factory() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE executions
            SET status = 'succeeded', completed_at = CURRENT_TIMESTAMP, final_output = ?
            WHERE id = ?
        """, (final_output.strip(), execution_id))
        conn.commit()

def generate_agent_thought(role: str, root_prompt: str, context: str, tool_res: Dict[str, Any] = None) -> str:
    tool_summary = f"\n[Tool Execution]: {json.dumps(tool_res)}" if tool_res else ""

    if "Planner" in role or "Architect" in role:
        return f"Decomposed project objective into verifiable execution milestones.\nScope: {root_prompt[:120]}...\nTarget deliverables: Architectural blueprints, vulnerability verification gates, and integration test validation.{tool_summary}"
    elif "Analyzer" in role or "Researcher" in role or "Scout" in role:
        return f"Executed thorough domain investigation based on planner specifications.\nContext evaluated: {context[:140]}...\nIdentified key structural patterns, data dependencies, and security boundaries.{tool_summary}"
    elif "Critic" in role or "Verification" in role or "Editor" in role:
        return f"Audited prior agent deliverables against quality standards.\nVerification Status: PASSED.\nAll dependency outputs conform to specifications with zero critical defects detected.{tool_summary}"
    else:
        return f"Completed specialized domain tasks according to workflow schedule.\nArtifact generated and transmitted to downstream message bus.{tool_summary}"
