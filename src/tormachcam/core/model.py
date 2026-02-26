"""STL mesh loading via trimesh with basic repair."""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh


@dataclass
class MeshModel:
    """Loaded and (optionally) repaired mesh model."""

    mesh: trimesh.Trimesh
    source_path: Path
    was_repaired: bool = False

    @property
    def bounds(self) -> np.ndarray:
        """Return (2, 3) array: [[xmin,ymin,zmin],[xmax,ymax,zmax]]."""
        return self.mesh.bounds

    @property
    def extents(self) -> np.ndarray:
        return self.mesh.extents

    @property
    def z_min(self) -> float:
        return float(self.mesh.bounds[0, 2])

    @property
    def z_max(self) -> float:
        return float(self.mesh.bounds[1, 2])

    def translate_to_origin(self) -> None:
        """Translate mesh so its bounding-box minimum is at the origin."""
        self.mesh.apply_translation(-self.mesh.bounds[0])


def load_stl(path: Path, repair: bool = True) -> MeshModel:
    """Load an STL (or any trimesh-supported mesh) from *path*.

    Parameters
    ----------
    path:
        Path to the mesh file.
    repair:
        When True, attempt to fill holes and fix winding on non-watertight
        meshes and emit a warning if the mesh required repair.

    Raises
    ------
    FileNotFoundError:
        If *path* does not exist.
    ValueError:
        If the file cannot be parsed as a mesh.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Mesh file not found: {path}")

    mesh = trimesh.load(str(path), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Could not load a single mesh from {path}")

    was_repaired = False
    if repair and not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        trimesh.repair.fix_winding(mesh)
        trimesh.repair.fix_normals(mesh)
        if not mesh.is_watertight:
            warnings.warn(
                f"Mesh '{path.name}' is not watertight after repair. "
                "Slicing results may be incomplete.",
                UserWarning,
                stacklevel=2,
            )
        was_repaired = True

    return MeshModel(mesh=mesh, source_path=path, was_repaired=was_repaired)
