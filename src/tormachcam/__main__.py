"""CLI entry point: ``python -m tormachcam input.stl -o output.ngc``"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config.defaults import build_default_tool_library
from .config.machine_profiles import TormachModel, get_profile
from .core.job import Job
from .core.model import load_stl
from .core.operation import Operation, StrategyType
from .core.stock import Stock
from .core.units import Units
from .gcode.pathpilot import PathPilotPostProcessor, PostProcessorConfig
from .gcode.validate import validate_toolpaths


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tormachcam",
        description="Generate PathPilot G-code (.ngc) from STL files.",
    )
    p.add_argument("--gui", action="store_true",
                    help="Launch the desktop GUI (default when no input file given)")
    p.add_argument("input", type=Path, nargs="?", default=None,
                   help="Input STL file (omit to launch GUI)")
    p.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output .ngc file (default: <input>.ngc)",
    )
    p.add_argument(
        "--machine", choices=["440", "770", "1100"], default="770",
        help="Tormach model (default: 770)",
    )
    p.add_argument(
        "--units", choices=["inch", "mm"], default="inch",
        help="Working units (default: inch)",
    )

    # Tool parameters
    p.add_argument("--tool-number", type=int, default=1,
                    help="Tool number (default: 1)")
    p.add_argument("--tool-diameter", type=float, default=None,
                    help="Tool diameter (overrides default library)")

    # Roughing parameters
    p.add_argument("--step-down", type=float, default=0.05,
                    help="Axial depth of cut (default: 0.05)")
    p.add_argument("--step-over", type=float, default=0.4,
                    help="Step-over as fraction of tool diameter (default: 0.4)")
    p.add_argument("--finish-allowance", type=float, default=0.005,
                    help="Material left for finishing (default: 0.005)")

    # Feeds and speeds
    p.add_argument("--rpm", type=int, default=None,
                    help="Spindle RPM (default: tool library default)")
    p.add_argument("--feed-xy", type=float, default=None,
                    help="XY feed rate (default: tool library default)")
    p.add_argument("--feed-z", type=float, default=None,
                    help="Plunge feed rate (default: tool library default)")

    # Clearance heights
    p.add_argument("--safe-z", type=float, default=0.1,
                    help="Safe Z for inter-cut rapids (default: 0.1)")
    p.add_argument("--rapid-z", type=float, default=0.5,
                    help="Rapid Z for inter-operation moves (default: 0.5)")

    # Stock (optional)
    p.add_argument("--stock-margin", type=float, default=0.1,
                    help="Margin around model for auto stock (default: 0.1)")

    # Operation mode
    p.add_argument("--strategy", choices=["roughing", "finishing", "both"],
                    default="both", help="Toolpath strategy (default: both)")

    # Validation
    p.add_argument("--skip-validate", action="store_true",
                    help="Skip machine-limit validation")

    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    # Launch GUI when --gui flag is set or no input file provided
    if args.gui or args.input is None:
        from .app import launch_gui
        return launch_gui()

    # Resolve output path
    output: Path = args.output or args.input.with_suffix(".ngc")

    # Map machine choice
    machine_map = {"440": TormachModel.PCNC_440, "770": TormachModel.PCNC_770,
                   "1100": TormachModel.PCNC_1100}
    machine = machine_map[args.machine]
    profile = get_profile(machine)

    # Units
    units = Units.INCH if args.units == "inch" else Units.MM

    # Load model
    print(f"Loading {args.input} ...")
    model = load_stl(args.input)
    if model.was_repaired:
        print("  Warning: mesh was repaired (may not be watertight)")
    print(f"  Bounds: {model.bounds[0]} → {model.bounds[1]}")
    print(f"  Extents: {model.extents}")

    # Position model: XY origin at lower-left of stock, Z=0 at stock top
    model.translate_to_origin()
    z_range = model.z_max - model.z_min
    # Shift so Z=0 is top of stock, and add XY margin offset so stock starts at (0,0)
    margin = args.stock_margin
    model.mesh.apply_translation([margin, margin, -z_range])

    # Tool setup
    lib = build_default_tool_library()
    tool = lib.get(args.tool_number)
    if tool is None:
        print(f"Error: tool T{args.tool_number} not found in default library",
              file=sys.stderr)
        return 1
    if args.tool_diameter is not None:
        tool.diameter = args.tool_diameter

    rpm = args.rpm or tool.default_rpm
    feed_xy = args.feed_xy or tool.default_feed_xy
    feed_z = args.feed_z or tool.default_feed_z

    print(f"Tool: T{tool.number} {tool.name} (dia={tool.diameter})")
    print(f"  RPM: {rpm}  Feed XY: {feed_xy}  Feed Z: {feed_z}")

    # Stock (auto from model bounds + margin; origin at 0,0)
    stock = Stock(
        x_size=model.extents[0] + 2 * margin,
        y_size=model.extents[1] + 2 * margin,
        z_size=z_range,
        x_origin=0.0,
        y_origin=0.0,
        z_top=0.0,
    )
    print(f"Stock: {stock.x_size:.3f} x {stock.y_size:.3f} x {stock.z_size:.3f}")

    # Build job
    job = Job(name=args.input.stem, units=units, model=model, stock=stock)

    if args.strategy in ("roughing", "both"):
        job.operations.append(Operation(
            name="Roughing",
            strategy=StrategyType.ROUGHING,
            tool=tool,
            z_top=0.0,
            z_bottom=stock.z_bottom,
            step_down=args.step_down,
            step_over_fraction=args.step_over,
            rpm=rpm,
            feed_xy=feed_xy,
            feed_z=feed_z,
            safe_z=args.safe_z,
            rapid_z=args.rapid_z,
            finish_allowance=args.finish_allowance,
        ))

    if args.strategy in ("finishing", "both"):
        job.operations.append(Operation(
            name="Finishing",
            strategy=StrategyType.FINISHING,
            tool=tool,
            z_top=0.0,
            z_bottom=stock.z_bottom,
            step_down=args.step_down,
            rpm=rpm,
            feed_xy=feed_xy,
            feed_z=feed_z,
            safe_z=args.safe_z,
            rapid_z=args.rapid_z,
        ))

    # Compute toolpaths
    print("Computing toolpaths ...")
    toolpaths = job.compute_toolpaths()
    total_points = sum(tp.total_points for tp in toolpaths)
    print(f"  Generated {len(toolpaths)} operations, {total_points} total points")

    # Validate
    if not args.skip_validate:
        result = validate_toolpaths(toolpaths, profile.envelope, rpm=rpm)
        if result.has_errors:
            print("VALIDATION ERRORS:", file=sys.stderr)
            for issue in result.issues:
                if issue.severity == "error":
                    print(f"  ERROR: {issue.message}", file=sys.stderr)
            return 1
        if result.has_warnings:
            for issue in result.issues:
                if issue.severity == "warning":
                    print(f"  Warning: {issue.message}")

    # Generate G-code
    pp_config = PostProcessorConfig(
        units=units,
        tool_number=tool.number,
        rpm=rpm,
        safe_z=args.safe_z,
        rapid_z=args.rapid_z,
    )
    post = PathPilotPostProcessor(pp_config)
    post.generate(toolpaths, output)
    print(f"Wrote {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
