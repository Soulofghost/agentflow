import json
import re
import ast
from typing import Dict, Any

class ToolExecutionError(Exception):
    pass

class ToolRegistry:
    @staticmethod
    def execute_tool(tool_name: str, payload: str) -> Dict[str, Any]:
        if tool_name == "none" or not tool_name:
            return {"status": "skipped", "message": "No tool assigned to this agent"}

        if tool_name == "math_calculator":
            return ToolRegistry._eval_math(payload)
        elif tool_name == "search_mock":
            return ToolRegistry._search_knowledge(payload)
        elif tool_name == "schema_validator":
            return ToolRegistry._validate_schema(payload)
        elif tool_name == "code_linter":
            return ToolRegistry._lint_code(payload)
        else:
            raise ToolExecutionError(f"Unknown tool: '{tool_name}'")

    @staticmethod
    def _eval_math(expression: str) -> Dict[str, Any]:
        # Clean expression to safe arithmetic characters only
        clean = re.sub(r'[^0-9\+\-\*\/\(\)\.\s]', '', expression)
        if not clean.strip():
            return {"status": "error", "error": "Invalid arithmetic expression"}
        try:
            # Safe evaluation using Python AST
            tree = ast.parse(clean, mode='eval')
            for node in ast.walk(tree):
                if not isinstance(node, (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.operator, ast.unaryop)):
                    raise ValueError("Disallowed expression syntax")
            res = eval(compile(tree, filename='', mode='eval'))
            return {"status": "success", "tool": "math_calculator", "expression": clean, "result": res}
        except Exception as e:
            return {"status": "error", "error": f"Evaluation error: {str(e)}"}

    @staticmethod
    def _search_knowledge(query: str) -> Dict[str, Any]:
        simulated_corpus = {
            "distributed": "Paxos and Raft consensus achieve quorum through majority voting (N/2 + 1) with leader election timeouts.",
            "security": "SQL injection and Cross-Site Scripting (XSS) remain prevalent OWASP vulnerabilities mitigated via parameterized queries and CSP headers.",
            "concurrency": "Python AsyncIO utilizes an event loop running cooperative coroutines within a single operating system thread.",
            "crypto": "Zero-Knowledge SNARKs provide succinct proof verification without revealing underlying witness assignments."
        }
        hits = []
        for key, text in simulated_corpus.items():
            if key in query.lower() or any(w in text.lower() for w in query.lower().split() if len(w) > 3):
                hits.append({"topic": key, "summary": text})
        return {
            "status": "success",
            "tool": "search_mock",
            "query": query,
            "hits": hits or [{"topic": "general", "summary": f"Telemetry verified for inquiry: '{query}'"}]
        }

    @staticmethod
    def _validate_schema(data_str: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(data_str) if isinstance(data_str, str) else data_str
            is_valid = isinstance(parsed, dict) and len(parsed.keys()) > 0
            return {
                "status": "success",
                "tool": "schema_validator",
                "valid": is_valid,
                "fields_detected": list(parsed.keys()) if isinstance(parsed, dict) else []
            }
        except Exception as e:
            return {"status": "error", "valid": False, "error": str(e)}

    @staticmethod
    def _lint_code(code: str) -> Dict[str, Any]:
        issues = []
        if "eval(" in code:
            issues.append("CRITICAL: Unsafe dynamic eval() detected")
        if "password" in code.lower() and "=" in code:
            issues.append("WARNING: Possible hardcoded credential detected")
        if "SELECT * FROM" in code and "WHERE" not in code:
            issues.append("INFO: Full table scan query detected without WHERE clause")

        return {
            "status": "success",
            "tool": "code_linter",
            "issues_count": len(issues),
            "findings": issues if issues else ["No high-severity syntax or credential risks detected in snippet."]
        }
