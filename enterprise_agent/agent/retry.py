"""Rule-based retry and fallback decisions."""

from __future__ import annotations

ACTION_BY_ISSUE = {
    "missing_citation": "retry_with_citation",
    "retrieval_empty": "fallback_insufficient_evidence",
    "sql_error": "fallback_without_data_claim",
    "permission_denied": "refusal",
    "format_error": "retry_with_format",
    "permission_violation": "refusal",
}


def decide_next_action(verifier_result: dict) -> str:
    for issue in verifier_result.get("issues", []):
        action = ACTION_BY_ISSUE.get(issue.get("type"))
        if action:
            return action
    return "none"
