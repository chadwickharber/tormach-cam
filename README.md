# TormachCAM

A Python desktop CAM application that loads STL files and generates [PathPilot](https://www.tormach.com/pathpilot)-compatible G-code (`.ngc`) for Tormach 3-axis mills (PCNC 440 / 770 / 1100).

![Python](https://img.shields.io/badge/python-3.9+-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Tests](https://img.shields.io/badge/tests-50%20passing-brightgreen)

---

## Features

- **STL loading** via trimesh with automatic mesh repair for non-watertight files
- **2.5D roughing** — raster zigzag pocket clearing at each Z level
- **2.5D finishing** — contour-parallel passes tracing part profile
- **PathPilot post-processor** — correct G30 tool changes, G64 path blending, M8/M9 coolant
- **Machine profiles** for PCNC 440, 770, and 1100 with travel-limit validation
- **Desktop GUI** — PyQt6 with 3D viewport (pyvistaqt/VTK), docked panels, and G-code preview
- **CLI** for headless/scripted use

---

## Installation

**Requirements:** macOS (Apple Silicon), Python 3.9+

```bash
git clone https://github.com/chadwickharber/tormach-cam
cd tormach-cam
pip install -e ".[dev]"
```

---

## Usage

### GUI

```bash
python -m tormachcam
```

Or double-click **TormachCAM.app** on your Desktop.

### CLI

```bash
# Roughing + finishing with defaults
python -m tormachcam part.stl -o part.ngc

# Full options
python -m tormachcam part.stl -o part.ngc \
  --machine 770 \
  --tool-number 1 \
  --tool-diameter 0.5 \
  --step-down 0.05 \
  --step-over 0.4 \
  --finish-allowance 0.005 \
  --rpm 3000 \
  --feed-xy 20 \
  --feed-z 5 \
  --strategy both
```

#### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--machine` | `770` | Tormach model: `440`, `770`, or `1100` |
| `--units` | `inch` | `inch` or `mm` |
| `--tool-number` | `1` | Tool number from library |
| `--tool-diameter` | — | Override tool diameter |
| `--step-down` | `0.05` | Axial depth per pass |
| `--step-over` | `0.4` | Radial step as fraction of diameter |
| `--finish-allowance` | `0.005` | Stock left for finishing |
| `--rpm` | tool default | Spindle RPM |
| `--feed-xy` | tool default | XY feed rate |
| `--feed-z` | tool default | Plunge feed rate |
| `--safe-z` | `0.1` | Z clearance between cuts |
| `--rapid-z` | `0.5` | Z clearance between operations |
| `--stock-margin` | `0.1` | Auto-stock margin around model |
| `--strategy` | `both` | `roughing`, `finishing`, or `both` |
| `--skip-validate` | — | Skip machine travel limit checks |

---

## G-code format

Generated `.ngc` files are compatible with PathPilot (LinuxCNC). Key conventions:

- **Preamble:** `G17 G20 G40 G49 G54 G80 G90 G94` + `G64 P0.002`
- **Tool change:** `M5` → `M9` → `G30` → `T# M6` → `G43 H#` → `S#### M3` → `M8` → `G4 P2.0`
- **Z convention:** Z=0 is the **top of stock** (Tormach standard)
- **Postamble:** `M5` → `M9` → `G30` → `M30` → `%`

> Always verify output in [CAMotics](https://camotics.org) or [NCViewer](https://ncviewer.com) and run PathPilot simulation before cutting.

---

## Project structure

```
src/tormachcam/
├── core/
│   ├── model.py          # STL loading + repair
│   ├── slicer.py         # Z-plane slicing → Shapely polygons
│   ├── stock.py          # Stock definition
│   ├── tool.py           # Tool definitions + JSON library
│   ├── operation.py      # Operation parameters
│   ├── job.py            # Job orchestrator
│   ├── units.py          # INCH/MM
│   └── toolpath/
│       ├── base.py       # ToolpathPoint, ToolpathSegment, Toolpath
│       ├── roughing.py   # Raster zigzag pocket clearing
│       ├── finishing.py  # Contour-parallel finishing
│       └── utils.py      # Geometry helpers
├── gcode/
│   ├── pathpilot.py      # PathPilot post-processor
│   ├── gcode_writer.py   # Line formatting
│   └── validate.py       # Travel limit checks
├── gui/
│   ├── main_window.py    # QMainWindow
│   ├── viewport.py       # 3D viewport (pyvistaqt)
│   ├── workers.py        # QThread background workers
│   └── panels/           # Model, tool, operation, G-code panels
└── config/
    ├── machine_profiles.py  # PCNC 440/770/1100
    ├── settings.py          # App preferences
    └── defaults.py          # Default tool library
```

---

## Machine profiles

| Model | X | Y | Z | RPM | Max feed |
|-------|---|---|---|-----|----------|
| PCNC 440 | 10" | 6.25" | 10" | 100–10,000 | 110 IPM |
| PCNC 770 | 12" | 8" | 10.25" | 175–10,000 | 110 IPM |
| PCNC 1100 | 18" | 9.5" | 16.25" | 175–10,000 | 135 IPM |

---

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=tormachcam --cov-report=term-missing
```

50 tests covering:
- Z-level slicer with cube and cylinder geometries
- Roughing zigzag and finishing contour toolpath assertions
- PathPilot G-code output format verification
- Machine travel limit and RPM validation

---

## Dependencies

| Library | Role |
|---------|------|
| [trimesh](https://trimesh.org) | STL loading, Z-plane slicing |
| [shapely](https://shapely.readthedocs.io) | 2D polygon offsets and boolean ops |
| [numpy](https://numpy.org) | Numerical arrays |
| [scipy](https://scipy.org) | Spatial queries |
| [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) | Desktop GUI |
| [pyvistaqt](https://qtdocs.pyvista.org) | Embeddable 3D viewport |

---

## Roadmap

- [ ] Phase 3: Full GUI (viewport toolpath overlay, job save/load)
- [ ] Phase 4: Tool animation, feeds/speeds advisor, packaged `.app`
- [ ] Adaptive clearing (trochoidal milling)
- [ ] 3D finishing (parallel planes with ball endmill)
- [ ] Direct PathPilot file transfer over network
