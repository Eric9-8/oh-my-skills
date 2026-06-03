#!/usr/bin/env python3
"""Generate an aiSim 6-radar sensor configuration."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

RADAR_SPECS: dict[str, dict[str, float | str]] = {
    "radar_front": {"h_fov": 120.0, "v_fov": 28.0, "range_min": 0.25, "range_max": 260.0, "model": "FVR30"},
    "radar_front_left": {"h_fov": 150.0, "v_fov": 20.0, "range_min": 0.2, "range_max": 160.0, "model": "CVR30/FVR30 side"},
    "radar_front_right": {"h_fov": 150.0, "v_fov": 20.0, "range_min": 0.2, "range_max": 160.0, "model": "CVR30/FVR30 side"},
    "radar_rear": {"h_fov": 120.0, "v_fov": 28.0, "range_min": 0.25, "range_max": 180.0, "model": "FVR30 rear"},
    "radar_rear_left": {"h_fov": 150.0, "v_fov": 20.0, "range_min": 0.2, "range_max": 160.0, "model": "CVR30/FVR30 side"},
    "radar_rear_right": {"h_fov": 150.0, "v_fov": 20.0, "range_min": 0.2, "range_max": 160.0, "model": "CVR30/FVR30 side"},
}

DEFAULT_TEMPLATE = Path("/opt/aiMotive/aisim_gui-5.11.0/data/calibrations/radar_sensor_advanced.json")


def require_number(value: Any, label: str) -> float:
    if not isinstance(value, int | float):
        raise ValueError(f"{label} must be a number, got {value!r}")
    return float(value)


def load_extrinsics(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    missing = sorted(set(RADAR_SPECS) - set(data))
    if missing:
        raise ValueError(f"{path} missing radar extrinsics: {missing}")
    return data


def normalize_pose(name: str, entry: dict[str, Any]) -> dict[str, Any]:
    position = entry.get("position")
    rotation = entry.get("rotation")
    if not isinstance(position, dict) or not isinstance(rotation, dict):
        raise ValueError(f"{name} requires position and rotation mappings")
    return {
        "position": [
            require_number(position.get("x"), f"{name}.position.x"),
            require_number(position.get("y"), f"{name}.position.y"),
            require_number(position.get("z"), f"{name}.position.z"),
        ],
        "rotation": {
            "yaw": require_number(rotation.get("yaw"), f"{name}.rotation.yaw"),
            "pitch": require_number(rotation.get("pitch"), f"{name}.rotation.pitch"),
            "roll": require_number(rotation.get("roll"), f"{name}.rotation.roll"),
        },
        "source": str(entry.get("source", "unknown")),
    }


def load_template(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    sensors = data.get("sensors")
    if not isinstance(sensors, dict) or not sensors:
        raise ValueError(f"{path} must contain a non-empty sensors mapping")
    template = next(iter(sensors.values()))
    if not isinstance(template, dict):
        raise ValueError(f"{path} first sensor must be a JSON object")
    return template


def make_sensor(name: str, pose: dict[str, Any], update_hz: float, template: dict[str, Any]) -> dict[str, Any]:
    spec = RADAR_SPECS[name]
    sensor = copy.deepcopy(template)
    update_interval_us = int(round(1_000_000.0 / update_hz))
    sensor["type"] = "radar"
    sensor["update_intervals"] = [update_interval_us]
    sensor["mounting"] = {"position": pose["position"], "rotation": pose["rotation"]}
    sensor["need_target_list"] = True
    sensor["visualize"] = False
    sensor["frustum_config"] = {
        "horizontal_fov_deg": spec["h_fov"],
        "vertical_fov_deg": spec["v_fov"],
        "depth_range": [spec["range_min"], spec["range_max"]],
        "viewport_resolution_scale": 10,
    }
    return sensor


def build_config(extrinsics_path: Path, update_hz: float, template_path: Path) -> dict[str, Any]:
    extrinsics = load_extrinsics(extrinsics_path)
    template = load_template(template_path)
    sensors = {}
    for name in RADAR_SPECS:
        pose = normalize_pose(name, extrinsics[name])
        sensors[name] = make_sensor(name, pose, update_hz, template)
    return {"sensors": sensors}


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extrinsics",
        type=Path,
        default=Path("aisim_radar_replay/data/radar_extrinsics.yaml"),
        help="Radar extrinsics YAML",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("aisim_radar_replay/data/aisim_radar_config_advanced.json"),
        help="Output aiSim JSON",
    )
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="aiSim radar template JSON")
    parser.add_argument("--update-hz", type=float, default=20.0, help="Radar update rate")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    if args.update_hz <= 0:
        raise ValueError("--update-hz must be positive")
    config = build_config(args.extrinsics, args.update_hz, args.template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {args.output}")
    for name, sensor in config["sensors"].items():
        mounting = sensor["mounting"]
        frustum = sensor["frustum_config"]
        print(f"{name}: pos={mounting['position']} rot={mounting['rotation']} frustum={frustum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
