#!/usr/bin/env python3
"""Validate RadarService MCAP structure and optional decoded target fields."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

try:
    from mcap.reader import make_reader
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Python package 'mcap' is required. Try:\n"
        "  python3 -m pip install mcap\n"
        "Then rerun this script from your project workspace."
    ) from exc

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from radarservice_spec import FormatSpec, RADAR_TOPICS, load_format as load_format_spec, read_cdr_string, unpack_value

EXPECTED_TOPICS = tuple(RADAR_TOPICS.values())

DEFAULT_EXPECTED_COUNT = 800
FRAME_INTERVAL_NS = 50_000_000
TOLERANCE_NS = 5_000_000


def load_format(path: Path | None) -> FormatSpec | None:
    if path is None or not path.exists():
        return None
    return load_format_spec(path)


def decode_first_targets(data: bytes, spec: FormatSpec, limit: int = 5) -> list[dict[str, Any]]:
    targets = []
    for index in range(min(spec.target_count, limit)):
        base = spec.targets_offset + index * spec.target_stride
        item: dict[str, Any] = {"index": index}
        for field in spec.fields:
            item[field.name] = unpack_value(data, base + field.offset, field.type_name)
        targets.append(item)
    return targets


def collect_stats(mcap_path: Path, expected_topics: tuple[str, ...]) -> dict[str, Any]:
    stats: dict[str, Any] = defaultdict(lambda: {"count": 0, "log_times": [], "lengths": [], "first": None})
    schemas: set[str] = set()
    all_topics: set[str] = set()
    with mcap_path.open("rb") as handle:
        reader = make_reader(handle)
        summary = reader.get_summary()
        if summary:
            for schema in summary.schemas.values():
                schemas.add(schema.name)
            for channel in summary.channels.values():
                all_topics.add(channel.topic)
        for _, channel, message in reader.iter_messages(topics=list(expected_topics)):
            item = stats[channel.topic]
            item["count"] += 1
            item["log_times"].append(message.log_time)
            item["lengths"].append(len(message.data))
            if item["first"] is None:
                item["first"] = message.data
    return {"schemas": schemas, "topics": dict(stats), "all_topics": all_topics}


def validate_topic(
    topic: str,
    item: dict[str, Any],
    spec: FormatSpec | None,
    expected_count: int,
) -> list[str]:
    errors = []
    count = item["count"]
    if count != expected_count:
        errors.append(f"{topic}: count {count} != {expected_count}")
    lengths = set(item["lengths"])
    if spec and lengths != {spec.payload_size}:
        errors.append(f"{topic}: payload lengths {sorted(lengths)} != {spec.payload_size}")
    if spec and item["first"]:
        first = item["first"]
        if first[: len(spec.cdr_header)] != spec.cdr_header:
            errors.append(f"{topic}: CDR header mismatch")
        frame_id = read_cdr_string(first, 24)
        expected_frame_ids = set(spec.frame_ids.values())
        if expected_frame_ids and frame_id not in expected_frame_ids:
            errors.append(f"{topic}: unexpected frame_id {frame_id}")
    times = item["log_times"]
    for index in range(1, len(times)):
        delta = times[index] - times[index - 1]
        if abs(delta - FRAME_INTERVAL_NS) > TOLERANCE_NS:
            errors.append(f"{topic}: interval at #{index} is {delta}ns")
            break
    return errors


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="MCAP file to validate")
    parser.add_argument(
        "--format",
        type=Path,
        default=Path("aisim_radar_replay/docs/RadarService_format.json"),
        help="Optional RadarService format spec",
    )
    parser.add_argument("--expected-count", type=int, default=DEFAULT_EXPECTED_COUNT)
    parser.add_argument("--expected-topic", action="append", help="Restrict validation to selected radar topic")
    parser.add_argument("--allow-extra-topics", action="store_true", help="Allow non-radar topics in full real MCAP")
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    spec = load_format(args.format)
    expected_topics = tuple(args.expected_topic or EXPECTED_TOPICS)
    report = collect_stats(args.input, expected_topics)
    errors: list[str] = []
    print("Radar MCAP validation")
    print(f"input: {args.input}")
    print(f"schemas: {sorted(report['schemas'])}")
    if spec is None:
        print("format: not provided, running structural checks only")
    else:
        print(f"format: payload_size={spec.payload_size} targets={spec.target_count}")
    topics = report["topics"]
    for topic in expected_topics:
        if topic not in topics:
            errors.append(f"missing topic: {topic}")
            continue
        item = topics[topic]
        topic_errors = validate_topic(topic, item, spec, args.expected_count)
        errors.extend(topic_errors)
        length_set = sorted(set(item["lengths"]))
        print(f"{topic}: count={item['count']} lengths={length_set[:6]}")
        if spec and item["first"]:
            targets = decode_first_targets(item["first"], spec, limit=2)
            print(f"  first targets: {targets}")
    extras = sorted(set(report["all_topics"]) - set(expected_topics))
    if extras and args.allow_extra_topics:
        print(f"extra topics ignored: {len(extras)}")
    elif extras:
        for topic in extras:
            errors.append(f"unexpected topic: {topic}")
    if errors:
        print("FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
