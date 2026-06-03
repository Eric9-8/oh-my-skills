#!/usr/bin/env python3
"""Convert aiSim radar object exports to hv_sensor_msgs/msg/RadarService MCAP."""

from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path
from typing import Any, Iterable

try:
    from mcap.writer import Writer
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Python package 'mcap' is required. Try:\n"
        "  python3 -m pip install mcap\n"
        "Then rerun this script from your project workspace."
    ) from exc

SCRIPT_DIR = Path(__file__).resolve().parent
import sys
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from radar_objects import frame_to_objects, load_aisim_frame
from radarservice_spec import FormatSpec, RADAR_TOPICS, load_format, pack_value, write_string

FRAME_INTERVAL_NS = 50_000_000
DEFAULT_START_TIME_NS = 1778500493663231744
SOURCE_MODES = ("captured_objects", "objects_with_targets")
RADAR_SLOT_LIMITS = {
    "radar_front": 40,
    "radar_front_left": 32,
    "radar_front_right": 32,
    "radar_rear": 40,
    "radar_rear_left": 32,
    "radar_rear_right": 32,
}


def load_targets_file(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            targets = data.get("targets", data.get("objects", []))
        else:
            targets = data
        if not isinstance(targets, list):
            raise ValueError(f"{path} JSON must contain a target list")
        return [dict(item) for item in targets]
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    raise ValueError(f"Unsupported radar export file type: {path}")


def find_frame_files(sensor_dir: Path) -> list[Path]:
    files = []
    for pattern in ("*.json", "*.csv"):
        files.extend(sensor_dir.glob(pattern))
    return sorted(files)


def select_frame_files(radar: str, files: list[Path], expected_frames: int, frame_limit: int | None) -> list[Path]:
    if len(files) < expected_frames:
        raise ValueError(f"{radar}: frame count {len(files)} < expected {expected_frames}")
    selected = files[:expected_frames]
    if frame_limit is not None:
        if frame_limit > len(files):
            raise ValueError(f"{radar}: frame-limit {frame_limit} > available {len(files)}")
        selected = files[:frame_limit]
    return selected


def target_value(target: dict[str, Any], name: str, fallback: float = 0.0) -> Any:
    aliases = {
        "cluster_dist_long": ("cluster_dist_long", "dx", "dist_long", "x", "position_x", "distance_long"),
        "cluster_dist_lat": ("cluster_dist_lat", "dy", "dist_lat", "y", "position_y", "distance_lat"),
        "cluster_vrel_long": ("cluster_vrel_long", "vx", "vrel_long", "velocity_x"),
        "cluster_vrel_lat": ("cluster_vrel_lat", "vy", "vrel_lat", "velocity_y"),
        "cluster_rcs": ("cluster_rcs", "rcs", "RCS"),
        "cluster_dyn_prop": ("cluster_dyn_prop", "motion_pattern", "dyn_prop", "dynamic_property"),
        "cluster_id": ("cluster_id", "object_id", "id", "track_id"),
        "confidence": ("confidence", "cluster_confidence", "probability_of_existence"),
        "valid_flag": ("valid_flag",),
        "update_flag": ("update_flag",),
        "x_std": ("x_std",),
        "y_std": ("y_std",),
        "vx_std": ("vx_std",),
        "ax_or_vx_abs": ("ax", "vx", "ax_or_vx_abs"),
        "object_type": ("object_type", "type"),
        "snr": ("snr", "cluster_snr"),
        "length": ("length", "object_length"),
        "width": ("width", "object_width"),
    }
    for key in aliases.get(name, (name,)):
        if key in target and target[key] not in ("", None):
            return target[key]
    if name in ("valid_flag", "update_flag"):
        return 1
    return fallback


def limit_targets(radar: str, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    limit = RADAR_SLOT_LIMITS[radar]
    if len(targets) <= limit:
        return targets
    return sorted(targets, key=target_rank)[:limit]


def target_rank(target: dict[str, Any]) -> tuple[float, float]:
    distance = float(target_value(target, "cluster_dist_long", 0.0))
    confidence = float(target_value(target, "confidence", 0.0))
    return (distance, -confidence)


def build_payload(targets: list[dict[str, Any]], spec: FormatSpec, radar: str, timestamp_ns: int, frame_index: int) -> bytes:
    if len(targets) > spec.target_count:
        raise ValueError(f"Too many targets: {len(targets)} > {spec.target_count}")
    payload = bytearray(spec.payload_size)
    payload[: len(spec.cdr_header)] = spec.cdr_header
    struct.pack_into("<d", payload, 4, timestamp_ns / 1_000_000_000.0)
    struct.pack_into("<d", payload, 12, timestamp_ns / 1_000_000_000.0)
    frame_id = spec.frame_ids.get(radar)
    if not frame_id:
        raise ValueError(f"Format spec missing frame_id for {radar}")
    write_string(payload, 24, frame_id)
    struct.pack_into("<f", payload, 48, 3.1796875)
    struct.pack_into("<d", payload, 52, timestamp_ns / 1_000_000_000.0)
    struct.pack_into("<I", payload, 60, spec.radar_ids.get(radar, 0))
    struct.pack_into("<I", payload, 64, frame_index)
    struct.pack_into("<I", payload, 68, spec.target_count)
    for target_index, target in enumerate(targets):
        base = spec.targets_offset + target_index * spec.target_stride
        for field in spec.fields:
            value = target_value(target, field.name)
            pack_value(payload, base + field.offset, field.type_name, value)
    return bytes(payload)


def objects_from_frame(path: Path, source_mode: str) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".csv":
        return load_targets_file(path)
    frame = load_aisim_frame(path)
    use_targets = source_mode == "objects_with_targets"
    return [item.to_payload_dict() for item in frame_to_objects(frame, use_targets)]


def register_channels(writer: Writer, radars: list[str]) -> dict[str, int]:
    schema_id = writer.register_schema(
        name="hv_sensor_msgs/msg/RadarService",
        encoding="ros2msg",
        data=b"",
    )
    return {
        sensor: writer.register_channel(
            topic=RADAR_TOPICS[sensor],
            message_encoding="cdr",
            schema_id=schema_id,
        )
        for sensor in radars
    }


def sensor_export_dir(input_dir: Path, radar: str, export_name: str | None) -> Path:
    if export_name:
        return input_dir / export_name
    return input_dir / radar


def write_mcap(options: argparse.Namespace, spec: FormatSpec) -> None:
    radars = options.radar or list(RADAR_TOPICS)
    invalid = sorted(set(radars) - set(RADAR_TOPICS))
    if invalid:
        raise ValueError(f"Unknown radar names: {invalid}")
    output = options.output
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer = Writer(handle)
        writer.start(profile="ros2", library="radar_to_mcap")
        channels = register_channels(writer, radars)
        total = 0
        for sensor, channel_id in channels.items():
            sensor_dir = sensor_export_dir(options.input_dir, sensor, options.export_sensor_name)
            if not sensor_dir.is_dir():
                raise FileNotFoundError(f"Missing aiSim export directory: {sensor_dir}")
            frame_files = find_frame_files(sensor_dir)
            if not frame_files:
                raise FileNotFoundError(f"No JSON/CSV radar frames in {sensor_dir}")
            frame_files = select_frame_files(sensor, frame_files, options.expected_frames, options.frame_limit)
            for frame_index, frame_path in enumerate(frame_files):
                targets = limit_targets(sensor, objects_from_frame(frame_path, options.source))
                timestamp_ns = options.start_time_ns + frame_index * FRAME_INTERVAL_NS
                payload = build_payload(targets, spec, sensor, timestamp_ns, frame_index)
                writer.add_message(
                    channel_id=channel_id,
                    log_time=timestamp_ns,
                    publish_time=timestamp_ns,
                    data=payload,
                )
                total += 1
            print(f"{sensor}: {len(frame_files)} frames")
        writer.finish()
    print(f"Wrote {output} with {total} messages")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True, help="aiSim export root")
    parser.add_argument("--output", type=Path, required=True, help="Output MCAP")
    parser.add_argument("--radar", action="append", choices=sorted(RADAR_TOPICS), help="Radar channel to emit")
    parser.add_argument("--export-sensor-name", default=None, help="aiSim export folder name for single-radar POC")
    parser.add_argument("--expected-frames", type=int, default=800, help="Required frame count per radar")
    parser.add_argument("--frame-limit", type=int, default=None, help="Use only the first N frames from each radar")
    parser.add_argument("--source", choices=SOURCE_MODES, default="captured_objects", help="aiSim JSON source mode")
    parser.add_argument(
        "--format",
        type=Path,
        default=Path("aisim_radar_replay/docs/RadarService_format.json"),
        help="Machine-readable RadarService format spec",
    )
    parser.add_argument("--start-time-ns", type=int, default=DEFAULT_START_TIME_NS)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    spec = load_format(args.format)
    write_mcap(args, spec)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
