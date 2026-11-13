import sqlite3
import json
from contextlib import contextmanager
from typing import Generator
from app.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            dag_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS executions (
            id TEXT PRIMARY KEY,
            workflow_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'succeeded', 'failed')),
            input_prompt TEXT NOT NULL,
            final_output TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (workflow_id) REFERENCES workflows (id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_logs (
            id TEXT PRIMARY KEY,
            execution_id TEXT NOT NULL,
            step_name TEXT NOT NULL,
            agent_role TEXT NOT NULL,
            status TEXT NOT NULL,
            input_context TEXT,
            output_artifact TEXT,
            tool_calls_json TEXT,
            duration_ms INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (execution_id) REFERENCES executions (id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    # Seed default production templates if empty
    cursor.execute("SELECT count(*) as count FROM workflows")
    if cursor.fetchone()[0] == 0:
        seed_workflows(cursor)
        conn.commit()

    conn.close()

def seed_workflows(cursor: sqlite3.Cursor):
    templates = [
        {
            "id": "wf-code-audit",
            "name": "Code Review & Security Audit DAG",
            "description": "Multi-agent pipeline that analyzes pull request diffs, checks AST syntax, executes vulnerability linting, and generates an executive review.",
            "dag": {
                "nodes": [
                    {"id": "planner", "role": "Architect Planner", "tool": "none", "dependencies": []},
                    {"id": "ast_checker", "role": "Code Analyzer", "tool": "code_linter", "dependencies": ["planner"]},
                    {"id": "sec_audit", "role": "Security Researcher", "tool": "search_mock", "dependencies": ["planner"]},
                    {"id": "critic", "role": "Verification Critic", "tool": "schema_validator", "dependencies": ["ast_checker", "sec_audit"]}
                ]
            }
        },
        {
            "id": "wf-research-fact",
            "name": "Fact-Verified Research Synthesis",
            "description": "Coordinated agents gather technical literature, compute metrics, and cross-examine claims to produce a verified briefing.",
            "dag": {
                "nodes": [
                    {"id": "literature_agent", "role": "Research Scout", "tool": "search_mock", "dependencies": []},
                    {"id": "quant_agent", "role": "Quantitative Analyst", "tool": "math_calculator", "dependencies": ["literature_agent"]},
                    {"id": "editor_agent", "role": "Chief Editor", "tool": "none", "dependencies": ["quant_agent"]}
                ]
            }
        }
    ]

    for t in templates:
        cursor.execute("""
            INSERT INTO workflows (id, name, description, dag_json)
            VALUES (?, ?, ?, ?)
        """, (t["id"], t["name"], t["description"], json.dumps(t["dag"])))

@contextmanager
def get_db_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
