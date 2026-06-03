#!/usr/bin/env python3
"""Decode FVR30 radar object signals from the real BLF using project DBC files."""

from __future__ import annotations

import argparse
import csv
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

import can
import cantools

DBC_BY_RADAR = {
    "radar_front": ("FVR30_CANFD_F_V3.4.dbc", "FLR"),
    "radar_left_side": ("FVR30_CANFD_F_V3.4.dbc", "FrntSideRdrLe20Obj"),
    "radar_right_side": ("FVR30_CANFD_F_V3.4.dbc", "FrntSideRdrRi20Obj"),
}

FIELDS = ("timestamp", "radar", "object_index", "object_id", "dx", "dy", "vx", "vy", "confidence", "object_type", "motion_pattern")


def load_databases(zip_path: Path) -> dict[str, Any]:
    dbs = {}
    with zipfile.ZipFile(zip_path) as archive:
        for name, _ in set(DBC_BY_RADAR.values()):
            content = archive.read(name).decode("gb18030", errors="ignore")
            with tempfile.NamedTemporaryFile("w", suffix=".dbc", encoding="utf-8") as tmp:
                tmp.write(content)
                tmp.flush()
                dbs[name] = cantools.database.load_file(tmp.name, strict=False)
    return dbs


def decode_blf(blf: Path, dbs: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for msg in can.BLFReader(str(blf)):
        for radar, row in decode_message(msg, dbs):
            row["radar"] = radar
            rows.append(row)
    return rows


def decode_message(msg: Any, dbs: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    for radar, (dbc_name, prefix) in DBC_BY_RADAR.items():
        db = dbs[dbc_name]
        try:
            message = db.get_message_by_frame_id(msg.arbitration_id)
        except KeyError:
            continue
        decoded = message.decode(msg.data, decode_choices=False, scaling=True, allow_truncated=True)
        yield from objects_from_decoded(radar, prefix, float(msg.timestamp), decoded)


def objects_from_decoded(radar: str, prefix: str, timestamp: float, decoded: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    if prefix == "FLR":
        yield from flr_objects(timestamp, decoded)
        return
    indices = object_indices(prefix, decoded)
    for index in indices:
        row = make_object_row(prefix, index, timestamp, decoded)
        if row:
            yield radar, row


def flr_objects(timestamp: float, decoded: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    indices = sorted(
        {
            int(match.group(1))
            for key in decoded
            for match in [re.search(r"FLR_P[12]_(\d{2})_", key)]
            if match
        }
    )
    for index in indices:
        row = {
            "timestamp": timestamp,
            "object_index": index,
            "object_id": decoded.get(f"FLR_P1_{index:02d}_Obj_ID"),
            "dx": decoded.get(f"FLR_P2_{index:02d}_Obj_XPos"),
            "dy": decoded.get(f"FLR_P2_{index:02d}_Obj_YPos"),
            "vx": decoded.get(f"FLR_P2_{index:02d}_Obj_XVelAbs"),
            "vy": decoded.get(f"FLR_P2_{index:02d}_Obj_YVelAbs"),
            "confidence": decoded.get(f"FLR_P1_{index:02d}_Obj_ObstacleProb"),
            "object_type": None,
            "motion_pattern": decoded.get(f"FLR_P1_{index:02d}_Obj_MotionPattern"),
        }
        if is_nonempty(row):
            yield "radar_front", row


def object_indices(prefix: str, decoded: dict[str, Any]) -> list[int]:
    found = set()
    pattern = re.compile(re.escape(prefix) + r"_?(\d+)|" + re.escape(prefix) + r"(\d+)")
    for key in decoded:
        match = pattern.search(key)
        if match:
            found.add(int(next(group for group in match.groups() if group)))
    return sorted(found)


def make_object_row(prefix: str, index: int, timestamp: float, decoded: dict[str, Any]) -> dict[str, Any] | None:
    values = {
        "timestamp": timestamp,
        "object_index": index,
        "object_id": pick(decoded, prefix, index, ("Obj_ID", "RdrObjID")),
        "dx": pick(decoded, prefix, index, ("Obj_XPos", "RdrObjDx")),
        "dy": pick(decoded, prefix, index, ("Obj_YPos", "RdrObjDy")),
        "vx": pick(decoded, prefix, index, ("Obj_XVelAbs", "RdrObjVxAbs", "RelVx")),
        "vy": pick(decoded, prefix, index, ("Obj_YVelAbs", "RdrObjVyAbs", "RelVy")),
        "confidence": pick(decoded, prefix, index, ("RdrObjConf", "Obj_ObstacleProb", "ObstacleProb")),
        "object_type": pick(decoded, prefix, index, ("RdrObjTyp",)),
        "motion_pattern": pick(decoded, prefix, index, ("RdrObjMtnPat", "Obj_MotionPattern", "MotionPattern")),
    }
    if not is_nonempty(values):
        return None
    return values


def is_nonempty(row: dict[str, Any]) -> bool:
    keys = ("object_id", "dx", "dy", "vx", "vy", "confidence")
    values = [row.get(key) for key in keys]
    if all(value is None for value in values):
        return False
    return any(float(value) != 0.0 for value in values if value is not None)


def pick(decoded: dict[str, Any], prefix: str, index: int, suffixes: tuple[str, ...]) -> Any:
    candidates = [f"{prefix}_{index:02d}_{suffix}" for suffix in suffixes]
    candidates += [f"{prefix}{index}{suffix}" for suffix in suffixes]
    for key in candidates:
        if key in decoded:
            return decoded[key]
    return None


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field) for field in FIELDS})


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blf", type=Path, required=True)
    parser.add_argument("--dbc-zip", type=Path, default=Path("radar_dbc.zip"))
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] = sys.argv[1:]) -> int:
    args = parse_args(argv)
    rows = decode_blf(args.blf, load_databases(args.dbc_zip))
    if not rows:
        raise RuntimeError("No radar objects decoded from BLF")
    write_csv(args.output, rows)
    print(f"Wrote {args.output} with {len(rows)} radar object rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
