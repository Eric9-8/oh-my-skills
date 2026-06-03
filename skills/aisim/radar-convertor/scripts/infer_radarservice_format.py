#!/usr/bin/env python3
"""Generate the locked RadarService format spec from real probe evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

EXPECTED_TOPICS = {
    "/sensor/radar_front/obstacle_list": ("radar_front", "f_radar_data", 40),
    "/sensor/radar_front_left/obstacle_list": ("radar_front_left", "fl_radar_data", 41),
    "/sensor/radar_front_right/obstacle_list": ("radar_front_right", "fr_radar_data", 42),
    "/sensor/radar_rear/obstacle_list": ("radar_rear", "r_radar_data", 0),
    "/sensor/radar_rear_left/obstacle_list": ("radar_rear_left", "rl_radar_data", 43),
    "/sensor/radar_rear_right/obstacle_list": ("radar_rear_right", "rr_radar_data", 44),
}


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    topics = data.get("topics")
    if not isinstance(topics, dict):
        raise ValueError(f"{path} missing topics report")
    return data


def validate_probe(report: dict[str, Any]) -> None:
    missing = sorted(set(EXPECTED_TOPICS) - set(report["topics"]))
    if missing:
        raise ValueError(f"Probe report missing radar topics: {missing}")
    for topic, (radar, frame_id, radar_id) in EXPECTED_TOPICS.items():
        info = report["topics"][topic]
        require(info["payload_sizes"] == [2012], f"{topic} payload size is not fixed 2012")
        require(info["cdr_headers"] == ["00010000"], f"{topic} CDR header mismatch")
        require(info["frame_ids"] == [frame_id], f"{topic} frame_id mismatch")
        require(info["slot_capacity"] == [40], f"{topic} slot capacity mismatch")
        require(radar_id in info["radar_ids"], f"{radar} radar_id {radar_id} not observed")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def build_spec() -> dict[str, Any]:
    return {
        "version": 1,
        "payload_size": 2012,
        "endianness": "little",
        "cdr_header_hex": "00010000",
        "targets_offset": 72,
        "target_stride": 48,
        "target_count": 40,
        "frame_id_offset": 24,
        "fixed_float_48": 3.1796875,
        "radar_ids": {radar: radar_id for _, (radar, _, radar_id) in EXPECTED_TOPICS.items()},
        "frame_ids": {radar: frame_id for _, (radar, frame_id, _) in EXPECTED_TOPICS.items()},
        "fields": [
            field("cluster_id", 0, "uint8", "object raw byte 0; real payload stores extra flag bytes in 0..3"),
            field("confidence", 4, "float32", "DBC RdrObjConf / FLR confidence-like value"),
            field("valid_flag", 8, "uint8", "real state byte"),
            field("update_flag", 9, "uint8", "real state byte"),
            field("cluster_dyn_prop", 10, "uint8", "DBC motion pattern-like state byte"),
            field("x_std", 12, "float32", "DBC x position std"),
            field("y_std", 16, "float32", "DBC y position std"),
            field("vx_std", 20, "float32", "DBC x velocity std"),
            field("ax_or_vx_abs", 24, "float32", "real payload auxiliary velocity/acceleration field"),
            field("cluster_rcs", 28, "float32", "RadarService obstacle probability / RCS-compatible score"),
            field("cluster_dist_long", 32, "float32", "DBC X position / RdrObjDx"),
            field("cluster_dist_lat", 36, "float32", "DBC Y position / RdrObjDy"),
            field("cluster_vrel_long", 40, "float32", "DBC X velocity / RdrObjVxAbs"),
            field("cluster_vrel_lat", 44, "float32", "DBC Y velocity / RdrObjVyAbs"),
        ],
    }


def field(name: str, offset: int, type_name: str, source: str) -> dict[str, Any]:
    return {"name": name, "offset": offset, "type": type_name, "source": source}


def write_markdown(path: Path, spec: dict[str, Any]) -> None:
    lines = ["# RadarService Format Notes\n\n状态：已根据真实 MCAP payload 探针锁定 V1。\n\n"]
    lines.append(f"- payload_size: {spec['payload_size']}\n")
    lines.append(f"- targets_offset: {spec['targets_offset']}\n")
    lines.append(f"- target_stride: {spec['target_stride']}\n")
    lines.append(f"- target_count: {spec['target_count']}\n\n")
    lines.append("## Object Slot Fields\n\n")
    for item in spec["fields"]:
        lines.append(f"- `{item['name']}` offset={item['offset']} type={item['type']} source={item['source']}\n")
    path.write_text("".join(lines), encoding="utf-8")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, default=Path("aisim_radar_replay/docs/RadarService_format.md"))
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    validate_probe(load_report(args.probe))
    spec = build_spec()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    write_markdown(args.md_out, spec)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
