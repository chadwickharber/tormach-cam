"""Mesh loading via trimesh with repair and display decimation.

Supports STL, OBJ, PLY, OFF, and other trimesh-compatible formats.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh

# Formats trimesh can load natively
SUPPORTED_EXTENSIONS = {
    ".stl", ".obj", ".ply", ".off", ".glb", ".gltf", ".3mf",
}

# Max face count for the 3D viewport (full mesh kept for CAM)
DISPLAY_MAX_FACES = 50_000


@dataclass
class MeshModel:
    """Loaded and (optionally) repaired mesh model."""

    mesh: trimesh.Trimesh
    source_path: Path
    was_repaired: bool = False
    # Lightweight copy for the viewport (may be decimated)
    _display_verts: np.ndarray = field(default=None, repr=False)
    _display_faces: np.ndarray = field(default=None, repr=False)

    @property
    def bounds(self) -> np.ndarray:
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

    @property
    def display_vertices(self) -> np.ndarray:
        if self._display_verts is None:
            self._build_display_mesh()
        return self._display_verts

    @property
    def display_faces(self) -> np.ndarray:
        if self._display_faces is None:
            self._build_display_mesh()
        return self._display_faces

    def translate_to_origin(self) -> None:
        self.mesh.apply_translation(-self.mesh.bounds[0])
        # Invalidate display cache
        self._display_verts = None
        self._display_faces = None

    def _build_display_mesh(self) -> None:
        """Create a decimated copy for viewport rendering."""
        m = self.mesh
        if len(m.faces) > DISPLAY_MAX_FACES:
            ratio = DISPLAY_MAX_FACES / len(m.faces)
            try:
                m = m.simplify_quadric_decimation(DISPLAY_MAX_FACES)
            except Exception:
                # Fallback: subsample faces
                indices = np.linspace(
                    0, len(self.mesh.faces) - 1,
                    DISPLAY_MAX_FACES, dtype=int,
                )
                m = trimesh.Trimesh(
                    vertices=self.mesh.vertices,
                    faces=self.mesh.faces[indices],
                    process=False,
                )
        self._display_verts = np.ascontiguousarray(
            m.vertices.astype(np.float64)
        )
        self._display_faces = np.ascontiguousarray(m.faces)


def load_mesh(path: Path, repair: bool = True) -> MeshModel:
    """Load a mesh from *path* (STL, OBJ, PLY, OFF, 3MF, etc.).

    Raises FileNotFoundError or ValueError on failure.
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

    model = MeshModel(mesh=mesh, source_path=path, was_repaired=was_repaired)
    # Pre-build the decimated display mesh (this runs in the worker thread)
    model._build_display_mesh()
    return model


# Keep backward compat alias
load_stl = load_mesh
