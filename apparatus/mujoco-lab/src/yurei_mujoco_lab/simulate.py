from __future__ import annotations

import mujoco
import numpy as np

from .arena import ARENA_XML, arena_digest

Waypoint = tuple[float, float]

POLICIES: dict[str, list[Waypoint]] = {
    "explore": [(-5, 5), (5, 5), (5, -5), (-5, -5), (0, 0)],
    "acquire": [(-4, 4), (-4, -4), (4, -4), (0, 0)],
    "construct": [(4, -4), (4, 4), (-4, 4), (4, 4)],
    "recover": [(3, 0), (-3, -3), (0, 0), (4, 4)],
}

# The fixtures encode distinct movement strategies as well as destinations.
# This keeps transition calibration grounded in observable motion instead of
# requiring absolute map coordinates to distinguish otherwise identical loops.
POLICY_DYNAMICS = {
    "explore": {"gain": 3.0, "damping": 1.2, "limit": 5.0},
    "acquire": {"gain": 1.25, "damping": 1.8, "limit": 2.5},
    "construct": {"gain": 5.0, "damping": 0.8, "limit": 8.0},
    "recover": {"gain": 2.4, "damping": 2.6, "limit": 6.0},
}


def simulate_sequence(phases: list[str], *, seconds_per_phase: float = 12.0,
                      sample_hz: int = 20) -> dict:
    if not phases or any(name not in POLICIES for name in phases) or seconds_per_phase <= 0 or sample_hz <= 0:
        raise ValueError("invalid simulation request")
    total_seconds = seconds_per_phase * len(phases)
    model = mujoco.MjModel.from_xml_string(ARENA_XML)
    data = mujoco.MjData(model)
    active_name = phases[0]
    waypoint = 0
    disturbed = False
    rows = []
    next_sample = 0.0
    while data.time < total_seconds:
        phase_index = min(int(data.time / seconds_per_phase), len(phases) - 1)
        name = phases[phase_index]
        phase_elapsed = data.time - phase_index * seconds_per_phase
        if name != active_name:
            active_name = name; waypoint = 0; disturbed = False
        waypoints = POLICIES[name]
        position = data.qpos[:2].copy()
        target = np.asarray(waypoints[waypoint])
        delta = target - position
        if np.linalg.norm(delta) < 0.55:
            waypoint = min(waypoint + 1, len(waypoints) - 1)
            target = np.asarray(waypoints[waypoint]); delta = target - position
        if name == "recover" and not disturbed and phase_elapsed >= 4.0:
            data.qpos[:2] = np.array([-4.5, 1.0]); data.qvel[:2] = 0; disturbed = True
        dynamics = POLICY_DYNAMICS[name]
        control = np.clip(
            dynamics["gain"] * delta - dynamics["damping"] * data.qvel[:2],
            -dynamics["limit"], dynamics["limit"],
        )
        data.ctrl[:] = control
        mujoco.mj_step(model, data)
        if data.time + 1e-9 >= next_sample:
            rows.append({"t": round(float(data.time), 4), "x": float(data.qpos[0]),
                         "y": float(data.qpos[1]), "z": 0.35,
                         "vx": float(data.qvel[0]), "vy": float(data.qvel[1]),
                         "control_x": float(data.ctrl[0]), "control_y": float(data.ctrl[1]),
                         "waypoint": waypoint, "contacts": int(data.ncon), "phase": name,
                         "phase_index": phase_index, "phase_elapsed": round(float(phase_elapsed), 4)})
            next_sample += 1 / sample_hz
    return {"format": "yurei-mujoco-lab.replay", "version": 1,
            "policy": phases[0] if len(phases) == 1 else "transition-sequence",
            "phases": phases, "mujoco_version": mujoco.__version__, "arena_digest": arena_digest(),
            "seconds": total_seconds, "sample_hz": sample_hz, "samples": rows}


def simulate_policy(name: str, *, seconds: float = 20.0, sample_hz: int = 20) -> dict:
    if name not in POLICIES or seconds <= 0 or sample_hz <= 0:
        raise ValueError("invalid simulation request")
    return simulate_sequence([name], seconds_per_phase=seconds, sample_hz=sample_hz)
