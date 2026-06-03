"""Tool registry for looking up runtime tools by stable name."""

from __future__ import annotations

from enterprise_agent.tools.base import BaseTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("tool name must not be empty")
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"tool not registered: {name}") from exc

    def list_metadata(self) -> list[dict]:
        return [tool.metadata() for tool in self._tools.values()]
