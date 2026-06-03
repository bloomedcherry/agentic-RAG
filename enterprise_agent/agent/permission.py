"""Role-based tool permission checks for the runtime."""

from __future__ import annotations

from typing import Any

ROLES = {"employee", "manager", "admin"}

TOOL_PERMISSIONS = {
    "search_kb": {"employee", "manager", "admin"},
    "generate_report": {"employee", "manager", "admin"},
    "workflow_check": {"employee", "manager", "admin"},
    "parse_doc": {"employee", "manager", "admin"},
    "query_sql": {"manager", "admin"},
}


def check_permission(user_role: str, tool: Any) -> dict:
    tool_name = getattr(tool, "name", "")
    allowed_roles = TOOL_PERMISSIONS.get(tool_name, set())
    if user_role in ROLES and user_role in allowed_roles:
        return {"allowed": True, "error_type": None, "message": ""}
    return {
        "allowed": False,
        "error_type": "permission_denied",
        "message": f"当前角色无权调用 {tool_name}",
    }
