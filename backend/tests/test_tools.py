from app.engine.tools import ToolRegistry

def test_math_calculator():
    res = ToolRegistry.execute_tool("math_calculator", "(100 * 4) + 25")
    assert res["status"] == "success"
    assert res["result"] == 425

def test_search_mock():
    res = ToolRegistry.execute_tool("search_mock", "distributed consensus raft")
    assert res["status"] == "success"
    assert len(res["hits"]) >= 1

def test_code_linter_vulnerability_catch():
    vulnerable_code = "eval(user_input); password = 'super_secret_value';"
    res = ToolRegistry.execute_tool("code_linter", vulnerable_code)
    assert res["status"] == "success"
    assert res["issues_count"] >= 2
    assert any("eval()" in issue for issue in res["findings"])

def test_schema_validator():
    valid_json = '{"name": "AgentFlow", "version": "1.0"}'
    res = ToolRegistry.execute_tool("schema_validator", valid_json)
    assert res["status"] == "success"
    assert res["valid"] is True
