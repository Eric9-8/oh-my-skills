#!/usr/bin/env python3
"""
validate_pattern_channel.py - 验证 Pattern JSON 与 channel_data 的一致性

用途：第一层验证（手册 → Pattern）
- 检查 Pattern 中的通道角度是否与手册提取的 channel_data 一致
- 生成差异报告

Usage:
    python3 validate_pattern_channel.py \
        --pattern "output/ATX_100/ATX_100_pattern.json" \
        --channel-data "output/ATX_100/channel_data.py" \
        --out "output/ATX_100/channel_validation_report.md"

Author: aiSim-agent
Version: 1.0.0
Date: 2026-01-04
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

@dataclass
class ChannelInfo:
    channel_id: int
    az_even: float
    az_odd: float
    elevation: float

@dataclass
class ValidationResult:
    total_channels: int
    matched: int
    mismatched: int
    missing_in_pattern: int
    errors: List[str]

def parse_channel_data_py(path: Path) -> List[ChannelInfo]:
    """Parse channel_data.py file."""
    content = path.read_text(encoding="utf-8")

    # Extract CHANNEL_DATA list using regex
    pattern = r'\((\d+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)\)'
    matches = re.findall(pattern, content)

    channels = []
    for m in matches:
        channels.append(ChannelInfo(
            channel_id=int(m[0]),
            az_even=float(m[1]),
            az_odd=float(m[2]),
            elevation=float(m[3])
        ))
    return channels

def parse_channel_data_csv(path: Path) -> List[ChannelInfo]:
    """Parse channel_data.csv file."""
    channels = []
    lines = path.read_text(encoding="utf-8").strip().split('\n')

    for line in lines[1:]:  # Skip header
        if not line.strip() or line.startswith('#'):
            continue
        parts = line.split(',')
        if len(parts) >= 4:
            channels.append(ChannelInfo(
                channel_id=int(parts[0]),
                az_even=float(parts[1]),
                az_odd=float(parts[2]),
                elevation=float(parts[3])
            ))
    return channels

def load_channel_data(path: Path) -> List[ChannelInfo]:
    """Load channel data from .py or .csv file."""
    if path.suffix == '.py':
        return parse_channel_data_py(path)
    elif path.suffix == '.csv':
        return parse_channel_data_csv(path)
    else:
        raise ValueError(f"Unsupported channel data format: {path.suffix}")

def load_pattern(path: Path) -> dict:
    """Load pattern JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))

def extract_pattern_channels(pattern: dict, h_fov: float = 120.0) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
    """
    Extract unique (azimuth_offset, elevation) pairs from pattern.

    For Flash LiDAR with absolute azimuth:
    - AzimuthDeg = scan_az + channel_offset
    - We need to extract channel_offset by finding the offset at scan start (first TimeOffsetS)

    Returns: (even_cycle_channels, odd_cycle_channels)
    """
    cycles = pattern.get("ScanningPattern", [])
    if not cycles:
        return [], []

    def extract_from_cycle(cycle_data: dict) -> List[Tuple[float, float]]:
        lasers = cycle_data.get("Lasers", [])
        if not lasers:
            return []

        # Find minimum TimeOffsetS (scan start)
        min_time = min(l["TimeOffsetS"] for l in lasers)

        # Get lasers at scan start
        start_lasers = [l for l in lasers if abs(l["TimeOffsetS"] - min_time) < 1e-9]

        # For absolute azimuth pattern, the azimuth at scan start = -h_fov/2 + channel_offset
        # So channel_offset = azimuth - (-h_fov/2) = azimuth + h_fov/2
        scan_start_az = -h_fov / 2

        channels = []
        for l in start_lasers:
            az_offset = l["AzimuthDeg"] - scan_start_az
            el = l["ElevationDeg"]
            channels.append((round(az_offset, 2), round(el, 2)))

        return channels

    even_channels = extract_from_cycle(cycles[0]) if len(cycles) > 0 else []
    odd_channels = extract_from_cycle(cycles[1]) if len(cycles) > 1 else even_channels

    return even_channels, odd_channels

def validate(
    channel_data: List[ChannelInfo],
    pattern_even: List[Tuple[float, float]],
    pattern_odd: List[Tuple[float, float]],
    tolerance: float = 0.05
) -> ValidationResult:
    """Validate pattern channels against channel_data."""
    errors = []
    matched = 0
    mismatched = 0
    missing = 0

    pattern_even_set = set(pattern_even)
    pattern_odd_set = set(pattern_odd)

    for ch in channel_data:
        expected_even = (round(ch.az_even, 2), round(ch.elevation, 2))
        expected_odd = (round(ch.az_odd, 2), round(ch.elevation, 2))

        # Check if channel exists in pattern (with tolerance)
        found_even = any(
            abs(p[0] - expected_even[0]) <= tolerance and abs(p[1] - expected_even[1]) <= tolerance
            for p in pattern_even_set
        )
        found_odd = any(
            abs(p[0] - expected_odd[0]) <= tolerance and abs(p[1] - expected_odd[1]) <= tolerance
            for p in pattern_odd_set
        )

        if found_even and found_odd:
            matched += 1
        elif not found_even and not found_odd:
            missing += 1
            errors.append(f"Channel {ch.channel_id}: not found in pattern (expected even=({ch.az_even}, {ch.elevation}), odd=({ch.az_odd}, {ch.elevation}))")
        else:
            mismatched += 1
            if not found_even:
                errors.append(f"Channel {ch.channel_id}: even frame mismatch (expected ({ch.az_even}, {ch.elevation}))")
            if not found_odd:
                errors.append(f"Channel {ch.channel_id}: odd frame mismatch (expected ({ch.az_odd}, {ch.elevation}))")

    return ValidationResult(
        total_channels=len(channel_data),
        matched=matched,
        mismatched=mismatched,
        missing_in_pattern=missing,
        errors=errors
    )

def generate_report(
    channel_data_path: Path,
    pattern_path: Path,
    result: ValidationResult,
    pattern_even: List[Tuple[float, float]],
    pattern_odd: List[Tuple[float, float]],
    h_fov: float
) -> str:
    """Generate validation report."""
    lines = [
        "# Pattern vs Channel Data 校验报告",
        "",
        "## 输入",
        f"- Channel Data: `{channel_data_path.as_posix()}`",
        f"- Pattern: `{pattern_path.as_posix()}`",
        f"- 水平 FOV (用于计算偏移): {h_fov}°",
        "",
        "## 概要",
        f"- 手册通道数: {result.total_channels}",
        f"- Pattern 偶数帧通道数: {len(pattern_even)}",
        f"- Pattern 奇数帧通道数: {len(pattern_odd)}",
        "",
        "## 验证结果",
        f"- 匹配: {result.matched} / {result.total_channels} ({100*result.matched/result.total_channels:.1f}%)",
        f"- 不匹配: {result.mismatched}",
        f"- 缺失: {result.missing_in_pattern}",
        "",
    ]

    if result.matched == result.total_channels:
        lines.append("**结论: ✅ 所有通道验证通过**")
    else:
        lines.append("**结论: ❌ 存在不匹配的通道**")
        lines.append("")
        lines.append("## 错误详情")
        for err in result.errors[:20]:  # Limit to first 20 errors
            lines.append(f"- {err}")
        if len(result.errors) > 20:
            lines.append(f"- ... 还有 {len(result.errors) - 20} 个错误")

    lines.append("")
    return "\n".join(lines)

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Pattern JSON against channel_data")
    parser.add_argument("--pattern", required=True, help="Path to pattern JSON file")
    parser.add_argument("--channel-data", required=True, help="Path to channel_data.py or .csv file")
    parser.add_argument("--out", help="Output report path (default: stdout)")
    parser.add_argument("--h-fov", type=float, default=120.0, help="Horizontal FOV in degrees (default: 120)")
    parser.add_argument("--tolerance", type=float, default=0.05, help="Angle tolerance in degrees (default: 0.05)")

    args = parser.parse_args()

    pattern_path = Path(args.pattern)
    channel_data_path = Path(args.channel_data)

    if not pattern_path.exists():
        print(f"Error: Pattern file not found: {pattern_path}", file=sys.stderr)
        return 1
    if not channel_data_path.exists():
        print(f"Error: Channel data file not found: {channel_data_path}", file=sys.stderr)
        return 1

    # Load data
    channel_data = load_channel_data(channel_data_path)
    pattern = load_pattern(pattern_path)

    # Extract pattern channels
    pattern_even, pattern_odd = extract_pattern_channels(pattern, args.h_fov)

    # Validate
    result = validate(channel_data, pattern_even, pattern_odd, args.tolerance)

    # Generate report
    report = generate_report(
        channel_data_path, pattern_path, result,
        pattern_even, pattern_odd, args.h_fov
    )

    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Report written to: {args.out}")
    else:
        print(report)

    return 0 if result.matched == result.total_channels else 1

if __name__ == "__main__":
    sys.exit(main())
