from enterprise_agent.agent.permission import check_permission
from enterprise_agent.tools.runtime_tools import QuerySqlTool, SearchKbTool


def test_employee_cannot_call_query_sql():
    result = check_permission("employee", QuerySqlTool())

    assert result == {
        "allowed": False,
        "error_type": "permission_denied",
        "message": "当前角色无权调用 query_sql",
    }


def test_manager_can_call_query_sql_and_employee_can_search_kb():
    assert check_permission("manager", QuerySqlTool())["allowed"] is True
    assert check_permission("employee", SearchKbTool())["allowed"] is True


def test_unknown_role_is_denied():
    result = check_permission("contractor", SearchKbTool())

    assert result["allowed"] is False
    assert result["error_type"] == "permission_denied"
