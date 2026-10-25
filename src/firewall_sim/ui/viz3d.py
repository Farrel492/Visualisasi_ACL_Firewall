"""3D packet trace and replay frame builder.

ATURAN ARSITEKTUR:
- Murni Python (tanpa dependensi Streamlit atau Plotly).
- Menghasilkan tuple frame deterministik dari SimulationResult yang immutable.
- Untuk DROP, frame terakhir berhenti di router dan tidak ada langkah setelahnya (T10).
- Ketinggian Z ditentukan secara deterministik berdasarkan tipe perangkat.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, List, Optional, Tuple

from firewall_sim.core.models import Decision, DeviceType, ProjectState, SimulationResult


@dataclass(frozen=True)
class Point3D:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ReplayFrame:
    frame_index: int
    device_id: str
    position: Point3D
    action: Optional[str]
    description: str
    path_so_far: Tuple[Point3D, ...]


def calculate_3d_positions(state: ProjectState) -> Dict[str, Point3D]:
    """Menghitung koordinat 3D deterministik untuk setiap perangkat.

    Z-level:
    - ROUTER: z = 1.8 (pusat & core firewall)
    - SWITCH: z = 0.9 (layer distribusi L2)
    - PC / SERVER: z = 0.0 (access / endpoint)
    """
    positions: Dict[str, Point3D] = {}
    routers = [d for d in state.devices if d.type == DeviceType.ROUTER]
    other_devices = [d for d in state.devices if d.type != DeviceType.ROUTER]

    if routers:
        positions[routers[0].id] = Point3D(0.0, 0.0, 1.8)

    n = len(other_devices)
    if n > 0:
        radius = 3.0
        for idx, dev in enumerate(other_devices):
            angle = (2.0 * math.pi * idx) / n
            x = round(radius * math.cos(angle), 3)
            y = round(radius * math.sin(angle), 3)

            if dev.type == DeviceType.SWITCH:
                z = 0.9
            else:
                z = 0.0

            positions[dev.id] = Point3D(x, y, z)

    return positions


def build_replay_frames(
    result: SimulationResult,
    positions: Dict[str, Point3D],
) -> Tuple[ReplayFrame, ...]:
    """Membangun urutan frame visualisasi 3D dari SimulationResult.

    Aturan:
    - Jika DROP: frame terakhir berhenti di router dan tidak ada frame setelahnya (T10).
    - Jika ACCEPT: frame berjalan berurutan hingga tiba di tujuan.
    - Jika NO_ROUTE: frame berhenti di titik putusnya jalur.
    """
    if not result.trace:
        return ()

    frames: List[ReplayFrame] = []
    accumulated_path: List[Point3D] = []

    for idx, step in enumerate(result.trace):
        pos = positions.get(step.device_id, Point3D(0.0, 0.0, 0.0))
        accumulated_path.append(pos)

        frame = ReplayFrame(
            frame_index=idx,
            device_id=step.device_id,
            position=pos,
            action=step.action,
            description=step.description,
            path_so_far=tuple(accumulated_path),
        )
        frames.append(frame)

        # Jika pada langkah ini terjadi terminal DROP, hentikan pembangunan frame
        if step.action == "DROP" or (result.decision == Decision.DROP and idx == len(result.trace) - 1):
            break

    return tuple(frames)
