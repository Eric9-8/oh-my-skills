#!/usr/bin/env python3
"""
Generate gs3d.json for aiSim GS3D maps from PLY offset and GPKG projection.

Computes the geocentric→map transformation matrix (RT) and block center
from the PLY header offset and GPKG MapInfo projection string.

RT translation is placed at the GPKG map center (E, N) with altitude set to
the negative of the PLY ground-level z, so that the point cloud road surface
aligns with aiSim z=0 (the GPKG road plane).

Usage:
    python3 generate_gs3d_json.py --ply <file.ply> --gpkg <file.gpkg> \
        --output <gs3d.json> --map-name <name>
"""

import argparse
import json
import os
import re
import struct
import sys

import numpy as np


def parse_ply_offset(ply_path: str) -> tuple[float, float, float] | None:
    """Extract 'comment Offset: X Y Z' from PLY header."""
    with open(ply_path, 'rb') as f:
        header = b''
        while True:
            line = f.readline()
            header += line
            if line.rstrip(b'\r\n') == b'end_header' or not line:
                break
    text = header.decode('ascii', errors='replace')
    m = re.search(r'comment Offset:\s*([\d.eE+\-]+)\s+([\d.eE+\-]+)\s+([\d.eE+\-]+)', text)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None


def sample_ply_ground_z(ply_path: str, n_samples: int = 50000) -> float:
    """
    Estimate the ground-level z of a PLY point cloud by sampling vertices.

    Samples n_samples random vertices, sorts by z, and returns the mean of
    the p5~p15 range — low enough to capture road surface, high enough to
    exclude underground noise.

    Returns the estimated ground z in PLY local coordinates (typically negative,
    e.g. -4.71 for a road scene where the PLY origin is above the road).
    """
    import random

    with open(ply_path, 'rb') as f:
        header = b''
        while True:
            line = f.readline()
            header += line
            if line.rstrip(b'\r\n') == b'end_header' or not line:
                break
        header_len = len(header)
        m_count = re.search(rb'element vertex (\d+)', header)
        if not m_count:
            raise ValueError("Cannot find vertex count in PLY header")
        vertex_count = int(m_count.group(1))
        props = re.findall(rb'property \w+ (\w+)', header)
        vertex_size = len(props) * 4

        sample_indices = sorted(random.sample(range(vertex_count), min(n_samples, vertex_count)))
        zs = []
        for idx in sample_indices:
            f.seek(header_len + idx * vertex_size)
            data = f.read(12)
            _x, _y, z = struct.unpack_from('<fff', data)
            zs.append(z)

    zs.sort()
    n = len(zs)
    p5, p15 = int(0.05 * n), int(0.15 * n)
    ground_z = sum(zs[p5:p15]) / len(zs[p5:p15])
    return ground_z


def get_gpkg_map_center(gpkg_path: str) -> tuple[float, float]:
    """
    Compute the map center (E, N) from GPKG Paths layer bounds via fiona.
    """
    import fiona
    from shapely.geometry import shape

    xs, ys = [], []
    with fiona.open(gpkg_path, layer="Paths") as src:
        for feat in src:
            geom = shape(feat["geometry"])
            b = geom.bounds  # (minx, miny, maxx, maxy)
            xs += [b[0], b[2]]
            ys += [b[1], b[3]]
    if not xs:
        raise ValueError("Cannot determine map center: Paths layer is empty")
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def get_projection_string(gpkg_path: str) -> str:
    """Read ProjectionString from GPKG MapInfo table via fiona."""
    import fiona
    with fiona.open(gpkg_path, layer="MapInfo") as src:
        for feat in src:
            props = feat["properties"]
            if props.get("name") == "ProjectionString" and props.get("value"):
                return str(props["value"])
    raise ValueError("Cannot read ProjectionString from MapInfo")


def ecef_to_enu_matrix(lat_deg: float, lon_deg: float) -> np.ndarray:
    """Build East-North-Up rotation matrix at given geodetic coordinates."""
    lat, lon = np.deg2rad(lat_deg), np.deg2rad(lon_deg)
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    sin_lon, cos_lon = np.sin(lon), np.cos(lon)
    east  = np.array([-sin_lon, cos_lon, 0.0])
    north = np.array([-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat])
    up    = np.array([cos_lat * cos_lon,  cos_lat * sin_lon,  sin_lat])
    return np.vstack((east, north, up))


def generate_gs3d(ply_path: str, gpkg_path: str, map_name: str,
                  depth_test_offset: float = 3.0,
                  hpgs_offset_e: float | None = None,
                  hpgs_offset_n: float | None = None) -> dict:
    """Generate the gs3d.json data structure.

    hpgs_offset_e/n: HPGS capture origin in Gauss-Kruger (E, N). When provided,
    this is used as the RT translation origin instead of the GPKG map center.
    This is REQUIRED for HPGS-sourced PLY files — the PLY local (0,0,0) corresponds
    to the HPGS capture origin, not the GPKG map center.
    """
    from pyproj import CRS, Transformer

    proj_str = get_projection_string(gpkg_path)
    print(f"Projection: {proj_str}")

    # --- RT translation origin (E, N) ---
    #
    # RT translation maps PLY local (0,0,0) to ECEF. For HPGS PLY files,
    # local (0,0,0) = HPGS capture origin, so use --hpgs-offset-e/n.
    # Fallback to GPKG map center only when HPGS offset is not available
    # (e.g. standard PLY without HPGS metadata).
    #
    # RT alt = -ground_z ensures PLY road surface aligns with aiSim z=0.

    if hpgs_offset_e is not None and hpgs_offset_n is not None:
        center_e, center_n = hpgs_offset_e, hpgs_offset_n
        print(f"Using HPGS Offset: E={center_e:.4f}, N={center_n:.4f}")
    else:
        center_e, center_n = get_gpkg_map_center(gpkg_path)
        print(f"GPKG map center (fallback): E={center_e:.4f}, N={center_n:.4f}")

    print(f"Sampling PLY ground z (this may take a few seconds)...")
    ground_z = sample_ply_ground_z(ply_path)
    rt_alt = -ground_z
    print(f"PLY ground z (p5~p15 mean): {ground_z:.4f}m  →  RT alt = {rt_alt:.4f}m")

    # (E, N, rt_alt) → lon/lat → ECEF
    proj_crs = CRS.from_string(proj_str)
    to_wgs84 = Transformer.from_crs(proj_crs, CRS.from_epsg(4326), always_xy=True)
    lon, lat = to_wgs84.transform(center_e, center_n)

    geocent_crs = CRS.from_proj4("+proj=geocent +datum=WGS84 +units=m +no_defs")
    to_geocent = Transformer.from_crs(CRS.from_epsg(4979), geocent_crs, always_xy=True)
    cx, cy, cz = to_geocent.transform(lon, lat, rt_alt)
    print(f"Geodetic: lon={lon:.6f}°, lat={lat:.6f}°")
    print(f"Geocentric center: {cx:.6f}, {cy:.6f}, {cz:.6f}")

    # ENU basis at map center → RT rotation
    enu = ecef_to_enu_matrix(lat, lon)
    rt = np.eye(4)
    rt[:3, :3] = enu
    rt[3, :3] = [cx, cy, cz]

    ply_filename = os.path.basename(ply_path)
    gs3d = {
        "version": "1.0",
        "depth_test_offset": depth_test_offset,
        "blocks": {
            "0": {
                "RT": rt.reshape(-1).tolist(),
                "center": [cx, cy, cz],
                "scale": 1.0,
                "filename": f"asset://maps/{map_name}/GS3D/{ply_filename}",
                "proj-string": "+proj=geocent",
            }
        },
    }
    return gs3d


def main():
    parser = argparse.ArgumentParser(description="Generate gs3d.json for aiSim GS3D maps")
    parser.add_argument("--ply", required=True, help="Path to PLY point cloud file")
    parser.add_argument("--gpkg", required=True, help="Path to GPKG file with MapInfo")
    parser.add_argument("--output", "-o", required=True, help="Output gs3d.json path")
    parser.add_argument("--map-name", required=True, help="Map name for asset:// URI")
    parser.add_argument("--depth-offset", type=float, default=3.0,
                        help="Depth test offset (default: 3.0)")
    parser.add_argument("--hpgs-offset-e", type=float, default=None,
                        help="HPGS capture origin Easting (Gauss-Kruger). Use for HPGS PLY files.")
    parser.add_argument("--hpgs-offset-n", type=float, default=None,
                        help="HPGS capture origin Northing (Gauss-Kruger). Use for HPGS PLY files.")
    args = parser.parse_args()

    for path, name in [(args.ply, "PLY"), (args.gpkg, "GPKG")]:
        if not os.path.exists(path):
            print(f"Error: {name} file not found: {path}")
            sys.exit(1)

    gs3d = generate_gs3d(args.ply, args.gpkg, args.map_name, args.depth_offset,
                         hpgs_offset_e=args.hpgs_offset_e,
                         hpgs_offset_n=args.hpgs_offset_n)
    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump(gs3d, f, indent=2)
    print(f"gs3d.json written to: {args.output}")


if __name__ == "__main__":
    main()
