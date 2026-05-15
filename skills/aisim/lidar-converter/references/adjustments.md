# 调整记录（维护必读）

本文件只记录**会影响 Skill 行为/兼容性/上下文成本**的关键调整，用于后续维护与回归验证。

## 2026-01-04：Rotating LiDAR Pattern 格式修正 + aiSim 执行参数规范（关键 Bug 修复）

### 问题 1：Rotating LiDAR VerticalScanningPattern 格式不完整

**原始错误**：
- 生成的 `VerticalScanningPattern` 缺少 `FiringSequenceSize` 和 `FiringSequence` 字段
- aiSim 加载时报错或无法正确解析通道时序

**错误格式**：
```json
{
    "VerticalScanningPattern": [
        {"AzimuthOffsetDeg": -1.042, "ElevationDeg": 14.882, "Id": 0},
        ...
    ]
}
```

**正确格式**：
```json
{
    "FiringSequenceSize": 1,
    "VerticalScanningPattern": [
        {"FiringSequence": [0.0], "ElevationDeg": 14.882, "AzimuthOffsetDeg": -1.042},
        {"FiringSequence": [0.0], "ElevationDeg": 11.032, "AzimuthOffsetDeg": -1.042},
        ...
    ]
}
```

**修正要点**：
1. 必须在根级添加 `"FiringSequenceSize": 1`
2. 每个通道必须包含 `"FiringSequence": [0.0]` 数组
3. 字段顺序建议：`FiringSequence` → `ElevationDeg` → `AzimuthOffsetDeg`

### 问题 2：aiSim 导出必须使用步进仿真模式

**错误**：直接使用 `--export` 参数导出数据
```bash
aisim_client --export ...
# 报错：Export doesn't work with realtime simulation!
```

**正确**：必须添加 `--stepped` 参数启用步进仿真
```bash
aisim_client --stepped=10000 --world_update_interval=10000 --scenario_update_interval=10000 --export ...
```

### 问题 3：LiDAR 必须使用 Vulkan Raytrace Backend

**错误**：未指定 raytrace backend
```bash
aisim_client --export ...
# 报错：Lidar sensor requires VULKAN raytrace engine backend to function correctly
```

**正确**：必须添加 `--engine_raytrace_backend=vulkan`
```bash
aisim_client --engine_raytrace_backend=vulkan --export ...
```

### 问题 4：传感器 update_interval 必须是 world_update_interval 的整数倍

**错误**：传感器 `update_intervals: [100000]`（100ms），但 world_update_interval 默认 40000µs（40ms）
```
# 100000 不是 40000 的整数倍，报错
```

**正确**：设置 `--world_update_interval=10000`（10ms），使 100000 是其整数倍
```bash
aisim_client --world_update_interval=10000 --export ...
```

### 验证结果（Pandar_64）

| 指标 | 值 | 说明 |
|------|-----|------|
| 匹配率 | **99.91%** | 114549/114652 点匹配 |
| 通道覆盖率 | **100%** | 64/64 通道全部覆盖 |
| 未匹配点 | 103 | 均在 el=-4.050° 边界，属正常情况 |

### 影响范围

- **SKILL.md 更新**：添加 Rotating LiDAR 格式规范
- **aisim-executor SKILL.md 更新**：添加 aisim_client 必需参数说明
- **示例文件**：`output/Pandar_64/Pandar_64_pattern.json` 已按正确格式生成

### 教训

1. **Rotating LiDAR 与 Flash LiDAR 格式差异大**：
   - Rotating 使用 `VerticalScanningPattern` + `FiringSequenceSize` + `FiringSequence`
   - Flash 使用 `ScanningPattern` + `Lasers` + `TimeOffsetS`
2. **aiSim 导出有严格的参数要求**：必须同时满足 stepped 模式、raytrace backend、update_interval 整数倍
3. **验证脚本需区分 LiDAR 类型**：Rotating LiDAR 的 AzimuthOffset 是通道偏移，不是扫描范围

---

## 2025-12-30：Flash LiDAR pattern 生成逻辑修正（关键 Bug 修复）

> ⚠️ 注意：本节对 `AzimuthDeg` 的结论已在 **2026-01-04** 条目中更正（`AzimuthDeg` 为绝对方位角，应包含扫描角）。此处保留仅作历史记录。

### 问题描述

**原始错误逻辑**：
- 对于 1D 摆镜扫描的 Flash LiDAR，错误地将 `AzimuthDeg` 计算为：
  ```python
  azimuth = base_scan_angle + channel_offset  # ❌ 错误
  ```
- 导致：
  - 通道角度随时间变化（例如通道1从 -55.83° 变化到 64.07°）
  - 部分角度超出 FOV 范围（120°）
  - 生成的 pattern 不符合 aiSim 规范

### 修正方案

**正确的理解**：
- aiSim 的 Flash LiDAR `ScanningPattern` 中，`AzimuthDeg` 应该是**通道的固定偏移量**
- 摆镜的扫描运动由 aiSim 内部处理（通过 `TimeOffsetS` 和 `frame_rate`）
- 每个通道在整个周期中保持固定的水平角度

**修正后的逻辑**：
```python
# 对于每个通道，在所有时间步使用相同的偏移量
for step in range(time_steps):
    time_offset = step * time_per_step
    for channel in channels:
        lasers.append({
            "TimeOffsetS": time_offset,
            "AzimuthDeg": channel.offset,  # ✅ 固定偏移量，不变
            "ElevationDeg": channel.elevation,
            "LaserId": channel.id
        })
```

### 影响范围

- **示例文件**：`output/ATX_100/ATX_100_pattern.json` 已重新生成（修正后 35 MB）
- **文档更新**：
  - `knowledge/core/lidar_essentials.md` - 添加 Flash LiDAR AzimuthDeg 正确语义说明
  - `output/ATX_100/analysis_report.md` - 添加修正记录
- **备份**：错误版本保存为 `ATX_100_pattern_old_WRONG.json`（仅供参考）

### 验证结果

修正后的 pattern 完全符合手册规范：
- ✅ 通道1：周期0 = +4.17°，周期1 = +4.17°
- ✅ 通道65：周期0 = -3.49°，周期1 = +4.48°
- ✅ 所有通道的角度在整个周期中保持固定

### 教训

1. **仔细理解 aiSim 文档中的角度语义**
2. **对于 Flash LiDAR，区分两种角度表示**：
   - Rotating LiDAR 使用 `AzimuthOffsetDeg`（相对旋转轴的偏移）
   - Flash LiDAR 使用 `AzimuthDeg`（但对于摆镜型，是相对摆镜中心的固定偏移）
3. **从实际生成物验证角度范围**：如果出现超出 FOV 的角度，说明逻辑有误

---

## 2026-01-04：Flash LiDAR ScanningPattern 语义更正（AzimuthDeg 为绝对方位角）

### 背景

- **aiSim 文档定义**：`AzimuthDeg` / `ElevationDeg` “Sets the laser's azimuth/elevation angle”（绝对角），并且 scanning pattern 会覆盖 `LaserCount/HorizontalResolutionDeg/...` 等配置项。
- **对照实测（ATX_100）**：导出的 LAS 点云由 XYZ 反算的方位角范围与 pattern 中 `AzimuthDeg` 范围一致：
  - offset-only pattern（仅通道偏转）：方位角约 `±4.7°`
  - abs-az pattern（扫描角 + 通道偏转）：方位角约 `[-64.5°, +64.3°]`（120° + 偏转）

### 结论

对于 **1D 摆镜扫描的 Flash LiDAR**（ATX/AT 等）：
- ✅ `AzimuthDeg = scan_az(TimeOffsetS) + channel_offset`
- ✅ `TimeOffsetS` 仅表示 ray 的时间戳，不会“自动注入”摆镜扫描角
- ❌ 仅写 `AzimuthDeg = channel_offset` 会导致水平扫描范围丢失

### 修正方案

- **更新 lidar-converter 规则**：将 Flash（1D 摆镜）生成逻辑改为“扫描角 + 通道偏转”。
- **同步更新验证脚本**：报告中对照 pattern 的角度范围与 config 的 `horizontal_fov_deg`，便于快速识别 offset-only pattern。

### 影响范围

- 需要重新生成 ATX_100 这类 Flash（1D 摆镜）LiDAR 的 pattern/config；旧 pattern 会生成水平 FOV 极窄的点云。

---

## 2025-12-29：整理为标准 Codex Skill

- 将 Skill 收敛为标准目录：`lidar-converter/`（入口 `lidar-converter/SKILL.md`）。
- `SKILL.md` 标准化（frontmatter 仅保留 `name`/`description`），移除重复长文，改为按需引用 `knowledge/`。
- 清理旧的示例/脚本/模板/文档与无效符号链接，降低维护成本与上下文噪声。

## 2025-12-29：配置结构约束（lidar_config / max_stored_cycles）

- 强制使用嵌套结构：`sensors -> lidar_sensor -> lidar_config`，LiDAR 业务参数统一放入 `lidar_config`。
- 将 `max_stored_cycles` 也归入 `lidar_config`（与 `scanning_pattern_file` 同层），以匹配当前项目的配置 schema。

## 2025-12-29：类型与数值约束（type / frame_rate）

- Rotating/Flash 统一使用 `"type": "lidar"`，通过 `lidar_config.rpm` vs `lidar_config.frame_rate` 区分。
- `lidar_config.frame_rate` 输出为整数（Hz），避免 `10.0` 这类浮点格式导致 schema 校验失败。

## 2025-12-29：新增 LAS 点云一致性校验脚本

- 新增 `scripts/validate_las_pattern.py`：解析 LAS v1.4（Point Data Record Format 7），计算点的方位角/俯仰角，并与 `*_pattern.json` 的离散角度集合做匹配统计，用于快速发现 pattern/config 的明显偏差。
- 支持从 `*_config.json` 自动解析 pattern 引用与 `distance_min_meter/distance_max_meter`，并默认按距离过滤（可用参数覆盖），避免近距离噪声点干扰统计。

## 2025-12：Token 优化（v2.0-optimized）

- 将默认上下文从“完整参考”切换为 `knowledge/core/` 精简规则（减少 token 消耗，保持生成质量）。
- 保留 `knowledge/reference/aisim_lidar_full.md` 作为人工查阅资料，避免默认加载进 prompt。

## 兼容性约束（重要）

- `lidar-converter/SKILL.md` 中引用的相对路径必须与 `lidar-converter/knowledge/`、`lidar-converter/references/` 的结构保持一致；若移动目录，需要同步更新并做一次端到端验证。
- 生成文件命名/引用一致性是最常见失败点：`*_config.json` 内的 `scanning_pattern_file` 必须与 `*_pattern.json` 文件名严格一致。
