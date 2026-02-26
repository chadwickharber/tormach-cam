"""Low-level G-code line formatting helpers."""

from __future__ import annotations

from typing import Optional


def fmt(value: float, decimals: int = 4) -> str:
    """Format a float for G-code, stripping trailing zeros."""
    return f"{value:.{decimals}f}".rstrip("0").rstrip(".")


def rapid(
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None,
) -> str:
    """G0 rapid traverse."""
    parts = ["G0"]
    if x is not None:
        parts.append(f"X{fmt(x)}")
    if y is not None:
        parts.append(f"Y{fmt(y)}")
    if z is not None:
        parts.append(f"Z{fmt(z)}")
    return " ".join(parts)


def linear(
    x: Optional[float] = None,
    y: Optional[float] = None,
    z: Optional[float] = None,
    f: Optional[float] = None,
) -> str:
    """G1 linear interpolation."""
    parts = ["G1"]
    if x is not None:
        parts.append(f"X{fmt(x)}")
    if y is not None:
        parts.append(f"Y{fmt(y)}")
    if z is not None:
        parts.append(f"Z{fmt(z)}")
    if f is not None:
        parts.append(f"F{fmt(f, 1)}")
    return " ".join(parts)


def comment(text: str) -> str:
    """Wrap *text* in PathPilot-style parenthetical comment."""
    # PathPilot uses () for comments, strip existing parens
    cleaned = text.replace("(", "").replace(")", "")
    return f"({cleaned})"
