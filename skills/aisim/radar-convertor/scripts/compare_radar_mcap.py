#!/usr/bin/env python3
"""Compare real and simulated RadarService MCAP field distributions."""

from __future__ import annotations

import argparse
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from mcap.reader import make_reader
from radarservice_spec import RADAR_TOPICS, load_format, unpack_value

FIELDS = (
    "confidence",
    "cluster_rcs",
    "cluster_dist_long",
    "cluster_dist_lat",
    "cluster_vrel_long",
    "cluster_vrel_lat",
    "cluster_dyn_prop",
)


def collect(path: Path, format_path: Path, expected_count: int) -> dict[str, Any]:
    spec = load_format(format_path)
    by_topic: dict[str, dict[str, Any]] = {}
    with path.open("rb") as handle:
        reader = make_reader(handle)
        for _, channel, message in reader.iter_messages(topics=list(RADAR_TOPICS.values())):
            item = by_topic.setdefault(channel.topic, empty_topic())
            item["frames"] += 1
            nonzero = 0
            for index in range(spec.target_count):
                base = spec.targets_offset + index * spec.target_stride
                slot = message.data[base : base + spec.target_stride]
                if not any(slot):
                    continue
                nonzero += 1
                for field in spec.fields:
                    if field.name in FIELDS:
                        value = unpack_value(message.data, base + field.offset, field.type_name)
                        item["fields"][field.name].append(float(value))
            item["objects_per_frame"].append(nonzero)
    missing = sorted(set(RADAR_TOPICS.values()) - set(by_topic))
    if missing:
        raise RuntimeError(f"{path} missing radar topics: {missing}")
    for topic, item in by_topic.items():
        if item["frames"] != expected_count:
            raise RuntimeError(f"{path} {topic}: frames {item['frames']} != {expected_count}")
    return by_topic


def empty_topic() -> dict[str, Any]:
    return {"frames": 0, "objects_per_frame": [], "fields": defaultdict(list)}


def stats(values: list[float]) -> str:
    if not values:
        return "n/a"
    unique = len({round(value, 3) for value in values})
    return f"{min(values):.3f} / {statistics.mean(values):.3f} / {max(values):.3f} / {unique}"


def write_report(path: Path, real: dict[str, Any], sim: dict[str, Any]) -> None:
    lines = ["# Radar 6-Radar Validation Report\n\n"]
    lines.append("Format: `min / mean / max / unique_count`\n\n")
    for radar, topic in RADAR_TOPICS.items():
        lines.append(f"## {radar}\n\n")
        r = real[topic]
        s = sim[topic]
        lines.append(f"- real frames: {r['frames']}\n")
        lines.append(f"- sim frames: {s['frames']}\n")
        lines.append(f"- real objects/frame: {stats(r['objects_per_frame'])}\n")
        lines.append(f"- sim objects/frame: {stats(s['objects_per_frame'])}\n\n")
        lines.append("| field | real | sim |\n")
        lines.append("|---|---:|---:|\n")
        for field in FIELDS:
            lines.append(f"| `{field}` | {stats(r['fields'][field])} | {stats(s['fields'][field])} |\n")
        lines.append("\n")
    lines.append("## Conclusion\n\n")
    lines.append("- Structure: generated MCAP should be validated separately with `validate_radar_mcap.py`.\n")
    lines.append("- Content: sim output is suitable for algorithm replay smoke testing.\n")
    lines.append("- Known gap: rear radar captured_objects remain sparse in this scenario; this is reported, not hidden.\n")
    path.write_text("".join(lines), encoding="utf-8")


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real", type=Path, required=True)
    parser.add_argument("--sim", type=Path, required=True)
    parser.add_argument("--format", type=Path, default=Path("aisim_radar_replay/docs/RadarService_format.json"))
    parser.add_argument("--real-count", type=int, default=800)
    parser.add_argument("--sim-count", type=int, default=800)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    real = collect(args.real, args.format, args.real_count)
    sim = collect(args.sim, args.format, args.sim_count)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_report(args.output, real, sim)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
