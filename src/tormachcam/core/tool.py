"""Cutting tool definitions and tool library with JSON persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


class ToolType(Enum):
    FLAT_ENDMILL = "flat_endmill"
    BALL_ENDMILL = "ball_endmill"
    DRILL = "drill"
    FACE_MILL = "face_mill"


@dataclass
class Tool:
    """A cutting tool definition.

    All dimensions are stored in the job's native units (inch or mm).
    """
    number: int
    name: str
    tool_type: ToolType
    diameter: float
    flute_count: int = 2
    flute_length: float = 0.0
    overall_length: float = 0.0
    default_rpm: int = 0
    default_feed_xy: float = 0.0
    default_feed_z: float = 0.0

    @property
    def radius(self) -> float:
        return self.diameter / 2.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tool_type"] = self.tool_type.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Tool:
        d = dict(d)
        d["tool_type"] = ToolType(d["tool_type"])
        return cls(**d)


class ToolLibrary:
    """Persistent tool library backed by a JSON file."""

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = Path.home() / ".tormachcam" / "tools.json"
        self._path = path
        self._tools: dict[int, Tool] = {}
        if self._path.exists():
            self.load()

    def add(self, tool: Tool) -> None:
        self._tools[tool.number] = tool

    def remove(self, number: int) -> None:
        self._tools.pop(number, None)

    def get(self, number: int) -> Optional[Tool]:
        return self._tools.get(number)

    def list_tools(self) -> list[Tool]:
        return sorted(self._tools.values(), key=lambda t: t.number)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = [t.to_dict() for t in self.list_tools()]
        self._path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        data = json.loads(self._path.read_text())
        self._tools = {}
        for d in data:
            tool = Tool.from_dict(d)
            self._tools[tool.number] = tool
