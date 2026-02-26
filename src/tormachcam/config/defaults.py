"""Default feeds, speeds, and tool definitions.

These are conservative starting points; users should adjust to their
specific tooling and material.
"""

from ..core.tool import Tool, ToolType, ToolLibrary


def build_default_tool_library() -> ToolLibrary:
    """Return a ToolLibrary pre-populated with common Tormach starter tools."""
    lib = ToolLibrary.__new__(ToolLibrary)
    lib._path = None   # in-memory only
    lib._tools = {}

    tools = [
        Tool(
            number=1,
            name="1/2\" Flat Endmill 2-flute",
            tool_type=ToolType.FLAT_ENDMILL,
            diameter=0.5,
            flute_count=2,
            flute_length=1.0,
            overall_length=3.0,
            default_rpm=3000,
            default_feed_xy=20.0,
            default_feed_z=5.0,
        ),
        Tool(
            number=2,
            name="1/4\" Flat Endmill 2-flute",
            tool_type=ToolType.FLAT_ENDMILL,
            diameter=0.25,
            flute_count=2,
            flute_length=0.75,
            overall_length=2.5,
            default_rpm=5000,
            default_feed_xy=15.0,
            default_feed_z=4.0,
        ),
        Tool(
            number=3,
            name="1/4\" Ball Endmill 2-flute",
            tool_type=ToolType.BALL_ENDMILL,
            diameter=0.25,
            flute_count=2,
            flute_length=0.75,
            overall_length=2.5,
            default_rpm=5000,
            default_feed_xy=12.0,
            default_feed_z=3.0,
        ),
        Tool(
            number=4,
            name="1/8\" Flat Endmill 2-flute",
            tool_type=ToolType.FLAT_ENDMILL,
            diameter=0.125,
            flute_count=2,
            flute_length=0.5,
            overall_length=2.0,
            default_rpm=8000,
            default_feed_xy=10.0,
            default_feed_z=3.0,
        ),
    ]

    for t in tools:
        lib.add(t)

    return lib
