#!/usr/bin/env python3
"""
校验 aiSim 导出的 LAS 点云是否与扫描模式（*_pattern.json）一致（快速一致性检查）。

支持：
- LAS v1.4
- Point Data Record Format 7
- Pattern JSON: ScanningPattern 或 VerticalScanningPattern

校验方法（KISS）：
1) 从 LAS 点云的 XYZ 反推出每个点的方位角/俯仰角（假设点坐标在 LiDAR 坐标系，或通过 --origin 做平移修正）。
2) 将点的(az, el)与 pattern 的离散角度集合做量化匹配（按 --bin-deg 分箱，默认 0.1°）。

注意：
- 由于场景遮挡/材质等原因，点云通常不会覆盖 pattern 的每一条 ray；本脚本更适合发现“明显错误”（FOV/角度偏移/周期设置/引用错文件等）。
- 对于 Flash LiDAR（ScanningPattern），`AzimuthDeg/ElevationDeg` 表示 ray 的绝对方向；若 pattern 的 `AzimuthDeg` 范围明显小于 config 的 `horizontal_fov_deg`，通常意味着 pattern 缺失扫描角。
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclass(frozen=True)
class LasHeader:
    version_major: int
    version_minor: int
    header_size: int
    offset_to_points: int
    point_format: int
    point_record_length: int
    point_count: int
    x_scale: float
    y_scale: float
    z_scale: float
    x_offset: float
    y_offset: float
    z_offset: float


POINT_FORMAT_7 = struct.Struct("<iiiHBBBBhHdHHH")  # 36 bytes


def _quantize(value: float, bin_deg: float) -> int:
    scaled = value / bin_deg
    if scaled >= 0:
        return int(math.floor(scaled + 0.5))
    return int(math.ceil(scaled - 0.5))


def _angles_from_xyz(x: float, y: float, z: float) -> tuple[float, float]:
    az = math.degrees(math.atan2(y, x))
    el = math.degrees(math.atan2(z, math.hypot(x, y)))
    return az, el


def read_las_header(path: Path) -> LasHeader:
    with path.open("rb") as f:
        header_prefix = f.read(375)  # LAS 1.4 常见 header size

    if len(header_prefix) < 227:
        raise ValueError(f"LAS header too small: {len(header_prefix)} bytes")

    if header_prefix[0:4] != b"LASF":
        raise ValueError("Not a LAS file (missing LASF signature)")

    version_major = header_prefix[24]
    version_minor = header_prefix[25]
    header_size = struct.unpack_from("<H", header_prefix, 94)[0]
    offset_to_points = struct.unpack_from("<I", header_prefix, 96)[0]
    point_format = header_prefix[104]
    point_record_length = struct.unpack_from("<H", header_prefix, 105)[0]
    legacy_point_count = struct.unpack_from("<I", header_prefix, 107)[0]

    x_scale, y_scale, z_scale = struct.unpack_from("<ddd", header_prefix, 131)
    x_offset, y_offset, z_offset = struct.unpack_from("<ddd", header_prefix, 155)

    point_count = legacy_point_count
    if version_major == 1 and version_minor >= 4 and len(header_prefix) >= 255:
        extended_point_count = struct.unpack_from("<Q", header_prefix, 247)[0]
        point_count = extended_point_count or legacy_point_count

    return LasHeader(
        version_major=version_major,
        version_minor=version_minor,
        header_size=header_size,
        offset_to_points=offset_to_points,
        point_format=point_format,
        point_record_length=point_record_length,
        point_count=point_count,
        x_scale=x_scale,
        y_scale=y_scale,
        z_scale=z_scale,
        x_offset=x_offset,
        y_offset=y_offset,
        z_offset=z_offset,
    )


@dataclass(frozen=True)
class PatternBins:
    kind: str  # "scanning" | "vertical"
    bin_deg: float
    az_bins: set[tuple[int, int]]  # (qaz, qel) for scanning
    el_bins: set[int]  # qel for vertical
    cycles: int
    rays: int
    az_min: float
    az_max: float
    el_min: float
    el_max: float


@dataclass(frozen=True)
class ConfigHints:
    path: Path
    min_range_m: Optional[float]
    max_range_m: Optional[float]
    horizontal_fov_deg: Optional[float]
    vertical_fov_deg: Optional[float]
    frame_rate_hz: Optional[float]
    rpm: Optional[float]


def load_pattern_bins(pattern_path: Path, bin_deg: float) -> PatternBins:
    obj = json.loads(pattern_path.read_text(encoding="utf-8"))

    if "ScanningPattern" in obj:
        az_bins: set[tuple[int, int]] = set()
        el_bins: set[int] = set()
        cycles = 0
        rays = 0
        az_min = float("inf")
        az_max = float("-inf")
        el_min = float("inf")
        el_max = float("-inf")

        for cycle in obj["ScanningPattern"]:
            cycles += 1
            lasers = cycle.get("Lasers")
            if not isinstance(lasers, list):
                raise ValueError("Invalid ScanningPattern: missing Lasers[]")
            for entry in lasers:
                az = float(entry["AzimuthDeg"])
                el = float(entry["ElevationDeg"])
                rays += 1
                az_min = min(az_min, az)
                az_max = max(az_max, az)
                el_min = min(el_min, el)
                el_max = max(el_max, el)
                az_bins.add((_quantize(az, bin_deg), _quantize(el, bin_deg)))

        return PatternBins(
            kind="scanning",
            bin_deg=bin_deg,
            az_bins=az_bins,
            el_bins=el_bins,
            cycles=cycles,
            rays=rays,
            az_min=az_min,
            az_max=az_max,
            el_min=el_min,
            el_max=el_max,
        )

    if "VerticalScanningPattern" in obj:
        az_bins = set()
        el_bins: set[int] = set()
        cycles = 1
        rays = 0
        az_min = float("inf")
        az_max = float("-inf")
        el_min = float("inf")
        el_max = float("-inf")

        for entry in obj["VerticalScanningPattern"]:
            rays += 1
            az = float(entry.get("AzimuthOffsetDeg", 0.0))
            el = float(entry["ElevationDeg"])
            az_min = min(az_min, az)
            az_max = max(az_max, az)
            el_min = min(el_min, el)
            el_max = max(el_max, el)
            el_bins.add(_quantize(el, bin_deg))

        return PatternBins(
            kind="vertical",
            bin_deg=bin_deg,
            az_bins=az_bins,
            el_bins=el_bins,
            cycles=cycles,
            rays=rays,
            az_min=az_min,
            az_max=az_max,
            el_min=el_min,
            el_max=el_max,
        )

    raise ValueError("Unsupported pattern JSON: expected ScanningPattern or VerticalScanningPattern")


def resolve_pattern_path(pattern: Optional[str], config: Optional[str]) -> Path:
    if pattern:
        return Path(pattern)
    if not config:
        raise ValueError("Provide --pattern or --config")

    config_path = Path(config)
    conf = json.loads(config_path.read_text(encoding="utf-8"))
    sensor = conf["sensors"]["lidar_sensor"]
    lidar_config = sensor.get("lidar_config", {})
    ref = (
        lidar_config.get("scanning_pattern_file")
        or lidar_config.get("vertical_scanning_pattern_file")
        or sensor.get("scanning_pattern_file")
        or sensor.get("vertical_scanning_pattern_file")
    )
    if not ref:
        raise ValueError("Cannot find scanning_pattern_file in config JSON")

    candidate = config_path.parent / os.path.basename(str(ref))
    if candidate.exists():
        return candidate

    raise ValueError(f"Pattern file not found near config: {candidate}")


def iter_points_format7(
    path: Path,
    header: LasHeader,
    *,
    max_points: int,
    origin_xyz: tuple[float, float, float],
) -> Iterator[tuple[float, float, float, float]]:
    if header.point_record_length < POINT_FORMAT_7.size:
        raise ValueError(
            f"Point record length too small for format 7: {header.point_record_length} < {POINT_FORMAT_7.size}"
        )

    remaining = header.point_count
    if max_points > 0:
        remaining = min(remaining, max_points)

    ox, oy, oz = origin_xyz
    record_len = header.point_record_length
    chunk_points = 8192

    with path.open("rb") as f:
        f.seek(header.offset_to_points)
        while remaining > 0:
            batch = min(remaining, chunk_points)
            data = f.read(record_len * batch)
            if len(data) < record_len:
                break
            for i in range(0, len(data), record_len):
                unpacked = POINT_FORMAT_7.unpack_from(data, i)
                raw_x, raw_y, raw_z = unpacked[0], unpacked[1], unpacked[2]
                gps_time = unpacked[10]
                x = raw_x * header.x_scale + header.x_offset - ox
                y = raw_y * header.y_scale + header.y_offset - oy
                z = raw_z * header.z_scale + header.z_offset - oz
                yield x, y, z, gps_time
            remaining -= batch


@dataclass
class MatchStats:
    read: int = 0
    processed: int = 0
    skipped_range: int = 0
    matched: int = 0
    unique_matched_bins: int = 0
    unmatched_examples: list[str] = None  # type: ignore[assignment]
    az_min: float = float("inf")
    az_max: float = float("-inf")
    el_min: float = float("inf")
    el_max: float = float("-inf")

    def __post_init__(self) -> None:
        if self.unmatched_examples is None:
            self.unmatched_examples = []


def validate_points(
    points: Iterable[tuple[float, float, float, float]],
    pattern_bins: PatternBins,
    *,
    max_unmatched_examples: int,
    min_range_m: float,
    max_range_m: Optional[float],
) -> MatchStats:
    stats = MatchStats()
    seen_bins: set[object] = set()

    if pattern_bins.kind == "scanning":
        for x, y, z, gps_time in points:
            stats.read += 1
            if x == 0.0 and y == 0.0 and z == 0.0:
                continue

            r = math.sqrt(x * x + y * y + z * z)
            if r < min_range_m or (max_range_m is not None and r > max_range_m):
                stats.skipped_range += 1
                continue

            stats.processed += 1
            az, el = _angles_from_xyz(x, y, z)
            stats.az_min = min(stats.az_min, az)
            stats.az_max = max(stats.az_max, az)
            stats.el_min = min(stats.el_min, el)
            stats.el_max = max(stats.el_max, el)

            qaz = _quantize(az, pattern_bins.bin_deg)
            qel = _quantize(el, pattern_bins.bin_deg)

            matched_key = None
            for daz in (-1, 0, 1):
                for del_ in (-1, 0, 1):
                    key = (qaz + daz, qel + del_)
                    if key in pattern_bins.az_bins:
                        matched_key = key
                        break
                if matched_key is not None:
                    break

            if matched_key is not None:
                stats.matched += 1
                seen_bins.add(matched_key)
            elif len(stats.unmatched_examples) < max_unmatched_examples:
                stats.unmatched_examples.append(
                    f"- x={x:.3f}, y={y:.3f}, z={z:.3f}, az={az:.3f}°, el={el:.3f}°, gps_time={gps_time:.6f}"
                )

        stats.unique_matched_bins = len(seen_bins)
        return stats

    # vertical pattern：只校验俯仰角集合（方位角由旋转决定，难以从点云直接约束）
    for x, y, z, gps_time in points:
        stats.read += 1
        if x == 0.0 and y == 0.0 and z == 0.0:
            continue

        r = math.sqrt(x * x + y * y + z * z)
        if r < min_range_m or (max_range_m is not None and r > max_range_m):
            stats.skipped_range += 1
            continue

        stats.processed += 1
        az, el = _angles_from_xyz(x, y, z)
        stats.az_min = min(stats.az_min, az)
        stats.az_max = max(stats.az_max, az)
        stats.el_min = min(stats.el_min, el)
        stats.el_max = max(stats.el_max, el)

        qel = _quantize(el, pattern_bins.bin_deg)
        if qel in pattern_bins.el_bins:
            stats.matched += 1
            seen_bins.add(qel)
        elif len(stats.unmatched_examples) < max_unmatched_examples:
            stats.unmatched_examples.append(
                f"- x={x:.3f}, y={y:.3f}, z={z:.3f}, az={az:.3f}°, el={el:.3f}°, gps_time={gps_time:.6f}"
            )

    stats.unique_matched_bins = len(seen_bins)
    return stats


def build_report(
    *,
    las_path: Path,
    header: LasHeader,
    pattern_path: Path,
    pattern_bins: PatternBins,
    stats: MatchStats,
    max_points: int,
    origin_xyz: tuple[float, float, float],
    min_range_m: float,
    max_range_m: Optional[float],
    config_hints: Optional[ConfigHints],
) -> str:
    processed = stats.processed
    matched = stats.matched
    match_rate = (matched / processed) if processed else 0.0

    expected_bins = len(pattern_bins.az_bins) if pattern_bins.kind == "scanning" else len(pattern_bins.el_bins)
    coverage = (stats.unique_matched_bins / expected_bins) if expected_bins else 0.0

    max_points_note = f"{max_points} (截断)" if max_points > 0 else "全部"
    origin_note = f"({origin_xyz[0]}, {origin_xyz[1]}, {origin_xyz[2]})"

    lines: list[str] = []
    lines.append("# LAS vs Pattern 校验报告")
    lines.append("")
    lines.append("## 输入")
    lines.append(f"- LAS: `{las_path.as_posix()}`")
    lines.append(f"- Pattern: `{pattern_path.as_posix()}`")
    if config_hints is not None:
        lines.append(f"- Config: `{config_hints.path.as_posix()}`")
    lines.append(f"- 采样点数: {max_points_note}")
    lines.append(f"- origin 偏移: {origin_note}")
    max_range_note = f"{max_range_m}" if max_range_m is not None else "(未限制)"
    lines.append(f"- 距离过滤: min={min_range_m}m, max={max_range_note}m")
    lines.append("")
    lines.append("## LAS 概要")
    lines.append(f"- 版本: {header.version_major}.{header.version_minor}")
    lines.append(f"- Point Data Record Format: {header.point_format}")
    lines.append(f"- Point Record Length: {header.point_record_length} bytes")
    lines.append(f"- 点数: {header.point_count}")
    lines.append("")
    lines.append("## Pattern 概要")
    lines.append(f"- 类型: {pattern_bins.kind}")
    lines.append(f"- cycles: {pattern_bins.cycles}")
    lines.append(f"- rays: {pattern_bins.rays}")
    lines.append(f"- bin_deg: {pattern_bins.bin_deg}")
    if pattern_bins.kind == "vertical":
        # Rotating LiDAR: az 是通道偏移量，不是扫描范围
        lines.append(f"- 通道偏移范围: AzimuthOffset=[{pattern_bins.az_min:.3f}°, {pattern_bins.az_max:.3f}°], Elevation=[{pattern_bins.el_min:.3f}°, {pattern_bins.el_max:.3f}°]")
        lines.append(f"- 说明: Rotating LiDAR 的 AzimuthOffset 是通道固定偏移量，实际扫描范围由机械旋转决定（通常 360°）")
    else:
        lines.append(f"- 角度范围(期望): az=[{pattern_bins.az_min:.3f}, {pattern_bins.az_max:.3f}], el=[{pattern_bins.el_min:.3f}, {pattern_bins.el_max:.3f}]")
        if config_hints is not None:
            if config_hints.frame_rate_hz is not None:
                lines.append(f"- config frame_rate: {config_hints.frame_rate_hz} Hz")
            if config_hints.horizontal_fov_deg is not None:
                az_span = pattern_bins.az_max - pattern_bins.az_min
                lines.append(f"- config horizontal_fov_deg: {config_hints.horizontal_fov_deg}° (pattern az_span≈{az_span:.3f}°)")
                if config_hints.horizontal_fov_deg >= 20.0 and az_span < config_hints.horizontal_fov_deg * 0.5:
                    lines.append("- ⚠️ 提示: pattern 的方位角跨度明显小于 config 的 horizontal_fov_deg，可能是 offset-only pattern（缺失扫描角）。")
            if config_hints.vertical_fov_deg is not None:
                el_span = pattern_bins.el_max - pattern_bins.el_min
                lines.append(f"- config vertical_fov_deg: {config_hints.vertical_fov_deg}° (pattern el_span≈{el_span:.3f}°)")
    lines.append("")
    lines.append("## 匹配结果")
    lines.append(f"- read: {stats.read}")
    lines.append(f"- skipped_range: {stats.skipped_range}")
    lines.append(f"- processed: {processed} (参与匹配)")
    lines.append(f"- matched: {matched} ({match_rate:.2%})")
    lines.append(f"- unique matched bins: {stats.unique_matched_bins} / {expected_bins} ({coverage:.2%})")
    if processed > 0 and stats.az_min != float('inf'):
        lines.append(f"- 角度范围(观测): az=[{stats.az_min:.3f}, {stats.az_max:.3f}], el=[{stats.el_min:.3f}, {stats.el_max:.3f}]")
    lines.append("")
    if stats.unmatched_examples:
        lines.append("## 未匹配样例（前若干条）")
        lines.extend(stats.unmatched_examples)
        lines.append("")
    lines.append("## 解释与局限")
    lines.append("- 遮挡/反射率/最大距离等会造成点云缺失，因此 coverage 不应期望 100%。")
    lines.append("- 若匹配率明显偏低，优先检查：pattern 文件引用、FOV/角分辨率、通道角度表、`max_stored_cycles` 与周期数是否一致。")
    return "\n".join(lines) + "\n"


def _load_distance_range_from_config(config_path: Path) -> tuple[Optional[float], Optional[float]]:
    conf = json.loads(config_path.read_text(encoding="utf-8"))
    sensor = conf.get("sensors", {}).get("lidar_sensor", {})
    lidar_config = sensor.get("lidar_config", {}) if isinstance(sensor, dict) else {}

    min_range = lidar_config.get("distance_min_meter")
    if min_range is None:
        min_range = sensor.get("distance_min_meter") if isinstance(sensor, dict) else None

    max_range = lidar_config.get("distance_max_meter")
    if max_range is None:
        max_range = sensor.get("distance_max_meter") if isinstance(sensor, dict) else None

    return (
        float(min_range) if min_range is not None else None,
        float(max_range) if max_range is not None else None,
    )


def _load_config_hints(config_path: Path) -> ConfigHints:
    conf = json.loads(config_path.read_text(encoding="utf-8"))
    sensor = conf.get("sensors", {}).get("lidar_sensor", {})
    lidar_config = sensor.get("lidar_config", {}) if isinstance(sensor, dict) else {}

    min_range, max_range = _load_distance_range_from_config(config_path)

    def _get_number(*keys: str) -> Optional[float]:
        for key in keys:
            value = lidar_config.get(key)
            if value is None and isinstance(sensor, dict):
                value = sensor.get(key)
            if value is not None:
                return float(value)
        return None

    return ConfigHints(
        path=config_path,
        min_range_m=min_range,
        max_range_m=max_range,
        horizontal_fov_deg=_get_number("horizontal_fov_deg", "horizontal_fov", "HorizontalFovDeg"),
        vertical_fov_deg=_get_number("vertical_fov_deg", "vertical_fov", "VerticalFovDeg"),
        frame_rate_hz=_get_number("frame_rate", "FrameRate"),
        rpm=_get_number("rpm", "RPM"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LAS v1.4 (PDRF 7) point cloud against aiSim pattern JSON")
    parser.add_argument("--las", required=True, help="Path to LAS file (v1.4, point format 7)")
    parser.add_argument("--pattern", help="Path to *_pattern.json (ScanningPattern or VerticalScanningPattern)")
    parser.add_argument("--config", help="Optional config JSON; used to auto-resolve pattern file when --pattern is omitted")
    parser.add_argument("--out", help="Write markdown report to this path (optional)")
    parser.add_argument("--bin-deg", type=float, default=0.1, help="Angle bin size in degrees (default: 0.1)")
    parser.add_argument("--max-points", type=int, default=200000, help="Max points to process (0 = all)")
    parser.add_argument("--origin", type=float, nargs=3, default=(0.0, 0.0, 0.0), help="Origin offset xyz to subtract")
    parser.add_argument("--min-range", type=float, default=None, help="Ignore points closer than this distance (meters). If omitted, try to read distance_min_meter from --config.")
    parser.add_argument("--max-range", type=float, default=None, help="Ignore points farther than this distance (meters). If omitted, try to read distance_max_meter from --config.")
    parser.add_argument("--max-unmatched", type=int, default=20, help="Max unmatched examples to include in report")
    args = parser.parse_args()

    las_path = Path(args.las)
    pattern_path = resolve_pattern_path(args.pattern, args.config)
    config_path = Path(args.config) if args.config else None

    header = read_las_header(las_path)
    if not (header.version_major == 1 and header.version_minor >= 4):
        raise SystemExit(f"Unsupported LAS version: {header.version_major}.{header.version_minor} (need 1.4)")
    if header.point_format != 7:
        raise SystemExit(f"Unsupported point format: {header.point_format} (need 7)")

    pattern_bins = load_pattern_bins(pattern_path, args.bin_deg)

    config_hints = None
    if config_path is not None and config_path.exists():
        config_hints = _load_config_hints(config_path)

    min_range_m = float(args.min_range) if args.min_range is not None else float((config_hints.min_range_m if config_hints else None) or 0.0)
    max_range_m = (
        float(args.max_range)
        if args.max_range is not None
        else (float(config_hints.max_range_m) if (config_hints and config_hints.max_range_m is not None) else None)
    )
    points = iter_points_format7(
        las_path,
        header,
        max_points=args.max_points,
        origin_xyz=(float(args.origin[0]), float(args.origin[1]), float(args.origin[2])),
    )
    stats = validate_points(
        points,
        pattern_bins,
        max_unmatched_examples=args.max_unmatched,
        min_range_m=min_range_m,
        max_range_m=max_range_m,
    )

    report = build_report(
        las_path=las_path,
        header=header,
        pattern_path=pattern_path,
        pattern_bins=pattern_bins,
        stats=stats,
        max_points=args.max_points,
        origin_xyz=(float(args.origin[0]), float(args.origin[1]), float(args.origin[2])),
        min_range_m=min_range_m,
        max_range_m=max_range_m,
        config_hints=config_hints,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
