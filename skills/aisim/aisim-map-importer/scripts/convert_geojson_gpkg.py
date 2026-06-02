#!/usr/bin/env python3
"""
Convert Overpass Turbo GeoJSON export to aiSim-compatible GPKG.

Workflow:
  1. Read GeoJSON (WGS84) exported from overpass-turbo.eu
  2. Reproject to target Gauss-Kruger CRS (from GPKG MapInfo or --proj4)
  3. Clip to scene bounding box
  4. Build aiSim layers: Paths, RoadShapes, Connections, MapInfo
  5. Write to GPKG with Budapest-style MapInfo (name/value rows)

Usage:
    python3 convert_geojson_gpkg.py \
        --input  export.geojson \
        --output shuying_std.gpkg \
        --map-name ShuYingLu_Afternoon \
        --proj4 "+proj=tmerc +lat_0=0 +lon_0=120 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs" \
        --bbox  629200,3444950,629700,3445350

Overpass query to use on overpass-turbo.eu (adjust bbox to your scene):
    [out:json][bbox:<lat_min>,<lon_min>,<lat_max>,<lon_max>];
    (
      way["highway"];
      way["highway"]["lanes"];
      relation["type"="restriction"];
    );
    out geom;
"""

import argparse
import itertools
import os
import sys
from datetime import datetime

import fiona
import geopandas as gpd
import numpy as np
from pyproj import CRS, Transformer
from shapely.geometry import box, mapping, MultiLineString
from shapely.ops import unary_union


# Road half-widths by OSM highway type (metres, one side)
LANE_HALF_WIDTH = {
    "motorway":       7.0,
    "trunk":          6.0,
    "primary":        5.0,
    "secondary":      4.0,
    "tertiary":       3.5,
    "residential":    3.0,
    "service":        2.5,
    "unclassified":   3.0,
    "living_street":  2.5,
    "footway":        1.5,
    "cycleway":       1.5,
    "path":           1.5,
}
DEFAULT_HALF_WIDTH = 3.5


def half_width(highway_tag: str | None) -> float:
    if highway_tag is None:
        return DEFAULT_HALF_WIDTH
    return LANE_HALF_WIDTH.get(highway_tag, DEFAULT_HALF_WIDTH)


def read_geojson(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    return gdf


def reproject(gdf: gpd.GeoDataFrame, proj4: str) -> gpd.GeoDataFrame:
    target = CRS.from_proj4(proj4)
    return gdf.to_crs(target)


def clip_to_bbox(gdf: gpd.GeoDataFrame, bbox: tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = bbox
    scene_box = box(minx, miny, maxx, maxy)
    clipped = gdf[gdf.geometry.intersects(scene_box)].copy()
    clipped["geometry"] = clipped.geometry.intersection(scene_box)
    clipped = clipped[~clipped.geometry.is_empty].copy()
    return clipped


def build_paths(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Build Paths layer: one row per LineString segment, direction=forward."""
    rows = []
    pid = itertools.count(0)
    for _, feat in roads.iterrows():
        geom = feat.geometry
        lines = list(geom.geoms) if isinstance(geom, MultiLineString) else [geom]
        for line in lines:
            rows.append({
                "id": next(pid),
                "direction": "forward",
                "road_shape_id": -1,   # filled in after RoadShapes are built
                "geometry": line,
            })
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=roads.crs)


def build_road_shapes(roads: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Build RoadShapes layer: buffer each road centre-line by its half-width."""
    rows = []
    for rid, (_, feat) in enumerate(roads.iterrows()):
        hw = half_width(feat.get("highway"))
        poly = feat.geometry.buffer(hw, cap_style=2, join_style=2)
        rows.append({"id": rid, "geometry": poly})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=roads.crs)


def assign_road_shape_ids(paths: gpd.GeoDataFrame,
                          road_shapes: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Assign road_shape_id to each path by spatial join."""
    joined = gpd.sjoin(
        paths[["id", "geometry"]],
        road_shapes[["id", "geometry"]].rename(columns={"id": "rs_id"}),
        how="left",
        predicate="within",
    )
    id_map = joined.groupby("id")["rs_id"].first().to_dict()
    paths = paths.copy()
    paths["road_shape_id"] = paths["id"].map(id_map).fillna(-1).astype(int)
    return paths


def build_map_info(proj4: str, map_name: str) -> list[dict]:
    """Build Budapest-style MapInfo rows (name/value pairs)."""
    return [
        {"name": "aiSimVersion",       "value": "5.11.0"},
        {"name": "RoadModelVersion",   "value": "1.0.0"},
        {"name": "ProjectionString",   "value": proj4},
        {"name": "Source",             "value": f"OSM_{map_name}_{datetime.now().year}"},
        {"name": "TrafficWay",         "value": "RHT"},
        {"name": "ROI",                "value": "Polygon"},
        {"name": "CreationDateTime",   "value": datetime.now().isoformat(timespec="seconds")},
    ]


def write_gpkg(output_path: str,
               paths: gpd.GeoDataFrame,
               road_shapes: gpd.GeoDataFrame,
               map_info_rows: list[dict],
               crs: CRS) -> None:
    """Write all layers to GPKG."""
    # Geometry layers
    for layer_name, gdf in [("Paths", paths), ("RoadShapes", road_shapes)]:
        gdf.to_file(output_path, layer=layer_name, driver="GPKG")
        print(f"  {layer_name}: {len(gdf)} rows")

    # MapInfo: Budapest name/value style via geopandas (geometry column stays None/empty)
    map_info_gdf = gpd.GeoDataFrame(map_info_rows, geometry=gpd.GeoSeries([None] * len(map_info_rows)), crs=crs)
    map_info_gdf.to_file(output_path, layer="MapInfo", driver="GPKG")
    print(f"  MapInfo: {len(map_info_rows)} rows")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Overpass GeoJSON to aiSim GPKG"
    )
    parser.add_argument("--input",    "-i", required=True, help="Input GeoJSON path")
    parser.add_argument("--output",   "-o", required=True, help="Output GPKG path")
    parser.add_argument("--map-name", "-n", required=True, help="Map name (for MapInfo Source)")
    parser.add_argument(
        "--proj4",
        default="+proj=tmerc +lat_0=0 +lon_0=120 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs",
        help="Target CRS as PROJ4 string (default: CGCS2000 / 120° Gauss-Kruger)",
    )
    parser.add_argument(
        "--bbox",
        default=None,
        help="Clip bbox in target CRS: minx,miny,maxx,maxy (e.g. 629200,3444950,629700,3445350)",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    bbox = None
    if args.bbox:
        parts = [float(v) for v in args.bbox.split(",")]
        if len(parts) != 4:
            print("Error: --bbox must be minx,miny,maxx,maxy", file=sys.stderr)
            sys.exit(1)
        bbox = tuple(parts)

    print(f"Reading {args.input} ...")
    gdf = read_geojson(args.input)
    print(f"  {len(gdf)} features (CRS: {gdf.crs})")

    print(f"Reprojecting to {args.proj4} ...")
    gdf = reproject(gdf, args.proj4)

    if bbox:
        print(f"Clipping to bbox {bbox} ...")
        gdf = clip_to_bbox(gdf, bbox)
        print(f"  {len(gdf)} features after clip")

    # Filter to road ways only
    roads = gdf[gdf.get("highway", gpd.pd.Series(dtype=str)).notna()].copy()
    if len(roads) == 0:
        print("Warning: no 'highway' features found — check your GeoJSON", file=sys.stderr)

    print("Building layers ...")
    road_shapes = build_road_shapes(roads)
    paths = build_paths(roads)
    paths = assign_road_shape_ids(paths, road_shapes)
    map_info = build_map_info(args.proj4, args.map_name)

    out_dir = os.path.dirname(args.output)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    print(f"Writing {args.output} ...")
    write_gpkg(args.output, paths, road_shapes, map_info, CRS.from_proj4(args.proj4))
    print(f"Done: {args.output}")


if __name__ == "__main__":
    main()
