#!/usr/bin/env python3
"""Shared RadarService format helpers."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RADAR_TOPICS = {
    "radar_front": "/sensor/radar_front/obstacle_list",
    "radar_front_left": "/sensor/radar_front_left/obstacle_list",
    "radar_front_right": "/sensor/radar_front_right/obstacle_list",
    "radar_rear": "/sensor/radar_rear/obstacle_list",
    "radar_rear_left": "/sensor/radar_rear_left/obstacle_list",
    "radar_rear_right": "/sensor/radar_rear_right/obstacle_list",
}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    offset: int
    type_name: str
    source: str = ""


@dataclass(frozen=True)
class FormatSpec:
    payload_size: int
    cdr_header: bytes
    target_count: int
    target_stride: int
    targets_offset: int
    frame_ids: dict[str, str]
    radar_ids: dict[str, int]
    fields: tuple[FieldSpec, ...]
    version: int = 1


def load_format(path: Path) -> FormatSpec:
    if not path.exists():
        raise FileNotFoundError(f"Missing RadarService format spec: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    fields = tuple(
        FieldSpec(
            name=str(item["name"]),
            offset=int(item["offset"]),
            type_name=str(item["type"]),
            source=str(item.get("source", "")),
        )
        for item in raw.get("fields", [])
    )
    required = ("payload_size", "target_count", "target_stride", "targets_offset")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Format spec missing required keys: {missing}")
    return FormatSpec(
        payload_size=int(raw["payload_size"]),
        cdr_header=bytes.fromhex(str(raw.get("cdr_header_hex", "00010000"))),
        target_count=int(raw["target_count"]),
        target_stride=int(raw["target_stride"]),
        targets_offset=int(raw["targets_offset"]),
        frame_ids={str(k): str(v) for k, v in raw.get("frame_ids", {}).items()},
        radar_ids={str(k): int(v) for k, v in raw.get("radar_ids", {}).items()},
        fields=fields,
        version=int(raw.get("version", 1)),
    )


def pack_value(buffer: bytearray, offset: int, type_name: str, value: Any) -> None:
    formats = {
        "float32": "<f",
        "float64": "<d",
        "uint8": "<B",
        "int8": "<b",
        "uint16": "<H",
        "int16": "<h",
        "uint32": "<I",
        "int32": "<i",
    }
    if type_name not in formats:
        raise ValueError(f"Unsupported field type: {type_name}")
    numeric = float(value) if type_name.startswith("float") else int(float(value))
    struct.pack_into(formats[type_name], buffer, offset, numeric)


def unpack_value(data: bytes, offset: int, type_name: str) -> float | int:
    formats = {
        "float32": "<f",
        "float64": "<d",
        "uint8": "<B",
        "int8": "<b",
        "uint16": "<H",
        "int16": "<h",
        "uint32": "<I",
        "int32": "<i",
    }
    if type_name not in formats:
        raise ValueError(f"Unsupported field type: {type_name}")
    return struct.unpack_from(formats[type_name], data, offset)[0]


def write_string(buffer: bytearray, offset: int, value: str) -> None:
    encoded = value.encode("ascii") + b"\x00"
    struct.pack_into("<I", buffer, offset, len(encoded))
    start = offset + 4
    buffer[start : start + len(encoded)] = encoded


def read_cdr_string(data: bytes, offset: int) -> str:
    size = struct.unpack_from("<I", data, offset)[0]
    raw = data[offset + 4 : offset + 4 + size]
    return raw.rstrip(b"\x00").decode("ascii", errors="replace")
