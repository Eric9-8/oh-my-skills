#!/usr/bin/env python3
"""Normalize aiSim radar exports into object-level RadarService inputs."""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIDENCE = 100.0
DEFAULT_RCS = 0.0
DEFAULT_SNR = 0.0
CONFIDENCE_SCALE = 98.0

OBJECT_TYPE_MAP = {
    "Car": 1,
    "Truck": 2,
    "Bus": 2,
    "Van": 1,
    "Motorcycle": 3,
    "Pedestrian": 4,
}


@dataclass(frozen=True)
class RadarObject:
    dx: float
    dy: float
    vx: float
    vy: float
    ax: float
    ay: float
    object_id: int
    object_type: int
    confidence: float
    motion_pattern: int
    length: float
    width: float
    rcs: float
    snr: float

    def to_payload_dict(self) -> dict[str, float | int]:
        data = asdict(self)
        data.update(
            {
                "cluster_dist_long": self.dx,
                "cluster_dist_lat": self.dy,
                "cluster_vrel_long": self.vx,
                "cluster_vrel_lat": self.vy,
                "cluster_rcs": self.rcs,
                "cluster_dyn_prop": self.motion_pattern,
                "cluster_id": self.object_id,
            }
        )
        return data


def load_aisim_frame(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an aiSim radar JSON object")
    return data


def frame_to_objects(frame: dict[str, Any], use_targets: bool) -> list[RadarObject]:
    objects = [object_from_capture(item) for item in frame.get("captured_objects", [])]
    if use_targets and frame.get("targets"):
        return merge_targets(objects, frame["targets"])
    return sorted(objects, key=lambda item: math.hypot(item.dx, item.dy))


def object_from_capture(item: dict[str, Any]) -> RadarObject:
    center = item.get("center_distance", [0.0, 0.0, 0.0])
    velocity = item.get("relative_velocity", [0.0, 0.0, 0.0])
    acceleration = item.get("relative_acceleration", [0.0, 0.0, 0.0])
    class_name = str(item.get("object_class", ""))
    return RadarObject(
        dx=float(center[0]),
        dy=float(center[1]),
        vx=float(velocity[0]),
        vy=float(velocity[1]),
        ax=float(acceleration[0]),
        ay=float(acceleration[1]),
        object_id=int(item.get("id", 0)) & 0xFF,
        object_type=OBJECT_TYPE_MAP.get(class_name, int(item.get("type", 0))),
        confidence=float(item.get("probability_of_existence", 1.0)) * CONFIDENCE_SCALE,
        motion_pattern=int(item.get("dynamic_property", 0)),
        length=float(item.get("length", 0.0)),
        width=float(item.get("width", 0.0)),
        rcs=float(item.get("rcs", DEFAULT_RCS)),
        snr=DEFAULT_SNR,
    )


def merge_targets(objects: list[RadarObject], targets: list[dict[str, Any]]) -> list[RadarObject]:
    grouped = {index: [] for index in range(len(objects))}
    for target in targets:
        nearest = nearest_object_index(objects, target)
        if nearest is not None:
            grouped[nearest].append(target)
    merged = [merge_object_targets(obj, grouped[index]) for index, obj in enumerate(objects)]
    return sorted(merged, key=lambda item: math.hypot(item.dx, item.dy))


def nearest_object_index(objects: list[RadarObject], target: dict[str, Any]) -> int | None:
    position = target.get("position")
    if not position or len(position) < 2 or not objects:
        return None
    tx = float(position[0])
    ty = float(position[1])
    best_index = min(
        range(len(objects)),
        key=lambda index: math.hypot(objects[index].dx - tx, objects[index].dy - ty),
    )
    best = objects[best_index]
    gate = max(4.0, 0.75 * max(best.length, best.width, 1.0))
    if math.hypot(best.dx - tx, best.dy - ty) > gate:
        return None
    return best_index


def merge_object_targets(obj: RadarObject, targets: list[dict[str, Any]]) -> RadarObject:
    if not targets:
        return obj
    strongest = max(targets, key=lambda item: float(item.get("snr", 0.0)))
    velocity = strongest.get("velocity_mps", [obj.vx, obj.vy, 0.0])
    snr = float(strongest.get("snr", obj.snr))
    rcs = float(strongest.get("rcs", obj.rcs))
    score = min(96.774, max(0.0, rcs, snr))
    return RadarObject(
        dx=obj.dx,
        dy=obj.dy,
        vx=float(velocity[0]),
        vy=float(velocity[1]),
        ax=obj.ax,
        ay=obj.ay,
        object_id=obj.object_id,
        object_type=obj.object_type,
        confidence=obj.confidence,
        motion_pattern=obj.motion_pattern,
        length=obj.length,
        width=obj.width,
        rcs=score,
        snr=snr,
    )
