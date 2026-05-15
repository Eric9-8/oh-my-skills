---
name: lidar-converter
description: 将 LiDAR 产品手册（Markdown，Hesai/RoboSense 等）转换为 aiSim LiDAR 仿真配置（扫描模式 JSON + 传感器配置 JSON + 审核清单）。当用户提到 "aiSim / LiDAR / scanning pattern / 传感器配置 / 转换手册" 或需要 Rotating/Flash LiDAR 配置时使用。
---

# LiDAR Converter（aiSim）

## 变更记录

### 2026-02-02 - v1.4.0 Flash LiDAR Pattern 生成逻辑重大修正（基于 ATX100 实测）
- **修正 Flash LiDAR 通道偏移量处理**（关键修正）
  - ❌ **之前错误理解**：通道水平偏移量不应写入 Pattern，应由角度修正文件处理
  - ✅ **正确理解**：通道水平偏移量**必须写入 Pattern 的 AzimuthDeg**
  - ✅ **验证依据**：ATX100 实测 JSON 中，同一 TimeOffsetS 下不同通道的 AzimuthDeg 不同（差异 = 通道偏移差）
  - ✅ **公式修正**：`AzimuthDeg = scan_az(TimeOffsetS) + channel_azimuth_offset`
- **更新 LaserId 编码与排序规范**
  - ✅ 编码方案：`LaserId = 物理通道号 + (扫描序号 × 100)`
  - ✅ 输出要求：按 LaserId 从小到大排序（便于阅读和调试）
  - ✅ 优点：可从 LaserId 反推通道号（`% 100`）和扫描序号（`// 100`）
- **更新 JSON 格式规范**
  - ✅ 必须使用纵向格式（`indent=4`），不要单行压缩
  - ✅ 确保可读性，便于人工审核和调试
- **更新文档**
  - ✅ 更新 `flash_lidar_pattern_template.md`：修正通道偏移量处理说明和代码示例
  - ✅ 更新 `lidar_essentials.md`：修正 Flash LiDAR 核心规则
  - ✅ 更新 `SKILL.md`：修正生成逻辑和验证标准
  - ✅ 添加 ATX100 实测验证点和代码示例

### 2026-01-04 - v1.3.0 两层验证体系
- **新增 channel_data.py 生成规范**
  - 从手册附录提取通道角度数据
  - 用于第一层验证（手册 → Pattern）
- **新增 validate_pattern_channel.py 验证脚本**
  - 验证 Pattern 与 channel_data 的一致性
  - 支持 .py 和 .csv 格式的 channel_data
- **完善两层验证体系文档**
  - 第一层：手册 → Pattern（validate_pattern_channel.py）
  - 第二层：Pattern → LAS（validate_las_pattern.py）

### 2026-01-04 - v1.2.2 Flash LiDAR ScanningPattern 语义更正（绝对方位角）
- **更正 Flash LiDAR `ScanningPattern` 的 `AzimuthDeg` 语义**（关键修正）
  - ✅ 正确：`AzimuthDeg = scan_az(TimeOffsetS) + 通道水平偏转`
  - ❌ 错误：`AzimuthDeg = 通道水平偏转`（会导致水平扫描范围丢失，导出点云方位角塌缩到 ±几度）
- **原因**：
  - aiSim 文档定义 `AzimuthDeg` 为 laser 的方位角（绝对角）
  - 实测导出的 LAS 方位角范围与 pattern 中 `AzimuthDeg` 范围一致 ⇒ 扫描角必须由 pattern 显式给出

### 2026-01-04 - v1.2.1 Rotating LiDAR Pattern 格式修正 + aiSim 执行参数规范
- **修正 Rotating LiDAR VerticalScanningPattern 格式**（关键 Bug）
  - ❌ 错误：缺少 `FiringSequenceSize` 和 `FiringSequence` 字段
  - ✅ 正确：必须包含 `FiringSequenceSize: 1` 和每个通道的 `FiringSequence: [0.0]`
- **Pandar_64 验证结果**
  - 匹配率 **99.91%**，通道覆盖率 **64/64 (100%)**
  - 通过完整的 LAS 点云闭环验证
- **更新验证脚本** `validate_las_pattern.py`
  - 区分 Rotating/Flash LiDAR 的角度范围显示
  - Rotating LiDAR 显示"通道偏移范围"而非"角度范围（期望）"
- **记录 aiSim 执行必需参数**（见 aisim-executor SKILL.md）
  - `--stepped=10000`：导出必须使用步进仿真模式
  - `--engine_raytrace_backend=vulkan`：LiDAR 必须使用 Vulkan 光线追踪
  - `--world_update_interval=10000`：确保传感器 update_interval 是其整数倍

### 2026-01-04 - v1.2.0 验证增强与文档完善
- **新增完整 LAS 验证脚本** `validate_las_full.py`
  - 验证 LAS 点云与 Pattern 文件的角度匹配
  - 验证 LAS 点云与手册 ROI/分辨率规格的一致性
  - 生成详细的规格差异分析报告
- **更新验证报告** `LAS_VALIDATION_REPORT.md`
  - 添加俯仰角范围差异分析（+6.98° vs +7°）
  - 添加非ROI下部分辨率差异分析（0.525° vs 0.4°）
  - 明确说明差异原因和影响评估
- **整理文件结构**
  - 归档历史文件到 `archive/` 目录
  - 保留必要的验证脚本和报告

### 2025-12-30 - v1.1.0 Flash LiDAR Pattern 修正
- **修正 Flash LiDAR AzimuthDeg 计算逻辑**（关键 Bug）
  - ❌ 错误：`AzimuthDeg = 扫描位置 + 通道偏移量`
  - ✅ 正确（已在 v1.2.2 更正）：`AzimuthDeg = scan_az(TimeOffsetS) + 通道偏移量`
- **ATX_100 验证结果**
  - 匹配率从 67.64% 提升到 **100%**
  - 通过完整的 LAS 点云闭环验证

### 2025-12-29 - v1.0.0 初始版本
- 初始化 lidar-converter Skill
- 支持 Rotating 和 Flash LiDAR 配置生成

---

## 快速使用

用户提示示例（安装该 Skill 后直接触发）：

```bash
请使用 lidar-converter：把 "inputs/<lidar>_manual.md" 转换为 aiSim 配置，输出到 "output/<lidar_name>/"，并生成复核清单。
```

如需固定输出目录或 LiDAR 类型，请在提示中明确写出（例如 “按 rotating 处理” / “输出到 …”）。

## 任务目标与输出物

对给定手册生成并写入 `output/<lidar_name>/`：
- `analysis_report.md`：提取结果、缺失项、默认值/推断项说明
- `channel_data.py`：**通道角度数据**（从手册附录提取，用于第一层验证）
- `<LidarName>_pattern.json`：扫描模式（Rotating=VerticalScanningPattern；Flash=ScanningPattern）
- `<LidarName>_config.json`：传感器配置（必须包含 `lidar_config`；`lidar_config.scanning_pattern_file` 必须与 pattern 文件名一致）
- `review_checklist.md`：人工复核清单（重点列出不确定/默认/均匀分布项）

### channel_data.py 格式规范

从手册附录提取通道角度数据，用于验证 Pattern 生成的正确性：

```python
# <LidarName> LiDAR 通道配置数据
# 来源: input/Lidar/<lidar>_manual.md 附录 A
# 每个元组格式: (通道序号, 偶数帧水平偏移°, 奇数帧水平偏移°, 垂直高度角°)
# 注: 如果偶数帧/奇数帧偏移相同，两列填相同值

CHANNEL_DATA = [
    (1, 4.17, 4.17, 6.98),
    (2, 3.81, 3.81, 6.58),
    # ... 所有通道
]

# 总计: N 个通道
```

**关键要求**：
- 必须从手册附录的通道分布表中提取
- 保持与手册中的通道编号一致
- 角度值保留手册中的精度（通常 2 位小数）

## 执行流程（面向 Agent）

1. 读取用户提供的手册 Markdown（用户给出文件路径或直接粘贴内容）。
2. 自动判断类型：包含 RPM/转速/rotating → Rotating；包含 frame rate/帧率/flash/MEMS → Flash（本项目两类 `type` 都是 `"lidar"`，由 `lidar_config.rpm` vs `lidar_config.frame_rate` 区分）。
3. 按 `knowledge/core/lidar_quick_ref.md` 提取必需参数；缺失则使用默认值并在 `analysis_report.md`/`review_checklist.md` 明确标注。
4. 计算更新间隔：
   - Rotating：`update_intervals = int(60_000_000 / rpm)`（µs）
   - Flash：`update_intervals = int(1_000_000 / frame_rate)`（µs，且 `frame_rate` 输出为整数）
5. 生成扫描模式 JSON（**严格遵循以下规则**）：

   **⚠️ Flash LiDAR 关键规则（1D 摆镜扫描，如 Hesai ATX/AT 系列）**：

   aiSim 的 `ScanningPattern` 中 `AzimuthDeg/ElevationDeg` 表示每条 ray 的**最终空间方向（绝对角）**。对于 1D 摆镜扫描 Flash LiDAR，需要把**扫描角（随时间）+ 通道水平偏移（固定）**写入 `AzimuthDeg`。

   - **`AzimuthDeg` = scan_az(TimeOffsetS) + channel_azimuth_offset**
   - **通道水平偏移量**：来自手册附录的「水平方位角偏移量」（如 ATX100：±4.17°）
     - ✅ **必须写入 Pattern 文件**（这是 LiDAR 的固有物理特性）
     - ✅ 同一 TimeOffsetS 下，不同通道的 AzimuthDeg 应该不同（差异 = 通道偏移差）
   - **`ElevationDeg`**：直接使用通道的俯仰角（来自手册附录）
   - **`TimeOffsetS`**：按扫描顺序递增（用于时序控制）
     - ⚠️ **多周期时，每个周期的 TimeOffsetS 必须从上一周期结束后开始**
     - 周期 N 的起始时间 = `N * frame_duration`
   - **`LaserId`**：使用编码方案 `物理通道号 + (扫描序号 × 100)`
     - ✅ 便于调试：`LaserId % 100` = 物理通道号，`LaserId // 100` = 扫描序号
     - ✅ 支持奇偶帧区分

   **✅ 正确的生成逻辑（基于 ATX100 实测）**：
   ```python
   # ✅ 正确：AzimuthDeg = 扫描角 + 通道偏移，TimeOffsetS 跨周期递增，LaserId 有序输出
   h_fov_min, h_fov_max = -60.0, 60.0  # 水平 FOV（度）
   h_resolution = 0.1  # 水平分辨率（度）
   h_steps = int((h_fov_max - h_fov_min) / h_resolution)  # 1200 步

   frame_duration = 1.0 / frame_rate  # 帧周期（秒）
   time_per_step = frame_duration / h_steps  # 每步时间

   cycles = []
   for cycle_idx in range(num_cycles):  # 通常 2 个周期（偶数帧/奇数帧）
       lasers = []

       # ⚠️ 关键：周期 N 的时间从 N * frame_duration 开始
       cycle_time_offset = cycle_idx * frame_duration

       for step in range(h_steps):
           scan_az = h_fov_min + step * h_resolution
           time_offset = cycle_time_offset + step * time_per_step

           for physical_ch_id, ch in enumerate(channels):
               # ✅ LaserId 编码：物理通道号 + (扫描序号 × 100)
               laser_id = physical_ch_id + step * 100

               laser = {
                   "TimeOffsetS": time_offset,
                   "AzimuthDeg": scan_az + ch.azimuth_offset,  # ✅ 扫描角 + 通道偏移
                   "ElevationDeg": ch.elevation,
                   "LaserId": laser_id
               }
               lasers.append(laser)

       # ✅ 按 LaserId 排序，确保输出有序（便于阅读和调试）
       lasers.sort(key=lambda x: x["LaserId"])
       cycles.append({"Lasers": lasers})
   ```

   **❌ 错误的生成逻辑（已废弃）**：
   ```python
   # ❌ 错误1：遗漏通道偏移，导致所有通道方位角相同
   "AzimuthDeg": scan_az  # 错误！同一时刻所有通道方位角都相同

   # ❌ 错误2：多周期时 TimeOffsetS 不能都从 0 开始！
   # 周期0: TimeOffsetS 0.0 ~ 0.1s
   # 周期1: TimeOffsetS 0.0 ~ 0.1s  ← 错误！应该是 0.1 ~ 0.2s

   # ❌ 错误3：LaserId 简单递增，不便于调试
   laser_id = 0
   for step in range(h_steps):
       for ch in channels:
           lasers.append({"LaserId": laser_id, ...})
           laser_id += 1  # 无法反推通道号和扫描序号

   # ❌ 错误4：输出无序，不便于阅读
   # 未对 lasers 列表排序，导致 LaserId 乱序
   ```

   **生成后验证（基于 ATX100 实测标准）**：
   - `AzimuthDeg` 范围应接近水平 FOV + 通道偏移范围
     - 例如 ATX100：扫描角 -60° ~ +60°，通道偏移 ±4.17°，总范围约 -64.17° ~ +64.17°
   - **同一 TimeOffsetS 下，不同通道的 AzimuthDeg 应该不同**（差异 = 通道偏移差）
     - 例如 ATX100：通道 0 和通道 1 的偏移差 ≈ 0.36°（4.17° - 3.81°）
   - 总点数 = `h_steps × 通道数`（如 ATX100：1200 × 100 = 120,000 点/周期）
   - **多周期时，周期 N 的 TimeOffsetS 范围应为 `[N*T, (N+1)*T)`**
   - **LaserId 应有序排列**（从小到大），便于阅读和调试
   - **JSON 格式应纵向展开**（indent=4），不要单行压缩

   **⚠️ Rotating LiDAR 关键规则（机械旋转式，如 Hesai Pandar 系列）**：

   Rotating LiDAR 使用 `VerticalScanningPattern` 格式，**必须包含 `FiringSequenceSize` 和 `FiringSequence` 字段**。

   - **`FiringSequenceSize`**：固定为 `1`
   - **`FiringSequence`**：时间偏移数组，通常为 `[0.0]`
   - **`ElevationDeg`**：通道的垂直角度（来自手册附录）
   - **`AzimuthOffsetDeg`**：通道的水平偏移量（来自手册附录）

   **✅ 正确的 VerticalScanningPattern 格式**：
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

   **❌ 错误的格式（缺少必需字段）**：
   ```json
   {
       "VerticalScanningPattern": [
           {"AzimuthOffsetDeg": -1.042, "ElevationDeg": 14.882, "Id": 0},
           ...
       ]
   }
   ```

   **生成后验证**：
   - 必须包含 `FiringSequenceSize` 字段
   - 每个通道必须包含 `FiringSequence` 数组
   - 通道数应与手册一致（如 Pandar64：64 个通道）
   - `ElevationDeg` 范围应与手册垂直 FOV 一致

6. 生成传感器配置 JSON（模板见 `knowledge/sample_structure.md`）：LiDAR 业务参数放入 `lidar_config`（含 `max_stored_cycles`、`scanning_pattern_file` 等），并保持 pattern 引用路径一致。
7. 自检：JSON 语法、文件名一致性、参数范围合理（RPM/帧率/距离/视场角等）。

## 可选：点云（LAS 1.4）与 Pattern 一致性校验

如果你在 aiSim 中跑通配置并导出了 LAS v1.4（Point Data Record Format 7）点云文件，可用脚本做“角度分布 vs Pattern”快速一致性检查：

```bash
python3 "scripts/validate_las_pattern.py" --las "path/to/points.las" --config "output/<lidar_name>/<LidarName>_config.json" --out "output/<lidar_name>/las_pattern_report.md"
```

说明：
- 优先传 `--config`：脚本会自动解析 `lidar_config.*pattern*_file` 来定位 pattern，并读取 `distance_min_meter/distance_max_meter` 作为默认距离过滤（可用 `--min-range/--max-range` 覆盖）。
- 该校验基于点的空间方向（由 XYZ 反推方位角/俯仰角）与 pattern 的离散角度集合做匹配；受测试场景/遮挡影响，不能保证 coverage 为 100%，但可用于发现明显的角度/文件引用/周期设置错误。

## 自动化端到端验证（推荐）

生成配置后，可使用 **aisim-executor** Skill 自动执行 aiSim 仿真、导出 LAS 数据并验证：

### 快速使用

```bash
# 在对话中提示
请使用 aisim-executor 验证刚才生成的 LiDAR 配置：
- sensor_config: output/ATX_100/ATX_100_config.json
- pattern_file: output/ATX_100/ATX_100_pattern.json
- sensor_type: lidar
- 生成验证报告
```

### 命令行方式

```bash
python3 ../aisim-executor/scripts/run_export.py \
  --sensor-config output/ATX_100/ATX_100_config.json \
  --pattern-file output/ATX_100/ATX_100_pattern.json \
  --sensor-type lidar \
  --output-dir output/ATX_100/validation \
  --validate
```

### 完整工作流

```
┌─────────────────────────────────────────────────────────────────┐
│                    lidar-converter + aisim-executor             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. lidar-converter 生成配置                                    │
│     ├─ ATX_100_config.json                                      │
│     ├─ ATX_100_pattern.json                                     │
│     ├─ analysis_report.md                                       │
│     └─ review_checklist.md                                      │
│                          ↓                                       │
│  2. aisim-executor 自动验证                                     │
│     ├─ 自动创建 pattern 符号链接                                │
│     ├─ 启动 aiSim 仿真                                          │
│     ├─ 导出 LAS 点云                                            │
│     └─ 运行 validate_las_pattern.py                             │
│                          ↓                                       │
│  3. 输出验证结果                                                │
│     ├─ lidar_sensor_*.las                                       │
│     ├─ validation_report.md                                     │
│     └─ execution_summary.json                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 前置条件

1. **aiSim 服务端已启动**：
   ```bash
   # 注意：使用完整版本号（如 5.9.0）
   sudo systemctl start aisim-5.9.0.service
   # 或
   /opt/aiMotive/aisim-5.9.0/bin/aisim
   ```

2. **calibrations 目录有写权限**：
   ```bash
   sudo chmod -R a+w /opt/aiMotive/aisim_gui-5.9.0/data/calibrations/
   ```

3. **⚠️ aiSim 执行必需参数**（常见问题根源）：
   - `--stepped=10000`：导出必须使用步进仿真模式（实时模式不支持导出）
   - `--engine_raytrace_backend=vulkan`：LiDAR 必须使用 Vulkan 光线追踪
   - `--world_update_interval=10000`：确保传感器 update_interval 是其整数倍

详细说明见 [aisim-executor SKILL.md](../aisim-executor/SKILL.md)。

---

## 参考资料（按需加载）

- **核心规则**（优先参考）：
  - `knowledge/core/lidar_quick_ref.md` - 快速参考与验证标准
  - `knowledge/core/lidar_essentials.md` - 核心规则与结构约束
  - `knowledge/flash_lidar_pattern_template.md` - Flash LiDAR 生成模板与示例代码
- **配置模板**：`knowledge/sample_structure.md`
- **完整参考**（仅人工查阅，避免默认加载）：`knowledge/reference/aisim_lidar_full.md`
- **调整记录**（维护必读）：`references/adjustments.md`
- **自动化验证**：[aisim-executor](../aisim-executor/SKILL.md)

---

## 两层验证体系

生成配置后，建议执行完整的两层验证以确保质量：

```
┌─────────────────────────────────────────────────────────────────┐
│                       两层验证体系                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  手册附录 ──→ channel_data.py ──→ Pattern JSON ──→ LAS 点云     │
│              │                    │                              │
│              └── 第一层验证 ──────┘                              │
│                  (validate_pattern_channel.py)                   │
│                                   │                              │
│                                   └── 第二层验证 ────────────────┘
│                                       (validate_las_pattern.py)  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 第一层验证：手册 → Pattern

验证 Pattern 中的通道角度是否与手册提取的 channel_data 一致：

```bash
python3 scripts/validate_pattern_channel.py \
  --pattern "output/ATX_100/ATX_100_pattern.json" \
  --channel-data "output/ATX_100/channel_data.py" \
  --h-fov 120 \
  --out "output/ATX_100/channel_validation_report.md"
```

**验证内容**：
- 通道数是否一致
- 每个通道的水平偏移和俯仰角是否匹配
- 偶数帧/奇数帧的角度差异是否正确

### 第二层验证：Pattern → LAS 点云

验证 aiSim 导出的点云是否与 Pattern 定义一致（通过 aisim-executor 自动执行）：

```bash
python3 ../aisim-executor/scripts/run_export.py \
  --sensor-config "output/ATX_100/ATX_100_config.json" \
  --pattern-file "output/ATX_100/ATX_100_pattern.json" \
  --sensor-type lidar \
  --output-dir "output/ATX_100/validation" \
  --validate
```

### 完整验证流程

```bash
# 1. 第一层验证（手册 → Pattern）
python3 scripts/validate_pattern_channel.py \
  --pattern "output/<lidar>/pattern.json" \
  --channel-data "output/<lidar>/channel_data.py" \
  --out "output/<lidar>/channel_validation_report.md"

# 2. 第二层验证（Pattern → LAS，需要 aiSim 服务运行）
python3 ../aisim-executor/scripts/run_export.py \
  --sensor-config "output/<lidar>/config.json" \
  --pattern-file "output/<lidar>/pattern.json" \
  --sensor-type lidar \
  --validate
```

**验证通过标准**：
- 第一层：100% 通道匹配
- 第二层：≥95% 点云匹配率（受场景遮挡影响）
