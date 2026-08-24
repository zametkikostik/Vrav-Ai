from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List


_TOOL_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,63}$")


@dataclass(slots=True)
class ToolSpec:
    name: str
    description: str
    fn: Callable[[str], str]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, tool: ToolSpec) -> None:
        if not _TOOL_NAME_RE.fullmatch(tool.name):
            raise ValueError("invalid_tool_name")
        self._tools[tool.name] = tool

    def has(self, name: str) -> bool:
        return name in self._tools

    def call(self, name: str, arg: str) -> str:
        return self._tools[name].fn(arg)

    def list_tools(self) -> List[dict[str, str]]:
        return [{"name": t.name, "description": t.description} for t in self._tools.values()]


    def register_lambda(self, name: str, description: str, fn: Callable[[str], str]) -> None:
        self.register(ToolSpec(name=name, description=description, fn=fn))


    def unregister(self, name: str) -> bool:
        if name not in self._tools:
            return False
        del self._tools[name]
        return True
