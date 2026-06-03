#!/usr/bin/env python3
"""Profile real hv_sensor_msgs/msg/RadarService CDR payloads."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from mcap.reader import make_reader
from radarservice_spec import RADAR_TOPICS, read_cdr_string, unpack_value


def sample_messages(mcap: Path, limit: int) -> dict[str, list[dict[str, Any]]]:
    samples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    wanted = set(RADAR_TOPICS.values())
    with mcap.open("rb") as handle:
        reader = make_reader(handle)
        for _, channel, message in reader.iter_messages(topics=list(wanted)):
            if len(samples[channel.topic]) >= limit:
                continue
            data = message.data
            samples[channel.topic].append(profile_payload(data, message.log_time))
            if all(len(samples[topic]) >= limit for topic in wanted):
                break
    return dict(samples)


def profile_payload(data: bytes, log_time: int) -> dict[str, Any]:
    nonzero_slots = count_nonzero_slots(data)
    return {
        "log_time": log_time,
        "payload_size": len(data),
        "cdr_header_hex": data[:4].hex(),
        "host_time_s": unpack_value(data, 4, "float64"),
        "sensor_time_s": unpack_value(data, 12, "float64"),
        "frame_id": read_cdr_string(data, 24),
        "fixed_float_48": unpack_value(data, 48, "float32"),
        "radar_id": unpack_value(data, 60, "uint32"),
        "sequence": unpack_value(data, 64, "uint32"),
        "slot_capacity": unpack_value(data, 68, "uint32"),
        "nonzero_slots": nonzero_slots,
        "first_slots": decode_slots(data, limit=4),
    }


def count_nonzero_slots(data: bytes) -> int:
    count = 0
    for index in range(40):
        base = 72 + index * 48
        if any(data[base : base + 48]):
            count += 1
    return count


def decode_slots(data: bytes, limit: int) -> list[dict[str, Any]]:
    slots = []
    for index in range(limit):
        base = 72 + index * 48
        slots.append(
            {
                "index": index,
                "raw_flags_hex": data[base : base + 4].hex(),
                "object_id_byte0": unpack_value(data, base, "uint8"),
                "confidence": unpack_value(data, base + 4, "float32"),
                "state_bytes": list(data[base + 8 : base + 12]),
                "x_std": unpack_value(data, base + 12, "float32"),
                "y_std": unpack_value(data, base + 16, "float32"),
                "vx_std": unpack_value(data, base + 20, "float32"),
                "ax_or_vx_abs": unpack_value(data, base + 24, "float32"),
                "obstacle_prob": unpack_value(data, base + 28, "float32"),
                "dist_long": unpack_value(data, base + 32, "float32"),
                "dist_lat": unpack_value(data, base + 36, "float32"),
                "vrel_long": unpack_value(data, base + 40, "float32"),
                "vrel_lat": unpack_value(data, base + 44, "float32"),
            }
        )
    return slots


def summarize(samples: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    topics = {}
    for topic, rows in samples.items():
        sizes = sorted({row["payload_size"] for row in rows})
        slots = [row["nonzero_slots"] for row in rows]
        topics[topic] = {
            "sample_count": len(rows),
            "payload_sizes": sizes,
            "cdr_headers": sorted({row["cdr_header_hex"] for row in rows}),
            "frame_ids": sorted({row["frame_id"] for row in rows}),
            "radar_ids": sorted({row["radar_id"] for row in rows}),
            "slot_capacity": sorted({row["slot_capacity"] for row in rows}),
            "nonzero_slots_min": min(slots),
            "nonzero_slots_max": max(slots),
            "nonzero_slots_mean": statistics.mean(slots),
            "first_sample": rows[0],
        }
    return {"topics": topics}


def write_markdown(path: Path, report: dict[str, Any], source: Path) -> None:
    lines = [f"# RadarService Probe Report\n\nSource: `{source}`\n"]
    for topic, info in report["topics"].items():
        lines.append(f"\n## {topic}\n")
        lines.append(f"- samples: {info['sample_count']}\n")
        lines.append(f"- payload_sizes: {info['payload_sizes']}\n")
        lines.append(f"- cdr_headers: {info['cdr_headers']}\n")
        lines.append(f"- frame_ids: {info['frame_ids']}\n")
        lines.append(f"- radar_ids: {info['radar_ids']}\n")
        lines.append(f"- slot_capacity: {info['slot_capacity']}\n")
        lines.append(
            "- nonzero_slots: "
            f"{info['nonzero_slots_min']}..{info['nonzero_slots_max']} "
            f"mean={info['nonzero_slots_mean']:.2f}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcap", type=Path, required=True)
    parser.add_argument("--sample-limit", type=int, default=200)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    samples = sample_messages(args.mcap, args.sample_limit)
    report = summarize(samples)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_markdown(args.md_out, report, args.mcap)
    print(f"Wrote {args.json_out} and {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
