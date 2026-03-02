"""Mesh loading via trimesh with optional repair and display decimation."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh

log = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".stl", ".obj", ".ply", ".off", ".glb", ".gltf", ".3mf",
}

# Max face count sent to the VTK viewport (full mesh kept for CAM)
DISPLAY_MAX_FACES = 50_000


@dataclass
class MeshModel:
    """Loaded mesh with a lightweight decimated copy for the viewport."""

    mesh: trimesh.Trimesh
    source_path: Path
    was_repaired: bool = False
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
        self._display_verts = None
        self._display_faces = None

    def _build_display_mesh(self) -> None:
        """Build a face-subsampled copy for the viewport.

        Uses uniform index subsampling — no C extensions, never crashes.
        simplify_quadric_decimation is intentionally avoided because it
        segfaults on non-manifold / real-world meshes.
        """
        m = self.mesh
        nf = len(m.faces)
        if nf > DISPLAY_MAX_FACES:
            indices = np.round(
                np.linspace(0, nf - 1, DISPLAY_MAX_FACES)
            ).astype(int)
            m = trimesh.Trimesh(
                vertices=m.vertices,
                faces=m.faces[indices],
                process=False,
            )
            log.debug(
                "Display mesh subsampled %d → %d faces", nf, DISPLAY_MAX_FACES
            )

        self._display_verts = np.ascontiguousarray(m.vertices, dtype=np.float64)
        self._display_faces = np.ascontiguousarray(m.faces)


def load_mesh(path: Path, repair: bool = False) -> MeshModel:
    """Load a mesh from *path*.

    repair=False by default — trimesh's hole-filling can hang or crash on
    real-world STL files.  Pass repair=True only for small, well-behaved meshes.
    """
    path = Path(path)
    log.info("Loading mesh: %s", path)

    if not path.exists():
        raise FileNotFoundError(f"Mesh file not found: {path}")

    mesh = trimesh.load(str(path), force="mesh")
    log.info(
        "trimesh.load done: %d verts, %d faces", len(mesh.vertices), len(mesh.faces)
    )

    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"Could not load a single mesh from {path.name}")

    was_repaired = False
    if repair and not mesh.is_watertight:
        log.info("Attempting mesh repair…")
        try:
            trimesh.repair.fix_winding(mesh)
            trimesh.repair.fix_normals(mesh)
            # fill_holes is intentionally skipped — it can hang indefinitely
        except Exception as exc:
            log.warning("Mesh repair failed: %s", exc)
        was_repaired = True
        if not mesh.is_watertight:
            warnings.warn(
                f"'{path.name}' is not watertight after repair. "
                "Slicing results may be incomplete.",
                UserWarning,
                stacklevel=2,
            )

    model = MeshModel(mesh=mesh, source_path=path, was_repaired=was_repaired)
    log.info("Building display mesh…")
    model._build_display_mesh()
    log.info(
        "Load complete: display mesh has %d faces", len(model._display_faces)
    )
    return model


# Backward-compat alias
load_stl = load_mesh
