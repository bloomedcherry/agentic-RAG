"""LLM answer generation with the M4 template path as fallback."""

from __future__ import annotations

import re
from typing import Any

from enterprise_agent.agent.state import AgentState
from enterprise_agent.llm.base import BaseLLMClient, LLMRequest, llm_call_summary
from enterprise_agent.llm.prompts import ANSWER_PROMPT_VERSION, build_answer_messages


class AnswerGenerator:
    def __init__(self, llm_client: BaseLLMClient | None = None) -> None:
        self.llm_client = llm_client

    def generate(self, state: AgentState) -> tuple[str, dict[str, Any]]:
        if self.llm_client is None or state.get("errors"):
            return generate_template_answer(state), {}

        response = self.llm_client.complete(
            LLMRequest(
                messages=build_answer_messages(
                    query=state.get("query", ""),
                    task_type=state.get("task_type", ""),
                    context=state.get("context", ""),
                ),
                temperature=0.0,
                max_tokens=1024,
            )
        )
        llm_calls = list(state.get("llm_calls") or [])
        llm_calls.append(
            llm_call_summary(
                response,
                purpose="answer_generator",
                prompt_version=ANSWER_PROMPT_VERSION,
            )
        )
        metadata = {
            "llm_calls": llm_calls,
            "prompt_version": ANSWER_PROMPT_VERSION,
        }
        if response.status == "success" and response.content.strip():
            metadata["llm_fallback_used"] = bool(state.get("llm_fallback_used", False))
            return _strip_reasoning_block(response.content), metadata

        metadata["llm_fallback_used"] = True
        return generate_template_answer(state), metadata


def _strip_reasoning_block(content: str) -> str:
    return re.sub(
        r"^\s*<think>.*?</think>\s*",
        "",
        content,
        count=1,
        flags=re.DOTALL,
    ).strip()


def generate_template_answer(state: AgentState) -> str:
    outputs = state.get("tool_outputs") or {}
    if state.get("task_type") in {"project_analysis", "data_analysis"}:
        report = outputs.get("generate_report", {}).get("markdown")
        return report or "证据不足：未生成分析草稿。"

    if state.get("task_type") == "workflow_check":
        workflow = outputs.get("workflow_check") or {}
        documents = outputs.get("search_kb", {}).get("documents") or []
        source_line = _source_line(documents)
        if workflow.get("approval_required") is True:
            return f"需要审批，审批人：{workflow.get('approver') or '未配置'}。\n{source_line}"
        if workflow.get("approval_required") is False:
            return f"不需要审批。\n{source_line}"
        return f"证据不足：无法匹配流程规则。\n{source_line}"

    documents = outputs.get("search_kb", {}).get("documents") or []
    if not documents:
        return "证据不足：知识库未检索到可用来源。"
    return _generate_policy_answer(state.get("query", ""), documents)


def _source_line(documents: list[dict]) -> str:
    if not documents:
        return "来源：知识库未命中。"
    sources = "，".join(dict.fromkeys(str(doc.get("source")) for doc in documents[:5]))
    return f"来源：{sources}"


def _generate_policy_answer(query: str, documents: list[dict]) -> str:
    evidence_text = "\n".join(str(doc.get("content", "")) for doc in documents[:5])
    if "差旅报销" in query:
        materials = [
            item
            for item in ["行程单", "发票", "审批单", "费用明细", "付款账户", "例外材料"]
            if item in evidence_text
        ]
        if materials:
            return (
                "结论：差旅报销通常需要提交以下材料：\n"
                + "\n".join(f"- {item}" for item in materials)
                + f"\n{_source_line(documents)}"
            )

    summaries = []
    for doc in documents[:3]:
        first_section = str(doc.get("content", "")).split("##", maxsplit=1)[0]
        cleaned = " ".join(first_section.split())
        if cleaned:
            summaries.append(f"- {cleaned[:120]}")
    if not summaries:
        return f"证据不足：知识库命中来源但内容不可用于回答。\n{_source_line(documents)}"
    return "结论：根据知识库检索结果，相关要求如下：\n" + "\n".join(summaries) + f"\n{_source_line(documents)}"
