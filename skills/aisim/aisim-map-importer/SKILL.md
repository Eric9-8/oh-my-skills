# aiSim Map Importer

Import Chinese-supplier or standard GPKG maps + PLY point clouds into aiSim via atlas_cmd_tool.
Also supports building a GPKG from scratch using OSM data from overpass-turbo.eu when no GPKG is available.

## Triggers

- "导入地图到 aiSim"
- "把这个地图转成 aiSim 格式"
- "import map to aiSim"
- "import this map"
- User provides GPKG + PLY file paths
- User has only a PLY / HPGS file and no GPKG (→ use OSM path below)

## Data Source Decision

| Situation | Path |
|-----------|------|
| GPKG already exists (Chinese layers) | Step 1 → convert Chinese GPKG |
| GPKG already exists (standard) | Skip Step 1, use as-is |
| No GPKG — manual QGIS workflow | **Step 0-manual: guided QGIS → validate** |
| No GPKG — only PLY / HPGS available | **Step 0: build GPKG from OSM** |

## Workflow

When invoked, ask the user for:

1. **GPKG file path** (required, or "none" to build from OSM)
2. **PLY file path** (optional) — 3D Gaussian Splatting point cloud
3. **Output asset directory** — where aiSim assets are stored
4. **Map name** — defaults to filename stem

Then execute:

### Step 0-manual: Manual QGIS Workflow (when OSM data is insufficient)

当OSM数据不可用或质量不足时，可以使用QGIS手动绘制路网。

#### 前提条件
- PLY点云文件
- CloudCompare导出的栅格底图（raster.tif）
- QGIS 3.x

#### 工作流程

**1. 准备工作环境**

```bash
# 创建QGIS工作目录
mkdir -p qgis_project
cd qgis_project

# 生成空白GeoPackage模板（使用临时GPS坐标）
/opt/aiMotive/atlas/atlas_python/bin/python3 \
  <project_root>/create_aisim_geopackage.py \
  --lat <temp_lat> --lon <temp_lon> \
  -o road_network.gpkg
```

**2. 在CloudCompare中导出栅格底图**

- 打开PLY点云
- Tools → Projection → Rasterize
- 分辨率设置：0.05-0.1米/像素
- 导出GeoTIFF格式（raster.tif）

**3. QGIS手动绘制**

```bash
qgis road_network.gpkg
```

- 加载raster.tif作为参考底图
- 绘制RoadShapes（道路表面多边形，优先级最高）
- 绘制RoadMarks（道路标线，填写color/type/width等属性）
- 可选：绘制Crosswalks、StopLines

绘制技巧：
- 放大到1:100～1:500比例尺
- 启用捕捉（顶点、线段、交叉点）
- 使用顶点工具(V键)调整形状
- 每绘制5-10个要素保存一次

**4. 坐标配准**

通过Google Earth确定场景GPS坐标：
- 观察栅格底图中的道路走向、交叉口形状
- 在Google Earth中搜索匹配的道路场景
- 记录场景中心点的GPS坐标

重新生成带GPS坐标的GeoPackage：

```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 \
  create_aisim_geopackage.py \
  --lat <real_lat> --lon <real_lon> \
  -o road_network_georef.gpkg

# 自动迁移手绘数据（复制粘贴所有要素到新GPKG）
# 或使用QGIS批量重投影工具
```

**5. 生成gs3d.json（关键步骤）**

⚠️ **重要警告**：必须使用GeoPackage中心的GPS坐标，而非投影原点！

```bash
# 第1步：计算GeoPackage中心的墨卡托坐标
ogrinfo -al -so road_network_georef.gpkg RoadShapes | grep Extent
# 输出示例：Extent: (-130016, -13344) - (-129979, -13137)

# 计算中心：
# E_center = (x_min + x_max) / 2
# N_center = (y_min + y_max) / 2

# 第2步：转换为GPS坐标
/opt/aiMotive/atlas/atlas_python/bin/python3 - <<'EOF'
from pyproj import CRS, Transformer

# 从GeoPackage读取的投影原点（在坐标配准时设置的）
proj_origin_lat = <投影原点纬度>
proj_origin_lon = <投影原点经度>

# 从Extent计算的GeoPackage中心（墨卡托坐标）
gpkg_center_e = <E_center>  # 替换为实际计算值
gpkg_center_n = <N_center>  # 替换为实际计算值

# 构建横轴墨卡托投影字符串
proj4 = f"+proj=tmerc +lat_0={proj_origin_lat} +lon_0={proj_origin_lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"

# 墨卡托 → WGS84
t = Transformer.from_crs(CRS.from_proj4(proj4), CRS.from_epsg(4326), always_xy=True)
lon_center, lat_center = t.transform(gpkg_center_e, gpkg_center_n)

print(f"GeoPackage中心GPS: {lat_center}°N, {lon_center}°E")
print(f"\n使用这些坐标生成gs3d.json:")
print(f"  --lat {lat_center}")
print(f"  --lon {lon_center}")
EOF

# 第3步：使用计算出的GPS坐标生成gs3d.json
/opt/aiMotive/atlas/atlas_python/bin/python3 \
  generate_gs3d_aligned.py \
  --ply point_cloud.ply \
  --output gs3d.json \
  --lat <lat_center> \
  --lon <lon_center>
```

**为什么必须使用GeoPackage中心GPS坐标？**

GeoPackage使用相对坐标系（横轴墨卡托投影），其数据中心可能距离投影原点很远（如130km）。如果直接使用投影原点生成gs3d.json，会导致PLY点云与GeoPackage路网严重偏移。

示例：
```
GeoPackage投影原点: (31.1256°N, 121.3611°E) → 墨卡托坐标 (0, 0)
GeoPackage中心: 墨卡托坐标 (-130km, -13km)
GeoPackage中心GPS: (30.9990°N, 120.0000°E)

如果使用投影原点 → PLY映射到 (31.1256°N, 121.3611°E)
而GeoPackage在 → (30.9990°N, 120.0000°E)
偏移距离 = 130.7 km ← 在RT_tool中完全看不到点云！
```

**6. 验证GPKG格式**

```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 -c "
import fiona
gpkg = 'road_network_georef.gpkg'
for layer in ['RoadMarks', 'RoadShapes']:
    with fiona.open(gpkg, layer=layer) as src:
        print(f'{layer}: {len(src)} features')
        if len(src) == 0:
            print(f'⚠️  {layer}图层为空！')
"
```

**验证通过后，设置 `STD_GPKG="$WORK_DIR/road_network_georef.gpkg"` 并继续到 Step 2。**

#### 常见问题

**Q1: 在RT_tool中点云与路网偏移130km？**
- **原因**：gs3d.json使用了投影原点，而GeoPackage中心距离投影原点130km
- **解决**：按上述第5步重新计算GeoPackage中心的GPS坐标，重新生成gs3d.json

**Q2: QGIS中绘制的路网要素太少？**
- 手动绘制GPKG是基础版本，重点是RoadShapes和关键RoadMarks
- 可以后续在QGIS中补充更多要素

**Q3: 需要哪些图层？**
- **必需**：RoadShapes（道路表面）
- **重要**：RoadMarks（道路标线，至少绘制主要车道线）
- **可选**：Crosswalks, StopLines, SidewalkShapes

#### 参考文档

详细的QGIS绘制指南请参考：
- `<project_root>/CloudCompare_QGIS完整操作指南.md`
- `<project_root>/QGIS绘制快速参考.txt`
- `<project_root>/坐标配准完整流程.md`

---

### Step 0: Build GPKG from OSM (only when no GPKG is available)

**Step 0a — Extract road data from Overpass Turbo**

First compute the WGS84 bbox from the PLY's actual world coordinate range.
Use the Gauss-Kruger bbox from Step 0b (PLY range + 20m margin), then convert
to WGS84 for the Overpass query. Add an extra ~200m buffer so Overpass returns
complete road segments that extend beyond the PLY boundary:

```bash
# Convert Gauss-Kruger bbox → WGS84 for Overpass
/opt/aiMotive/atlas/atlas_python/bin/python3 - <<'EOF'
from pyproj import CRS, Transformer
proj4 = "+proj=tmerc +lat_0=0 +lon_0=120 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
t = Transformer.from_crs(CRS.from_proj4(proj4), CRS.from_epsg(4326), always_xy=True)
# Use PLY bbox + 200m buffer for Overpass (wider than GPKG clip bbox)
corners = [(<minx>-200, <miny>-200), (<maxx>+200, <maxy>+200)]
lons, lats = zip(*[t.transform(e, n) for e, n in corners])
print(f"Overpass bbox: {min(lats):.6f},{min(lons):.6f},{max(lats):.6f},{max(lons):.6f}")
EOF
```

Go to https://overpass-turbo.eu and run the following query:

```
[out:json][bbox:<lat_min>,<lon_min>,<lat_max>,<lon_max>];
(
  way["highway"];
  way["highway"]["lanes"];
  relation["type"="restriction"];
);
out geom;
```

Export the result as **GeoJSON** (Export → GeoJSON). Save as `export.geojson`.

OSM data limitations to be aware of:
- Coordinates are road centre-lines only — no precise lane centre-lines
- No stop lines, crosswalks, or parking spaces
- No elevation (2D only)
- Lane count may be missing or inaccurate

**Step 0b — Convert GeoJSON to aiSim GPKG**

Compute the scene bounding box from the PLY's **actual world coordinate range**
(NOT a fixed ±500m square). Use the smallest PLY shard (e.g. `point_cloud_4.ply`)
to get the local coordinate range quickly, then add the HPGS Offset:

```bash
# Quick bbox calculation from PLY shard + HPGS Offset
/opt/aiMotive/atlas/atlas_python/bin/python3 - <<'EOF'
import struct, re
ply = "<path_to_point_cloud_4.ply>"
offset_e, offset_n = <E from transform_matrix.json>, <N from transform_matrix.json>
margin = 20.0
with open(ply,'rb') as f:
    h=b''
    while True:
        l=f.readline(); h+=l
        if l.rstrip(b'\r\n')==b'end_header': break
    vc=int(re.search(rb'element vertex (\d+)',h).group(1))
    vs=len(re.findall(rb'property \w+ \w+',h))*4
    data=f.read(vc*vs)
xs=[struct.unpack_from('<f',data,i*vs)[0] for i in range(vc)]
ys=[struct.unpack_from('<f',data,i*vs+4)[0] for i in range(vc)]
print(f"--bbox {offset_e+min(xs)-margin:.0f},{offset_n+min(ys)-margin:.0f},{offset_e+max(xs)+margin:.0f},{offset_n+max(ys)+margin:.0f}")
EOF
```

Then run the conversion with the computed bbox:

```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 \
    <skill_dir>/scripts/convert_geojson_gpkg.py \
    --input  export.geojson \
    --output "$WORK_DIR/${MAP_NAME}_std.gpkg" \
    --map-name "$MAP_NAME" \
    --proj4 "+proj=tmerc +lat_0=0 +lon_0=120 +k=1 +x_0=500000 +y_0=0 +ellps=GRS80 +units=m +no_defs" \
    --bbox  <minx>,<miny>,<maxx>,<maxy>
```

**IMPORTANT**: The bbox must match the PLY's actual world coordinate range.
Using a fixed ±500m square will include road segments far outside the PLY scene,
causing the GPKG map center to drift away from the HPGS capture origin and
producing a misaligned gs3d.json even after the HPGS offset fix.

The script builds three layers:
- **Paths** — one row per road centre-line segment, `direction=forward`
- **RoadShapes** — polygon buffer of each road (half-width by highway type)
- **MapInfo** — Budapest-style name/value rows including `ProjectionString`

Verify the output:
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 -c "
import fiona
gpkg = '$WORK_DIR/${MAP_NAME}_std.gpkg'
for t in ['Paths','RoadShapes','MapInfo']:
    with fiona.open(gpkg, layer=t) as src: print(t, len(src))
"
```

Set `STD_GPKG="$WORK_DIR/${MAP_NAME}_std.gpkg"` and continue from Step 2.

### Step 1: GPKG Conversion (skip if GPKG was built in Step 0)

Check if the GPKG contains Chinese-named layers:
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 -c "
import fiona; layers = fiona.listlayers('$GPKG_PATH')
has_cn = any('一' <= ch <= '鿿' for name in layers for ch in name)
print(has_cn)
"
```

If Chinese layers detected → convert:
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 \
    <skill_dir>/scripts/convert_chinese_gpkg.py \
    --input "$GPKG_PATH" \
    --output "$WORK_DIR/${MAP_NAME}_std.gpkg" \
    --map-name "$MAP_NAME"
```

If standard GPKG → use as-is, copy to work dir.

### Step 2: PLY Patching (if PLY provided)

**For HPGS PLY: always inject `comment Offset` (required for correct SH color in aiSim)**

aiSim's gaussian splatting shader computes view-dependent SH color using a camera
direction vector in PLY local space. The RT origin is the GPKG map center, but the
PLY local origin is the HPGS capture origin. Without `comment Offset`, aiSim cannot
shift the PLY into GPKG-center-relative space, causing the ENU basis mismatch that
makes the SH higher-order terms cancel the base color → grey point cloud.

Read the HPGS Offset from `transform_matrix.json` → `translation_vector`:
```bash
python3 -c "import json; d=json.load(open('transform_matrix.json')); print(d['translation_vector'])"
# → [E, N, H]
```

Inject the Offset comment (binary-safe, one-shot read):
```python
offset_line = b"comment Offset: <E> <N> <H>\n"
with open(src, "rb") as f:
    parts = []
    while True:
        line = f.readline()
        if line.rstrip(b"\r\n") == b"end_header":
            parts.append(offset_line)
            parts.append(line)
            break
        parts.append(line)
    vertex_data = f.read()          # one shot — never chunked
with open(dst, "wb") as f:
    for p in parts: f.write(p)
    f.write(vertex_data)
```

Verify: `file_size == header_len + vertex_count * vertex_size` (diff must be 0).

**SH coefficient check** (only needed if PLY was not produced by HPGS):
```bash
grep -c "f_rest_0" "$PLY_PATH"
```

If count = 0 → patch SH coefficients:
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 \
    <skill_dir>/scripts/patch_ply_sh.py \
    --input "$PLY_PATH" \
    --output "$WORK_DIR/${MAP_NAME}_sh3.ply"
```

**IMPORTANT — PLY header injection must be binary-safe:**
Never use text mode or chunked writes — Python's I/O buffer can append residual bytes
(typically 8192) after the declared vertex data, corrupting vertex coordinates from
~vertex 1000 onward and causing the scene to appear as a cylinder or distorted shape.

### Step 2.5: Patch atlas fixup.py (always required)

atlas's built-in `fixup.py` has a KeyError bug in `merge_paths` that causes
Paths=0 output whenever road paths have branches or merges. Patch it via
PYTHONPATH injection — no root access needed.

Create `$WORK_DIR/atlas_patch/geopackage/fixup.py` by copying
`/opt/aiMotive/atlas/importers/scripts/geopackage/fixup.py` and adding two
guard checks in `process_line`:

```python
# In the start_lines block:
if len(start_lines) == 1:
    adj_idx = start_lines[0]
    if adj_idx not in line_dict:   # ADD THIS GUARD
        return
    adj_line = line_dict[adj_idx]
    ...

# In the end_lines block:
if len(end_lines) == 1:
    adj_idx = end_lines[0]
    if adj_idx not in line_dict:   # ADD THIS GUARD
        return
    adj_line = line_dict[adj_idx]
    ...
```

Then prepend the patch directory to PYTHONPATH before running atlas:
```bash
export PYTHONPATH="$WORK_DIR/atlas_patch:$PYTHONPATH"
```

### Step 3: Generate gs3d.json (if PLY provided)

**For HPGS PLY: use HPGS Offset as RT origin** (pass `--hpgs-offset-e/n`):
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 \
    <skill_dir>/scripts/generate_gs3d_json.py \
    --ply "$PATCHED_PLY" \
    --gpkg "$STD_GPKG" \
    --output "$WORK_DIR/gs3d.json" \
    --map-name "$MAP_NAME" \
    --hpgs-offset-e <E from transform_matrix.json> \
    --hpgs-offset-n <N from transform_matrix.json>
```

The script computes RT translation as follows:

- **(E, N)**: HPGS capture origin from `transform_matrix.json` → `translation_vector`.
  The PLY local (0,0,0) corresponds to this origin, so RT must be placed here for
  correct spatial alignment. Do NOT use GPKG map center — it differs from the HPGS
  origin by 50–150 m and will cause the point cloud to appear offset in aiSim.
- **alt**: `-ground_z`, where `ground_z` is the PLY road surface z estimated by
  sampling 50 000 vertices and taking the p5~p15 mean

**NOTE — known grey color issue with large PLY files**: aiSim 5.11.0 renders the
point cloud grey when the PLY exceeds ~18M vertices (8.7 GB full cloud fails,
4.3 GB / 18.4 M vertices renders correctly). Use a lower-density shard
(e.g. `point_cloud_1.ply`) as the primary block until aiSim team resolves the limit.
See Known Issue #10.

Also create the GS3D directory next to gs3d.json and symlink the PLY into it
(atlas requires `GS3D/` to exist alongside gs3d.json):
```bash
mkdir -p "$WORK_DIR/GS3D"
ln -sf "$PATCHED_PLY" "$WORK_DIR/GS3D/$(basename $PATCHED_PLY)"
```

**Optional: add environment.ply as a second block**

HPGS captures sometimes include an `environment.ply` alongside the main point cloud
shards. This file contains sky/background Gaussians (identifiable by `"sky": N` in
the `comment meta` header line where N > 0) that extend the visual background beyond
the main scene boundary.

Check if it exists and whether the user wants it included:
```bash
ENV_PLY="$HPGS_DIR/PLY/point_cloud/iteration_10000/environment.ply"
if [ -f "$ENV_PLY" ]; then
    # inspect sky count from header
    head -c 2000 "$ENV_PLY" | grep -o '"sky":[0-9]*'
fi
```

If `sky > 0` and the user wants background rendering, add a second block to
`gs3d.json` **with the same RT matrix** (all HPGS shards share the same local
coordinate origin):
```json
{
  "version": "1.0",
  "depth_test_offset": 3.0,
  "blocks": {
    "0": { "RT": [...], "center": [...], "scale": 1.0,
           "filename": "asset://maps/<MAP_NAME>/GS3D/<main>.ply",
           "proj-string": "+proj=geocent" },
    "1": { "RT": [...], "center": [...], "scale": 1.0,
           "filename": "asset://maps/<MAP_NAME>/GS3D/environment.ply",
           "proj-string": "+proj=geocent" }
  }
}
```

Copy `environment.ply` to the GS3D deploy directory alongside the main PLY.
Effect is subtle (distant sky points); skip if the user does not need it.

### Step 4: Run atlas_cmd_tool

**IMPORTANT**: atlas_cmd_tool must be run from `/opt/aiMotive/atlas/` — it
resolves `atlas_python/bin/python3` as a relative path and will fail with
"Import to GeoPackage failed!" if run from any other directory.

```bash
cd /opt/aiMotive/atlas && \
PYTHONPATH="$WORK_DIR/atlas_patch:$PYTHONPATH" \
./tools/atlas_cmd_tool \
    -i "$STD_GPKG" \
    --gs3d_path "$WORK_DIR/gs3d.json" \
    -o "$OUTPUT_ASSET_DIR" \
    -r /opt/aiMotive/atlas \
    -a "$ATLAS_ASSET_PATH"
```

Check output for `Atlas_Status:successful`.

Verify the output GPKG has non-zero Paths:
```bash
/opt/aiMotive/atlas/atlas_python/bin/python3 -c "
import sqlite3
conn = sqlite3.connect('$OUTPUT_GPKG')
print('Paths:', conn.execute('SELECT COUNT(*) FROM Paths').fetchone()[0])
"
```

If Paths=0, the fixup.py patch was not applied — re-check PYTHONPATH.

### Step 5: Deploy

Copy atlas output to the aiSim asset directory with the correct map name
(atlas names the output after the GPKG filename stem, which may differ):

```bash
cp "$ATLAS_OUTPUT/GeoPackage/"*.gpkg \
   "$ASSET_DIR/maps/$MAP_NAME/GeoPackage/$MAP_NAME.gpkg"
cp "$WORK_DIR/gs3d.json" "$ASSET_DIR/maps/$MAP_NAME/gs3d.json"
mkdir -p "$ASSET_DIR/maps/$MAP_NAME/GS3D"
cp "$PATCHED_PLY" "$ASSET_DIR/maps/$MAP_NAME/GS3D/"

# If environment.ply was added as block 1:
# cp "$ENV_PLY" "$ASSET_DIR/maps/$MAP_NAME/GS3D/environment.ply"
```

### Step 6: Report

Summarize results:
- GPKG layers written (Paths count must be > 0)
- PLY patch status + file size diff (must be 0)
- gs3d.json center coordinates + RT alt value
- atlas_cmd_tool status

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/convert_geojson_gpkg.py` | Overpass GeoJSON → aiSim GPKG (Paths + RoadShapes + MapInfo) |
| `scripts/convert_chinese_gpkg.py` | Chinese GPKG → aiSim standard GPKG |
| `scripts/patch_ply_sh.py` | Add SH f_rest_* coefficients to PLY |
| `scripts/generate_gs3d_json.py` | Generate gs3d.json: GPKG map center + PLY ground-z alignment |

All scripts require `/opt/aiMotive/atlas/atlas_python/bin/python3`.

## Known Issues & Fixes

### 1. atlas_cmd_tool "Import to GeoPackage failed!"
**Cause**: Run from wrong directory — atlas uses relative path `atlas_python/bin/python3`.  
**Fix**: Always `cd /opt/aiMotive/atlas` before running `./tools/atlas_cmd_tool`.

### 2. atlas output Paths=0
**Cause**: `fixup.py` `merge_paths` KeyError — iterates `line_dict` while deleting keys,
then accesses a deleted `adj_idx` without checking.  
**Fix**: Step 2.5 PYTHONPATH patch. Affects all maps with branching/merging paths.

### 3. Point cloud displays as cylinder / distorted shape
**Cause**: PLY header injection script corrupted binary vertex data by appending
8192 bytes of I/O buffer residue after the declared vertices.  
**Fix**: Binary-safe one-shot read/write (see Step 2). Always verify `diff == 0`.

### 4. ego appears below point cloud road surface in aiSim
**Cause**: `generate_gs3d_json.py` used the PLY capture origin's absolute ellipsoidal
altitude (~19 m) as RT alt. `geocent_pose_to_map` passes this altitude directly as
the map z-coordinate, lifting the entire point cloud ~14 m above aiSim z=0.  
**Fix**: RT alt = `-ground_z` where `ground_z` is the PLY road surface z (p5~p15 mean
of sampled vertices). This is now the default behavior of `generate_gs3d_json.py`.

### 5. Point cloud horizontally offset from road (50–100 m)
**Cause**: RT translation (E,N) must equal the HPGS capture origin — NOT the GPKG map
center. The HPGS origin and GPKG center can differ by 50–150 m. Using GPKG center as
RT origin shifts the entire point cloud by that offset.  
**Fix**: Always pass `--hpgs-offset-e/n` to `generate_gs3d_json.py` with the values
from `transform_matrix.json` → `translation_vector`. The PLY local (0,0,0) corresponds
to the HPGS capture origin, so RT must be placed there.

### 6. Point cloud displays as grey / no color in aiSim (but correct in RT_tool)
**Cause**: Under investigation (Jira filed with aiSim team). Confirmed observations:
- RT_tool uses only f_dc (0th-order SH, view-independent) → always correct
- aiSim uses full 3rd-order SH (view-dependent) → grey on large PLY files
- Grey occurs when PLY exceeds ~18M vertices regardless of RT origin or comment Offset
- Switching free-fly view angle does not change the grey → not a view-direction issue
- `gs3d_color_sh_degree_limit=4294967295` (unlimited) → SH degree limit not the cause
- `libaimsimengine.so` contains `autoOffset`, `Offset,` strings → parses comment Offset,
  but injecting `comment Offset` alone did not fix the grey

**Current workaround**: Use a lower-density shard (≤18M vertices). See Known Issue #10.

### 7. atlas Python 缺少 `_sqlite3` 模块
**Cause**: atlas 自带的 Python 3.11 未编译 `_sqlite3` C 扩展，`import sqlite3` 会报 `ModuleNotFoundError: No module named '_sqlite3'`。  
**Fix**: 所有读写 GPKG 的操作改用 fiona（已在 `generate_gs3d_json.py` 和 `convert_geojson_gpkg.py` 中完成）。不要在这两个脚本中使用 sqlite3。

### 8. GPKG bbox 与 PLY 实际覆盖范围不匹配
**Cause**: 用固定 ±500m bbox 生成 GPKG，而 PLY 实际覆盖可能只有 300~400m，导致 GPKG 包含大量 PLY 范围外的路段，地图中心偏移。  
**Fix**: 用 PLY 局部坐标范围 + HPGS Offset 计算 PLY 世界坐标范围，加 20m 边距作为 GPKG 裁剪 bbox：
```python
bbox = (
    offset_e + xmin_local - 20,
    offset_n + ymin_local - 20,
    offset_e + xmax_local + 20,
    offset_n + ymax_local + 20,
)
```
PLY 坐标范围可从 point_cloud_4.ply（最小分片）快速获取，无需读取 9GB 完整文件。

### 9. OSM 数据质量限制
**Cause**: Overpass data has no lane-level geometry, no stop lines, no crosswalks.  
**Workaround**: `convert_geojson_gpkg.py` buffers centre-lines by highway-type half-width
to generate RoadShapes. For higher fidelity, supplement with manual annotation in QGIS
or replace with an HD map source.

### 10. 大顶点数 PLY 在 aiSim 5.11.0 中渲染为灰色
**Cause**: aiSim 5.11.0 的 GS3D 加载器存在顶点数量或文件大小上限（具体阈值待 aiSim 团队确认）。
已测试：18.4M 顶点 / 4.3 GB → 颜色正常；37.2M 顶点 / 8.7 GB → 渲染灰色。
所有分片 header 结构完全相同，排除 header 差异和 SH 计算问题。
`gs3d_color_sh_degree_limit=4294967295`（无限制），排除 SH 阶数限制。
**Workaround**: 使用次优分片（如 `point_cloud_1.ply`，18.4M 顶点）替代完整点云，
直到 aiSim 团队修复该限制。已提交 Jira 给 aiSim 团队排查。
**Threshold estimate**: 18.4M（正常）< 阈值 ≤ 37.2M，2^25（33.6M）是候选边界。

### 11. 手动绘制GPKG时PLY点云与路网严重偏移

**Cause**: gs3d.json的RT平移向量使用了横轴墨卡托投影原点的GPS坐标，
而GeoPackage中心距离投影原点可能有数十至数百公里。
当GeoPackage使用相对坐标系（坐标原点为(0,0)）时，场景实际位置可能
在投影原点的远处（如-130km, -13km），导致PLY映射到错误的位置。

**Symptoms**: 在RT_tool中，"地图固定到原点"视角下看不到PLY点云，
或PLY点云与GeoPackage路网相距数十至数百公里。

**Diagnosis**:
```
GeoPackage投影原点: (31.1256°N, 121.3611°E) → 墨卡托坐标 (0, 0)
GeoPackage中心: 墨卡托坐标 (-130km, -13km)
实际GPS坐标: (30.9990°N, 120.0000°E)

如果gs3d.json使用投影原点:
  PLY映射到 → (31.1256°N, 121.3611°E)
  GeoPackage在 → (30.9990°N, 120.0000°E)
  偏移 = 130.7 km
```

**Fix**: 计算GeoPackage中心的GPS坐标（而非投影原点），使用该坐标生成gs3d.json：

```bash
# 1. 从GeoPackage读取实际坐标范围
ogrinfo -al -so road_network.gpkg RoadShapes | grep Extent
# 输出：Extent: (x_min, y_min) - (x_max, y_max)

# 2. 计算中心（墨卡托坐标）
# gpkg_center_e = (x_min + x_max) / 2
# gpkg_center_n = (y_min + y_max) / 2

# 3. 墨卡托 → WGS84
/opt/aiMotive/atlas/atlas_python/bin/python3 - <<'EOF'
from pyproj import CRS, Transformer
proj_origin_lat = <投影原点纬度>
proj_origin_lon = <投影原点经度>
gpkg_center_e = <E_center>
gpkg_center_n = <N_center>

proj4 = f"+proj=tmerc +lat_0={proj_origin_lat} +lon_0={proj_origin_lon} +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
t = Transformer.from_crs(CRS.from_proj4(proj4), CRS.from_epsg(4326), always_xy=True)
lon_center, lat_center = t.transform(gpkg_center_e, gpkg_center_n)
print(f"{lat_center},{lon_center}")
EOF

# 4. 使用GeoPackage中心GPS坐标生成gs3d.json
generate_gs3d_aligned.py --lat <lat_center> --lon <lon_center>
```

**Verification**: 在RT_tool中重新加载地图，PLY点云应与GeoPackage路网完美重合。

## Example

User says: "把这个地图导入 aiSim" with:
- GPKG: `/data/GreenValley.gpkg`
- PLY: `/data/GreenValley.ply`
- Output: `/home/user/aisim-assets/maps`

Expected outcome: Standard GPKG (Paths > 0) + patched PLY (diff=0) + gs3d.json
with correct z-alignment written to output, atlas_cmd_tool reports success,
ego placed at z=0 sits on the point cloud road surface.

User says: "只有 PLY，没有 GPKG" with:
- PLY: `/data/ShuYingLu.ply`
- Scene bbox (WGS84): 31.120°N–31.122°N, 121.356°E–121.361°E

Expected outcome: Overpass GeoJSON → GPKG built via Step 0, then full pipeline runs.
