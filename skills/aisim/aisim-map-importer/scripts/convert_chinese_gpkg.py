#!/usr/bin/env python3
"""
Convert Chinese-named GeoPackage layers to aiSim standard English layer names.

Usage:
    python3 convert_chinese_gpkg.py --input <chinese.gpkg> --output <standard.gpkg>
"""

import argparse
import sys
import os
from datetime import datetime

import geopandas as gpd
import fiona
import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, MultiLineString, MultiPolygon, mapping
from shapely.ops import unary_union
from pyproj import CRS


# ─── Layer name mapping: Chinese → aiSim English ──────────────────────────
LAYER_MAP = {
    "车道线": "RoadMarks",
    "人行横道": "Crosswalks",
    "禁停线": "RoadMarks",
}

# ─── Per-layer column defaults (merged into every row after remap) ────────
COLUMN_DEFAULTS = {
    "Paths": {
        "direction": "forward",
        "road_shape_id": 0,
    },
    "RoadMarks": {
        "color": "white",
        "material": "painted",
        "dash_length": 0.0,
        "space_length": 0.0,
        "metadata": "",
        "width": 0.2,
    },
    "Crosswalks": {
        "type": "outline",
        "color": "white",
        "source_id": -1,
    },
}

# ─── Per-layer column renames: Chinese column → aiSim column ──────────────
COLUMN_RENAME = {
    "车道线": {"Type": "type", "Width": "width"},
}

# ─── Layer-specific overrides (e.g. 禁停线 gets special type/color) ───────
LAYER_OVERRIDES = {
    "禁停线": {"type": "no_parking", "color": "yellow"},
}



def detect_chinese_layers(filepath: str) -> bool:
    """Return True if the GPKG contains any layer with Chinese characters."""
    layers = fiona.listlayers(filepath)
    for name in layers:
        for ch in name:
            if '一' <= ch <= '鿿':
                return True
    return False


def normalize_geometry(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Explode Multi* geometries into single-part rows.
    MultiLineString → multiple LineString rows
    MultiPolygon → multiple Polygon rows
    """
    geom_types = set()
    for g in gdf.geometry.dropna():
        geom_types.add(g.geom_type)

    needs_explode = any(
        gt.startswith("Multi") for gt in geom_types
    )
    if not needs_explode:
        return gdf

    # geopandas explode: splits multi-geom rows, re-indexes
    exploded = gdf.explode(index_parts=False)
    return exploded.reset_index(drop=True)


def load_and_remap(filepath: str, cn_name: str, en_name: str) -> gpd.GeoDataFrame | None:
    """Load a Chinese-named layer, normalize geometry, rename columns, add defaults."""
    gdf = gpd.read_file(filepath, layer=cn_name, driver="GPKG")

    if len(gdf) == 0:
        return None

    gdf = normalize_geometry(gdf)

    # Rename columns
    rename_map = COLUMN_RENAME.get(cn_name, {})
    gdf.rename(columns=rename_map, inplace=True)

    # Drop Chinese-only columns we don't need
    cols_to_keep = {"geometry"} | set(rename_map.values())
    drop_cols = [c for c in gdf.columns if c not in cols_to_keep]
    gdf.drop(columns=drop_cols, inplace=True)

    # Add ID column
    gdf.insert(0, "id", range(len(gdf)))

    # Apply defaults for missing columns
    defaults = COLUMN_DEFAULTS.get(en_name, {})
    for col, default_val in defaults.items():
        if col not in gdf.columns:
            gdf[col] = default_val

    # Apply layer-specific overrides
    overrides = LAYER_OVERRIDES.get(cn_name, {})
    for col, val in overrides.items():
        gdf[col] = val

    # Cast type columns to string (aiSim expects str)
    if "type" in gdf.columns:
        gdf["type"] = gdf["type"].astype(str)
    if "color" in gdf.columns:
        gdf["color"] = gdf["color"].astype(str)
    if "material" in gdf.columns:
        gdf["material"] = gdf["material"].astype(str)

    # For Paths: insert direction and road_shape_id right after id
    if en_name == "Paths":
        for col_name, default_val in [("direction", "forward"), ("road_shape_id", 0)]:
            if col_name not in gdf.columns:
                gdf[col_name] = default_val

    # Cast width to float
    if "width" in gdf.columns:
        gdf["width"] = gdf["width"].astype(float)

    return gdf


def generate_roadshapes(paths_gdf: gpd.GeoDataFrame,
                        lanelines_raw: gpd.GeoDataFrame | None = None) -> gpd.GeoDataFrame:
    """
    Generate RoadShapes polygons from Type=0 (solid) lane boundary lines.

    v3: Filters lane lines to only solid (Type=0) lines which represent actual
    road boundaries, merges segments on the same side, and builds a polygon
    from the two outermost continuous boundaries.
    """
    if lanelines_raw is None or len(lanelines_raw) == 0:
        return _generate_roadshapes_fallback(paths_gdf)

    # Filter to Type=0 (solid line = road boundary), exclude Type=1 (dashed = lane divider)
    if 'Type' in lanelines_raw.columns:
        solid = lanelines_raw[lanelines_raw['Type'] == 0]
    elif 'type' in lanelines_raw.columns:
        solid = lanelines_raw[lanelines_raw['type'].astype(str) == '0']
    else:
        solid = lanelines_raw

    if len(solid) == 0:
        return _generate_roadshapes_fallback(paths_gdf)

    # Flatten MultiLineString to individual LineStrings for merging
    lines = []
    for _, row in solid.iterrows():
        g = row.geometry
        if g is None or g.is_empty:
            continue
        if g.geom_type == 'MultiLineString':
            lines.extend(list(g.geoms))
        else:
            lines.append(g)

    if len(lines) < 2:
        return _generate_roadshapes_fallback(paths_gdf)

    # Merge nearby boundary segments into two continuous boundaries
    left_boundary, right_boundary = _build_boundary_pair(lines, paths_gdf)

    if left_boundary is None or right_boundary is None:
        return _generate_roadshapes_fallback(paths_gdf)

    # Build polygon from the two boundaries
    polygon = _polygon_from_boundary_pair(left_boundary, right_boundary)
    if polygon is None:
        return _generate_roadshapes_fallback(paths_gdf)

    # Split MultiPolygon into individual rows
    if polygon.geom_type == 'MultiPolygon':
        rows = [p for p in polygon.geoms if p.is_valid and not p.is_empty]
    elif polygon.is_valid and not polygon.is_empty:
        rows = [polygon]
    else:
        return _generate_roadshapes_fallback(paths_gdf)

    return gpd.GeoDataFrame({"geometry": rows}, crs=paths_gdf.crs)


def _generate_roadshapes_fallback(paths_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Fallback: buffer centerlines with fixed width when lane lines unavailable."""
    polygons = []
    for geom in paths_gdf.geometry:
        if geom is None or geom.is_empty:
            continue
        polygons.append(geom.buffer(1.75, cap_style=2))
    if not polygons:
        return gpd.GeoDataFrame(columns=["geometry"], crs=paths_gdf.crs)
    merged = unary_union(polygons)
    if merged.geom_type == "MultiPolygon":
        rows = list(merged.geoms)
    else:
        rows = [merged]
    return gpd.GeoDataFrame({"geometry": rows}, crs=paths_gdf.crs)


def _build_boundary_pair(lines: list, paths_gdf: gpd.GeoDataFrame):
    """
    Group solid boundary lines into left and right sides, merge each side
    into a single continuous boundary, return (left, right).
    """
    # Use the overall path direction to split lines into two groups
    all_paths = unary_union([g for g in paths_gdf.geometry if g is not None and not g.is_empty])

    # Classify each line as left or right relative to the overall path direction
    mid_pt = all_paths.interpolate(0.5, normalized=True)
    mid_dist = all_paths.project(mid_pt)
    eps = 1.0
    pa = all_paths.interpolate(max(0, mid_dist - eps))
    pb = all_paths.interpolate(min(all_paths.length, mid_dist + eps))
    direction = (pb.x - pa.x, pb.y - pa.y)

    left_group = []
    right_group = []

    for line in lines:
        if line.length < 1.0:  # skip tiny fragments
            continue
        near = line.interpolate(line.project(mid_pt))
        dx = near.x - mid_pt.x
        dy = near.y - mid_pt.y
        cross = direction[0] * dy - direction[1] * dx
        if cross > 0:
            left_group.append(line)
        else:
            right_group.append(line)

    if len(left_group) == 0 or len(right_group) == 0:
        return None, None

    left_merged = _merge_line_group(left_group)
    right_merged = _merge_line_group(right_group)

    # Orient both boundaries consistently: start near path start, end near path end
    first_path = all_paths.geoms[0] if all_paths.geom_type.startswith('Multi') else all_paths
    path_start = shapely.Point(first_path.coords[0])
    left_merged = _orient_forward(left_merged, path_start)
    right_merged = _orient_forward(right_merged, path_start)

    return left_merged, right_merged


def _orient_forward(line: shapely.LineString, ref_start: shapely.Point) -> shapely.LineString:
    """Reverse line if its start is closer to the reference end than to the reference start."""
    d_start_to_line_start = ref_start.distance(shapely.Point(line.coords[0]))
    d_start_to_line_end = ref_start.distance(shapely.Point(line.coords[-1]))
    if d_start_to_line_start > d_start_to_line_end:
        return shapely.LineString(reversed(line.coords))
    return line


def _merge_line_group(lines: list, merge_threshold: float = 5.0):
    """Merge LineStrings that belong to the same side, connecting endpoints that are nearby."""
    if len(lines) == 1:
        return lines[0]

    remaining = list(lines)

    while len(remaining) > 1:
        merged_any = False
        for i in range(len(remaining)):
            for j in range(i + 1, len(remaining)):
                a, b = remaining[i], remaining[j]
                d1 = shapely.distance(shapely.Point(a.coords[-1]), shapely.Point(b.coords[0]))
                d2 = shapely.distance(shapely.Point(a.coords[0]), shapely.Point(b.coords[-1]))

                if d1 < merge_threshold and d1 <= d2:
                    # a → b
                    combined = shapely.LineString(list(a.coords) + list(b.coords))
                    remaining.pop(j)
                    remaining.pop(i)
                    remaining.append(combined)
                    merged_any = True
                    break
                elif d2 < merge_threshold:
                    # b → a
                    combined = shapely.LineString(list(b.coords) + list(a.coords))
                    remaining.pop(j)
                    remaining.pop(i)
                    remaining.append(combined)
                    merged_any = True
                    break
            if merged_any:
                break
        if not merged_any:
            break

    if not remaining:
        return max(lines, key=lambda ll: ll.length)
    return max(remaining, key=lambda ll: ll.length)


def _polygon_from_boundary_pair(left_boundary, right_boundary):
    """Build a closed polygon from a pair of boundary lines."""
    try:
        ring_coords = []
        ring_coords.extend(left_boundary.coords)
        ring_coords.append(right_boundary.coords[-1])
        ring_coords.extend(reversed(right_boundary.coords))
        ring_coords.append(left_boundary.coords[0])

        poly = shapely.Polygon(ring_coords)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if poly.is_valid and not poly.is_empty else None
    except Exception:
        return None


def _derive_paths_and_roadshapes(centerlines_gdf: gpd.GeoDataFrame,
                                 lanelines_gdf: gpd.GeoDataFrame | None):
    """
    v4: Derive per-lane Paths and RoadShapes from center dividers and lane lines.
    The Chinese lane centerlines are center DIVIDERS between traffic directions.
    Generates one Path + one RoadShape per lane by evenly dividing the road.
    """
    if lanelines_gdf is None or len(lanelines_gdf) == 0:
        return None, None

    dividers = _merge_center_dividers(centerlines_gdf)
    if not dividers:
        return None, None

    main_divider = dividers[0]
    mid_pt = main_divider.interpolate(0.5, normalized=True)
    mid_dist = main_divider.project(mid_pt)
    eps = 1.0
    pa = main_divider.interpolate(max(0, mid_dist - eps))
    pb = main_divider.interpolate(min(main_divider.length, mid_dist + eps))
    direction = (pb.x - pa.x, pb.y - pa.y)

    # Collect solid edge lines and count dashed dividers on each side
    solid_left, solid_right = [], []
    dashed_left, dashed_right = 0, 0

    for _, row in lanelines_gdf.iterrows():
        g = row.geometry
        if g is None or g.is_empty:
            continue
        line_type = row.get('Type', 0)
        if g.geom_type == 'MultiLineString':
            g = max(g.geoms, key=lambda seg: seg.length)
        if g.length < 1.0:
            continue

        near = g.interpolate(g.project(mid_pt))
        dx, dy = near.x - mid_pt.x, near.y - mid_pt.y
        cross = direction[0] * dy - direction[1] * dx

        if line_type == 0:
            (solid_left if cross > 0 else solid_right).append(g)
        else:
            if cross > 0:
                dashed_left += 1
            else:
                dashed_right += 1

    if not solid_left or not solid_right:
        return None, None

    # Outermost solid = road edge
    left_edge = max(solid_left, key=lambda l: main_divider.distance(l))
    right_edge = max(solid_right, key=lambda l: main_divider.distance(l))

    # Lane count: 1 dashed divider → 2 lanes, 0 dashed → 1 lane
    n_left = 2 if dashed_left > 0 else 1
    n_right = 2 if dashed_right > 0 else 1

    all_paths, all_roadshapes = [], []
    crs = centerlines_gdf.crs

    for edge, n_lanes in [(left_edge, n_left), (right_edge, n_right)]:
        paths, shapes = _build_even_lanes(main_divider, edge, n_lanes)
        all_paths.extend(paths)
        all_roadshapes.extend(shapes)

    if not all_paths:
        return None, None

    # Pair Paths with RoadShapes 1:1
    n = min(len(all_paths), len(all_roadshapes))
    all_paths, all_roadshapes = all_paths[:n], all_roadshapes[:n]

    paths_gdf = gpd.GeoDataFrame(
        {"id": range(n), "direction": "forward",
         "road_shape_id": range(n), "geometry": all_paths},
        crs=crs,
    )
    roadshapes_gdf = gpd.GeoDataFrame({"geometry": all_roadshapes}, crs=crs)
    return paths_gdf, roadshapes_gdf


def _build_even_lanes(divider, outer_edge, n_lanes):
    """Build n evenly-spaced lanes between divider and outer road edge."""
    try:
        total_width = divider.distance(outer_edge)
        if total_width < 0.5:
            return [], []

        # Determine offset direction via signed distance
        sign = 1 if _signed_distance(divider, outer_edge) > 0 else -1

        paths, shapes = [], []
        for i in range(n_lanes):
            inner_frac = i / n_lanes
            outer_frac = (i + 1) / n_lanes

            inner_d = sign * total_width * inner_frac
            outer_d = sign * total_width * outer_frac

            inner_boundary = divider if abs(inner_d) < 0.01 else _offset_line(divider, inner_d)
            if inner_boundary is None:
                inner_boundary = _offset_line_fallback(divider, inner_d)
            outer_boundary = _offset_line(divider, outer_d)
            if outer_boundary is None:
                outer_boundary = _offset_line_fallback(divider, outer_d)
            if inner_boundary is None or outer_boundary is None:
                continue

            path = _offset_line(divider, sign * total_width * (inner_frac + outer_frac) / 2)
            if path is None:
                path = _offset_line_fallback(divider, sign * total_width * (inner_frac + outer_frac) / 2)
            if path is None:
                continue

            shape = _lane_polygon(inner_boundary, outer_boundary)
            if shape is not None:
                paths.append(path)
                shapes.append(shape)

        return paths, shapes
    except Exception:
        return [], []


def _lane_polygon(left_line, right_line):
    """Build a polygon between two boundary lines defining a lane."""
    try:
        ring = [tuple(c[:2]) for c in left_line.coords]
        ring.append(tuple(right_line.coords[-1][:2]))
        ring.extend(tuple(c[:2]) for c in reversed(right_line.coords))
        ring.append(tuple(left_line.coords[0][:2]))
        poly = shapely.Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if poly.is_valid and not poly.is_empty else None
    except Exception:
        return None


def _signed_distance(line, other_line):
    """Signed distance from line to other_line (positive = left of line direction)."""
    mid_pt = line.interpolate(0.5, normalized=True)
    proj_dist = line.project(mid_pt)
    eps = 0.5
    pa = line.interpolate(max(0, proj_dist - eps))
    pb = line.interpolate(min(line.length, proj_dist + eps))
    dx, dy = pb.x - pa.x, pb.y - pa.y
    length = (dx*dx + dy*dy) ** 0.5
    if length == 0:
        return 0
    nx, ny = -dy/length, dx/length  # left normal

    near = other_line.interpolate(other_line.project(mid_pt))
    return nx * (near.x - mid_pt.x) + ny * (near.y - mid_pt.y)


def _merge_center_dividers(centerlines_gdf: gpd.GeoDataFrame, proximity: float = 2.0):
    """Merge near-coincident centerlines into single divider reference lines."""
    geoms = [g for g in centerlines_gdf.geometry if g is not None and not g.is_empty]
    if not geoms:
        return []
    groups, used = [], set()
    for i, g1 in enumerate(geoms):
        if i in used: continue
        group = [g1]; used.add(i)
        for j, g2 in enumerate(geoms):
            if j in used: continue
            if g1.hausdorff_distance(g2) < proximity:
                group.append(g2); used.add(j)
        groups.append(group)
    return [max(g, key=lambda x: x.length) for g in groups]


def _offset_line_fallback(line, distance):
    """Fallback perpendicular offset using sampled points."""
    try:
        n = max(2, int(line.length / 2))
        pts = []
        for t in np.linspace(0, 1, n):
            pt = line.interpolate(t, normalized=True)
            proj_dist = line.project(pt)
            eps = 0.5
            pa = line.interpolate(max(0, proj_dist - eps))
            pb = line.interpolate(min(line.length, proj_dist + eps))
            dx, dy = pb.x - pa.x, pb.y - pa.y
            length = np.sqrt(dx*dx + dy*dy)
            if length == 0:
                continue
            nx, ny = -dy/length, dx/length
            z = pt.z if pt.has_z else 0
            pts.append(shapely.Point(pt.x + nx*distance, pt.y + ny*distance, z))
        if len(pts) < 2:
            return None
        return shapely.LineString(pts)
    except Exception:
        return None


def _offset_line(line, distance, side='left'):
    """Offset a LineString by a perpendicular distance."""
    try:
        offset = line.offset_curve(distance)
        if offset.geom_type == 'MultiLineString':
            offset = max(offset.geoms, key=lambda g: g.length)
        return offset
    except Exception:
        return _offset_line_fallback(line, distance)


def get_crs_proj4(filepath: str) -> str:
    """Extract a clean PROJ4 string from the input GPKG."""
    with fiona.open(filepath) as src:
        input_crs = src.crs
    try:
        crs_obj = CRS.from_user_input(input_crs)
        return crs_obj.to_proj4()
    except Exception:
        return "+proj=utm +zone=49 +datum=WGS84 +units=m +no_defs"


def get_target_crs(filepath: str):
    """Get a pyproj CRS object from the input GPKG."""
    proj4_str = get_crs_proj4(filepath)
    return CRS.from_proj4(proj4_str)


def generate_mapinfo(filepath: str, map_name: str) -> gpd.GeoDataFrame:
    """Synthesize a MapInfo metadata layer — Hamburg-style single-row wide table, no geometry."""
    proj4_str = get_crs_proj4(filepath)

    return gpd.GeoDataFrame(
        [{
            "id": 0,
            "aisim_version": "5.7.0",
            "road_model_version": "2.0.1",
            "roi": "Polygon",
            "source": f"CN_{map_name}",
            "creation_date_time": datetime.now().isoformat(),
            "projection_string": proj4_str,
        }],
        geometry=None,
    )


def convert(input_path: str, output_path: str, map_name: str | None = None):
    """Main conversion: Chinese GPKG → aiSim standard GPKG."""

    if not detect_chinese_layers(input_path):
        print("Warning: no Chinese layers detected, copying input as-is.")
        gdfs = {}
        for layer in fiona.listlayers(input_path):
            gdf = gpd.read_file(input_path, layer=layer, driver="GPKG")
            if len(gdf) > 0:
                gdfs[layer] = gdf
    else:
        # Derive map name from filename
        if map_name is None:
            map_name = os.path.splitext(os.path.basename(input_path))[0]

        gdfs = {}

        # Load raw Chinese layers for lane structure derivation
        raw_centerlines = None
        raw_lanelines = None
        try:
            raw_centerlines = gpd.read_file(input_path, layer='车道中心线', driver='GPKG')
        except Exception:
            pass
        try:
            raw_lanelines = gpd.read_file(input_path, layer='车道线', driver='GPKG')
        except Exception:
            pass

        for cn_name, en_name in LAYER_MAP.items():
            try:
                gdf = load_and_remap(input_path, cn_name, en_name)
            except Exception as e:
                print(f"Skipping layer '{cn_name}': {e}")
                continue

            if gdf is None:
                continue

            # Merge multiple sources into same target layer (e.g. 车道线 + 禁停线 → RoadMarks)
            if en_name in gdfs:
                gdfs[en_name] = gpd.GeoDataFrame(
                    gpd.pd.concat([gdfs[en_name], gdf], ignore_index=True),
                    crs=gdf.crs,
                )
            else:
                gdfs[en_name] = gdf

        # v4: Derive Paths and RoadShapes from center dividers + lane boundaries
        if raw_centerlines is not None and len(raw_centerlines) > 0:
            paths_gdf, roadshapes_gdf = _derive_paths_and_roadshapes(
                raw_centerlines, raw_lanelines
            )
            if paths_gdf is not None:
                gdfs["Paths"] = paths_gdf
            if roadshapes_gdf is not None:
                gdfs["RoadShapes"] = roadshapes_gdf

        if "Paths" not in gdfs:
            print("Warning: no Paths generated.")
            gdfs["Paths"] = gpd.GeoDataFrame(columns=["id", "direction", "road_shape_id", "geometry"])
        if "RoadShapes" not in gdfs:
            print("Warning: no RoadShapes generated.")
            gdfs["RoadShapes"] = gpd.GeoDataFrame(columns=["geometry"])

        # Generate MapInfo (Hamburg-style single-row wide table)
        gdfs["MapInfo"] = generate_mapinfo(input_path, map_name)

    # Write output GPKG using fiona directly
    target_crs = get_target_crs(input_path)
    _write_gpkg_layers(gdfs, output_path, target_crs)

    print(f"Conversion complete: {output_path}")
    print(f"Layers written: {list(gdfs.keys())}")
    for name, gdf in gdfs.items():
        print(f"  {name}: {len(gdf)} rows")


def _gdf_to_fiona_schema(gdf: gpd.GeoDataFrame) -> dict:
    """Build a fiona-compatible schema dict from a GeoDataFrame."""
    props = {}
    for col in gdf.columns:
        if col == "geometry":
            continue
        dtype = gdf[col].dtype
        if dtype == "int64" or dtype == "int32":
            props[col] = "int"
        elif dtype == "float64" or dtype == "float32":
            props[col] = "float"
        elif dtype == "bool":
            props[col] = "str"
        else:
            props[col] = "str"

    # Check if this layer has geometry
    geom_col = getattr(gdf, '_geometry_column_name', 'geometry')
    has_geom = geom_col is not None and geom_col in gdf.columns and gdf[geom_col].notna().any()

    if not has_geom:
        return {"geometry": None, "properties": props}

    geom_type = _dominant_geometry_type(gdf)
    return {"geometry": geom_type, "properties": props}


def _dominant_geometry_type(gdf: gpd.GeoDataFrame):
    """Return the dominant geometry type, or None if no geometries."""
    counts = {}
    for g in gdf.geometry.dropna():
        gt = g.geom_type
        counts[gt] = counts.get(gt, 0) + 1
    if not counts:
        return None
    return max(counts, key=counts.get)


def _normalize_layer_geometry(gdf: gpd.GeoDataFrame, target_type: str) -> gpd.GeoDataFrame:
    """Convert all geometries to the target type.
    LineString → Polygon: buffer with minimal width (0.001)
    Polygon → LineString: take exterior boundary
    """
    def convert(g):
        if g is None:
            return None
        gt = g.geom_type
        if gt == target_type:
            return g
        if target_type == "Polygon" and gt in ("LineString", "MultiLineString"):
            return g.buffer(0.001, cap_style=2)
        if target_type == "LineString" and gt in ("Polygon", "MultiPolygon"):
            return g.exterior
        # Fallback: return as-is, let fiona reject if invalid
        return g

    gdf = gdf.copy()
    gdf["geometry"] = gdf["geometry"].apply(convert)
    return gdf


def _write_gpkg_layers(gdfs: dict, output_path: str, crs):
    """Write all GeoDataFrames as layers to a GPKG file using fiona directly."""
    # Use pyproj CRS for fiona (handles EPSG codes)
    if hasattr(crs, 'to_proj4'):
        fiona_crs = crs.to_proj4()
    else:
        fiona_crs = crs

    for layer_name, gdf in gdfs.items():
        if len(gdf) == 0:
            print(f"Skipping empty layer: {layer_name}")
            continue

        schema = _gdf_to_fiona_schema(gdf)
        target_geom_type = schema["geometry"]

        # Normalize geometry to single type per layer (fiona requirement)
        if target_geom_type is not None:
            gdf = _normalize_layer_geometry(gdf, target_geom_type)

        # Build features
        features = []
        for _, row in gdf.iterrows():
            geom = row.get("geometry")
            if geom is not None and hasattr(geom, 'geom_type'):
                feat_geom = mapping(geom)
            else:
                feat_geom = None

            props = {}
            for col in gdf.columns:
                if col == "geometry":
                    continue
                val = row[col]
                if isinstance(val, (np.integer,)):
                    val = int(val)
                elif isinstance(val, (np.floating,)):
                    val = float(val)
                elif isinstance(val, np.bool_):
                    val = str(val)
                elif val is None:
                    val = ""
                elif schema["properties"].get(col) == "int":
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        val = str(val)
                elif schema["properties"].get(col) == "float":
                    try:
                        val = float(val)
                    except (ValueError, TypeError):
                        val = str(val)
                else:
                    val = str(val)
                props[col] = val

            features.append({"geometry": feat_geom, "properties": props})

        fiona_kwargs = dict(driver='GPKG', schema=schema)
        if schema["geometry"] is not None:
            fiona_kwargs["crs"] = fiona_crs

        with fiona.open(output_path, 'w', layer=layer_name, **fiona_kwargs) as dst:
            for feat in features:
                dst.write(feat)

        print(f"  Wrote layer '{layer_name}': {len(features)} rows")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Chinese-named GPKG to aiSim standard English GPKG (v2)"
    )
    parser.add_argument("--input", "-i", required=True, help="Input Chinese GPKG file")
    parser.add_argument("--output", "-o", required=True, help="Output aiSim-standard GPKG file")
    parser.add_argument("--map-name", type=str, default=None,
                        help="Map name (default: derived from input filename)")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}")
        sys.exit(1)

    convert(args.input, args.output, map_name=args.map_name)


if __name__ == "__main__":
    main()
