"""G-code validation and sanity checks.

Checks generated toolpath / G-code against machine travel limits and
other safety rules before cutting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..core.toolpath.base import Toolpath, ToolpathPoint


@dataclass
class MachineEnvelope:
    """Axis travel limits for a Tormach mill."""

    x_min: float = 0.0
    x_max: float = 18.0
    y_min: float = 0.0
    y_max: float = 9.5
    z_min: float = -16.25
    z_max: float = 0.0
    max_rpm: int = 10000
    min_rpm: int = 175
    max_feed: float = 135.0  # IPM


@dataclass
class ValidationIssue:
    """A single validation problem found in the toolpath."""

    severity: str  # "error" or "warning"
    message: str
    point: Optional[ToolpathPoint] = None


@dataclass
class ValidationResult:
    """Result of validating one or more toolpaths."""

    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)

    @property
    def is_ok(self) -> bool:
        return len(self.issues) == 0


def validate_toolpaths(
    toolpaths: list[Toolpath],
    envelope: MachineEnvelope,
    rpm: int = 3000,
) -> ValidationResult:
    """Check *toolpaths* against *envelope* limits.

    Checks performed:
    - All XYZ coordinates within machine travel
    - Feed rates within machine maximum
    - RPM within machine range
    - Toolpath is non-empty
    """
    result = ValidationResult()

    # RPM check
    if rpm < envelope.min_rpm:
        result.issues.append(ValidationIssue(
            "error",
            f"RPM {rpm} below machine minimum ({envelope.min_rpm})",
        ))
    if rpm > envelope.max_rpm:
        result.issues.append(ValidationIssue(
            "error",
            f"RPM {rpm} above machine maximum ({envelope.max_rpm})",
        ))

    all_empty = True
    for tp in toolpaths:
        if tp.is_empty:
            continue
        all_empty = False

        for seg in tp.segments:
            for pt in seg.points:
                # Travel limit checks
                if pt.x < envelope.x_min or pt.x > envelope.x_max:
                    result.issues.append(ValidationIssue(
                        "error",
                        f"X={pt.x:.4f} outside travel "
                        f"[{envelope.x_min}, {envelope.x_max}]",
                        pt,
                    ))
                if pt.y < envelope.y_min or pt.y > envelope.y_max:
                    result.issues.append(ValidationIssue(
                        "error",
                        f"Y={pt.y:.4f} outside travel "
                        f"[{envelope.y_min}, {envelope.y_max}]",
                        pt,
                    ))
                if pt.z < envelope.z_min or pt.z > envelope.z_max:
                    result.issues.append(ValidationIssue(
                        "error",
                        f"Z={pt.z:.4f} outside travel "
                        f"[{envelope.z_min}, {envelope.z_max}]",
                        pt,
                    ))

                # Feed rate check
                if pt.feed_rate is not None and pt.feed_rate > envelope.max_feed:
                    result.issues.append(ValidationIssue(
                        "warning",
                        f"Feed {pt.feed_rate:.1f} exceeds machine max "
                        f"({envelope.max_feed:.1f})",
                        pt,
                    ))

    if all_empty:
        result.issues.append(ValidationIssue(
            "warning",
            "All toolpaths are empty — no G-code will be generated",
        ))

    return result
