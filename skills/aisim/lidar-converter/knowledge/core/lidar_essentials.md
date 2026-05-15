# aiSim LiDAR 核心规则（精简版）

> **说明:** 这是压缩的核心规则。完整文档见 `knowledge/reference/aisim_lidar_full.md`（仅供人工查阅）

## 1. LiDAR 类型判断

| 类型 | 识别特征 | 配置 type 字段 |
|------|----------|---------------|
| **Rotating** | 有 RPM、360° 水平覆盖、机械旋转 | `"type": "lidar"` |
| **Flash** | 有 frame_rate、固定 FOV (< 180°)、无旋转部件 | `"type": "lidar"` |

## 2. 配置文件结构

> **重要（本项目约定）**
>
> - Rotating/Flash 统一使用 `"type": "lidar"`，由 `lidar_config.rpm` vs `lidar_config.frame_rate` 区分。
> - 除 `type`、`update_intervals`、`mounting` 等传感器外层字段外，LiDAR 业务参数统一放在 `lidar_config` 内（包括 `max_stored_cycles` 与 `scanning_pattern_file`），避免平铺到 `lidar_sensor` 下。
> - `lidar_config.frame_rate` 输出为 **整数 Hz**（不要用 `10.0` 这类浮点）。

### Rotating LiDAR 最小配置
```json
{
  "sensors": {
    "lidar_sensor": {
      "type": "lidar",
      "update_intervals": [50000],
      "mounting": {"position": [1.0, 0.0, 3.0], "rotation": {...}},
      "lidar_config": {
        "max_stored_cycles": 2,
        "rpm": 1200,
        "laser_count": 64,
        "vertical_fov_min_deg": -25.0,
        "vertical_fov_max_deg": 15.0,
        "horizontal_resolution_deg": 0.2,
        "distance_min_meter": 0.3,
        "distance_max_meter": 200.0,
        "vertical_scanning_pattern_file": "calibrations://scanning_pattern/xxx_pattern.json"
      }
    }
  }
}
```

### Flash LiDAR 最小配置
```json
{
  "sensors": {
    "lidar_sensor": {
      "type": "lidar",
      "update_intervals": [40000],
      "mounting": {"position": [1.0, 0.0, 3.0], "rotation": {...}},
      "lidar_config": {
        "max_stored_cycles": 2,
        "frame_rate": 25,
        "horizontal_fov_deg": 80,
        "vertical_fov_deg": 30,
        "horizontal_resolution_deg": 0.2,
        "vertical_resolution_deg": 0.2,
        "distance_min_meter": 0.5,
        "distance_max_meter": 200.0,
        "scanning_pattern_file": "calibrations://scanning_pattern/xxx_pattern.json"
      }
    }
  }
}
```

## 3. 扫描模式 JSON

### Rotating: VerticalScanningPattern
```json
{
  "VerticalScanningPattern": [
    {"AzimuthOffsetDeg": 0.0, "ElevationDeg": -25.0, "Id": 0},
    {"AzimuthOffsetDeg": 0.0, "ElevationDeg": -24.0, "Id": 1},
    ...
  ]
}
```
- **数量:** 与 `laser_count` 一致
- **ElevationDeg 范围:** `vertical_fov_min_deg` ~ `vertical_fov_max_deg`

### Flash: ScanningPattern

**⚠️ 关键：Flash LiDAR 的 AzimuthDeg 语义（基于 ATX100 实测）**

对于 **1D 摆镜扫描的 Flash LiDAR**（如禾赛 ATX_100）：
- ✅ `AzimuthDeg` 表示每条 ray 的**最终绝对方位角**
- ✅ 计算公式：`AzimuthDeg = scan_az(TimeOffsetS) + channel_azimuth_offset`
- ✅ `ElevationDeg` 为通道固定俯仰角（来自手册附录）
- ✅ **通道水平偏移量必须写入 Pattern**（这是 LiDAR 的固有物理特性）
- ✅ **同一 TimeOffsetS 下，不同通道的 AzimuthDeg 应该不同**（差异 = 通道偏移差）
- ✅ `LaserId` 使用编码方案：`物理通道号 + (扫描序号 × 100)`
- ✅ **输出必须有序**：按 LaserId 从小到大排序
- ❌ 遗漏通道偏移会导致所有通道方位角相同（丢失通道间的水平分布）

**正确的生成逻辑**：
```python
scan_az = -horizontal_fov_deg / 2 + step * horizontal_resolution_deg
azimuth = scan_az + channel.azimuth_offset  # ✅ 扫描角 + 通道偏移
laser_id = physical_ch_id + step * 100      # ✅ 编码方案
# ✅ 最后对 lasers 列表排序
lasers.sort(key=lambda x: x["LaserId"])
```

**Pattern 结构（ATX100 实测）**：
```json
{
  "ScanningPattern": [{
    "Lasers": [
      {"TimeOffsetS": 0.010172, "AzimuthDeg": 59.4765625, "ElevationDeg": 6.82421875, "LaserId": 0},
      {"TimeOffsetS": 0.010172, "AzimuthDeg": 59.07421875, "ElevationDeg": 6.421875, "LaserId": 1},
      {"TimeOffsetS": 0.010272, "AzimuthDeg": 59.375, "ElevationDeg": 6.82421875, "LaserId": 100},
      ...
    ]
  }]
}
```

**关键验证点**：
- 同一 TimeOffsetS 下，通道 0 和通道 1 的 AzimuthDeg 差异 ≈ 0.40°（对应通道偏移差）
- LaserId 有序排列（0, 1, 2, ..., 99, 100, 101, ...）
- 通道偏移来自厂家手册附录（如 ATX100：±4.17°）
- **覆盖范围**：水平 ±(horizontal_fov_deg/2 + max_channel_offset)
- **时间跨度**：1/frame_rate 秒
- **JSON 格式**：纵向展开（indent=4），便于阅读

## 4. 关键计算公式

### update_intervals 计算
```python
# Rotating LiDAR
update_intervals = int(60_000_000 / rpm)  # 微秒

# Flash LiDAR
update_intervals = int(1_000_000 / frame_rate)  # 微秒
```

### 通道分布生成（均匀分布）
```python
# Rotating - 垂直方向均匀分布
fov_range = vertical_fov_max - vertical_fov_min
step = fov_range / (laser_count - 1)
elevations = [vertical_fov_min + i * step for i in range(laser_count)]

# Flash - 二维网格
h_steps = int(horizontal_fov / horizontal_resolution)
v_steps = int(vertical_fov / vertical_resolution)
# 生成 h_steps × v_steps 个采样点
```

## 5. 文件命名规范

```
输入: inputs/pandar64_manual.md

输出:
  - output/pandar64/pandar64_pattern.json     ← 扫描模式
  - output/pandar64/pandar64_config.json      ← 传感器配置

配置中引用:
  "scanning_pattern_file": "calibrations://scanning_pattern/pandar64_pattern.json"
  (必须与 pattern 文件名完全匹配)
```

## 6. 缺失参数处理

| 参数 | 处理策略 |
|------|----------|
| **必需但缺失** | 使用默认值 + 警告 |
| **可选且缺失** | 不填写该字段 |
| **通道分布缺失** | 生成均匀分布 + 标注 |

**示例警告信息:**
```
⚠️  参数缺失: distance_accuracy_meter
   → 使用默认值: 0.0
   → 建议: 查阅手册确认精度规格
```

## 7. 常见错误与修复

| 错误 | 原因 | 修复 |
|------|------|------|
| Pattern file not found | 文件名不匹配 | 检查 config 中的路径 |
| Invalid rpm value | RPM 超出范围 | 检查是否为 300-2400 |
| No point cloud output | update_intervals 错误 | 重新计算: 60000000/rpm |

---

**完整文档:** `knowledge/reference/aisim_lidar_full.md`
**参数映射:** `knowledge/core/parameter_mapping.yaml`
