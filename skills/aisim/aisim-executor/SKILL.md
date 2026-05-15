---
name: aisim-executor
version: 1.0.0
description: 执行 aiSim 仿真、导出传感器数据、触发验证流程
author: aiSim-agent
dependencies:
  - aiSim 5.9+
  - aisim_client (tc_core toolchain)
---

# aisim-executor Skill

> 通用 aiSim 仿真执行与传感器数据导出工具

---

## 任务目标

1. **自动化执行 aiSim 仿真**：通过 `aisim_client` 命令行工具运行仿真
2. **导出传感器数据**：支持 LiDAR (LAS)、Camera (TGA/JPEG)、Radar (JSON) 等格式
3. **触发验证流程**：自动调用对应的验证脚本生成报告
4. **管理配置路径**：处理 `calibrations://` 协议与本地路径的映射

---

## 输入参数

| 参数 | 必需 | 类型 | 说明 |
|------|------|------|------|
| `sensor_config` | ✅ | 路径 | 传感器配置文件路径（如 `ATX_100_config.json`） |
| `sensor_type` | ✅ | 枚举 | 传感器类型：`lidar` / `camera` / `radar` |
| `pattern_file` | ❌ | 路径 | 扫描模式文件路径（LiDAR 专用，如 `ATX_100_pattern.json`） |
| `output_dir` | ❌ | 路径 | 输出目录（默认：`./output/<timestamp>/`） |
| `scenario` | ❌ | 路径 | 场景文件（默认：`TestTrack_Synth_SensorCalibrationStation_demo.xosc`） |
| `map` | ❌ | 字符串 | 地图名称（默认：`TestTrack_Synth_SensorCalibrationStation`） |
| `tick_us` | ❌ | int | 仿真步进（微秒），同时用于 `--stepped/--world_update_interval/--scenario_update_interval`（默认：10000） |
| `client_timeout_sec` | ❌ | int | `aisim_client` 执行超时（秒），用于复杂场景/更小 tick（默认：300） |
| `environment_config` | ❌ | 路径 | 环境配置文件路径（如 `Garage.json` 用于光照设置） |
| `export_steps` | ❌ | 对象 | 导出范围 `{start: 5, end: 20, step: 1}` |
| `server_address` | ❌ | 字符串 | aiSim 服务端地址（默认：`127.0.0.1:8888`） |
| `skip_validation` | ❌ | 布尔 | 跳过验证步骤（默认：`false`） |
| `validator_script` | ❌ | 路径 | 自定义验证脚本路径 |

---

## 输出物

| 文件 | 说明 |
|------|------|
| `<sensor>_<step>.<ext>` | 导出的传感器数据（如 `lidar_sensor_00005.las`） |
| `execution_log.txt` | aisim_client 执行日志 |
| `validation_report.md` | 验证报告（如果启用验证） |
| `execution_summary.json` | 执行摘要（状态、耗时、文件列表） |

---

## 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    aisim-executor 工作流                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 输入验证                                                     │
│     ├─ 检查 sensor_config 文件存在性                             │
│     ├─ 检查 pattern_file 存在性（如果指定）                       │
│     └─ 验证 sensor_type 有效性                                   │
│                                                                  │
│  2. 路径处理                                                     │
│     ├─ 解析 sensor_config 中的 scanning_pattern_file             │
│     ├─ 如果是 calibrations:// 协议：                             │
│     │   └─ 检查文件是否已在 calibrations 目录                    │
│     ├─ 如果是本地路径：                                          │
│     │   ├─ 创建符号链接到 calibrations 目录                      │
│     │   └─ 或：修改 config 使用绝对路径（需 aiSim 支持）          │
│     └─ 生成临时工作配置文件                                      │
│                                                                  │
│  3. 服务端检查                                                   │
│     ├─ 检测 aiSim 服务端是否运行（端口连接测试）                  │
│     ├─ 如未运行：                                                │
│     │   ├─ 提示用户启动：systemctl start aisim-5.9.service       │
│     │   └─ 或：/opt/aiMotive/aisim-5.9.0/bin/aisim              │
│     └─ 等待服务就绪（最多 30 秒）                                │
│                                                                  │
│  4. 生成导出配置                                                 │
│     ├─ 根据 sensor_type 选择模板                                 │
│     ├─ 设置导出范围（start/end/step）                            │
│     └─ 写入临时 export_config.json                               │
│                                                                  │
│  5. 执行 aisim_client                                           │
│     ├─ 构建命令行：                                              │
│     │   aisim_client \                                          │
│     │     --address=<server_address> \                          │
│     │     --sensor_configuration=<config> \                     │
│     │     --map=<map> \                                         │
│     │     --scenario=<scenario> \                               │
│     │     --open_scenario \                                     │
│     │     --export \                                            │
│     │     --export_configuration=<export_config> \              │
│     │     --output_dir=<output_dir> \                           │
│     │     --exit_after_export_end \                             │
│     │     --no_draw                                             │
│     ├─ 执行并捕获输出                                            │
│     └─ 检查退出码                                                │
│                                                                  │
│  6. 验证（可选）                                                 │
│     ├─ LiDAR：调用 validate_las_pattern.py                      │
│     ├─ Camera：（未来实现）                                      │
│     └─ Radar：（未来实现）                                       │
│                                                                  │
│  7. 生成报告                                                     │
│     ├─ execution_summary.json                                   │
│     ├─ validation_report.md（如果验证）                          │
│     └─ 清理临时文件（可选）                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 关键路径常量

```python
# aiSim 安装路径（自动检测版本）
AISIM_VERSION = detect_aisim_version()  # 如 "5.9.0", "5.10.0"
AISIM_BIN = f"/opt/aiMotive/aisim-{AISIM_VERSION}/bin/aisim"
AISIM_CLIENT = f"/opt/aiMotive/toolchains/tc_core-{AISIM_VERSION}/clients/bin/aisim_client"

# 服务名称（使用完整版本号）
AISIM_SERVICE = f"aisim-{AISIM_VERSION}.service"

# 环境变量可覆盖自动检测
# AISIM_VERSION, AISIM_HOME, AISIM_GUI_HOME, TC_CORE_HOME

# 默认 calibrations 目录
CALIBRATIONS_DIR = f"/opt/aiMotive/aisim_gui-{AISIM_VERSION}/data/calibrations"
SCANNING_PATTERN_DIR = f"{CALIBRATIONS_DIR}/scanning_pattern"

# 默认测试场景
DEFAULT_MAP = "TestTrack_Synth_SensorCalibrationStation"
DEFAULT_SCENARIO = f"/opt/aiMotive/aisim_gui-{AISIM_VERSION}/data/openscenarios/TestTrack_Synth_SensorCalibrationStation_demo.xosc"

# 默认服务端
DEFAULT_SERVER = "127.0.0.1:8888"
DEFAULT_PORT = 8888

# 推荐 tick（导出必须满足 update_intervals 整除约束）
DEFAULT_TICK_US = 10000
```

---

## 使用示例

### 示例 1：基本 LiDAR 验证

```
请使用 aisim-executor 执行以下任务：

传感器配置：output/ATX_100/ATX_100_config.json
Pattern 文件：output/ATX_100/ATX_100_pattern.json
传感器类型：lidar
输出目录：output/ATX_100/validation/
```

### 示例 2：指定导出范围

```
使用 aisim-executor：
- sensor_config: /path/to/lidar_config.json
- sensor_type: lidar
- export_steps: {start: 10, end: 30, step: 2}
- 生成验证报告
```

### 示例 3：跳过验证

```
aisim-executor 导出 LiDAR 数据：
- 配置：ATX_100_config.json
- 跳过验证
- 仅导出 LAS 文件
```

### 示例 4：Highway 场景（运动状态）导出

用于验证“车辆运动 + 逐点时间戳”是否会产生点云运动畸变（rolling shutter / deskew 问题）：

```
python3 "aisim-executor/scripts/run_export.py" \
  --sensor-config "output/ATX_100/ATX_100_config.json" \
  --sensor-type lidar \
  --pattern-file "output/ATX_100/ATX_100_pattern.json" \
  --output-dir "output/ATX_100/validation_highway_motion/" \
  --map "Highway_Synth_Straight5km" \
  --scenario "Highway_Synth_Straight5km_demo.xosc" \
  --tick-us 10000 \
  --export-start 5 --export-end 8 --export-step 1 \
  --validate
```

---

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| **配置文件不存在** | 报错并提示正确路径 |
| **aiSim 服务未启动** | 提示启动命令，等待 30 秒后超时 |
| **aisim_client 执行失败** | 保存错误日志，返回失败状态 |
| **导出文件为空** | 警告并记录，继续执行验证 |
| **验证脚本失败** | 记录错误，仍生成部分报告 |
| **权限不足** | 提示使用 sudo 或检查目录权限 |

### 日志查看与问题排查

当遇到 `Internal lidar raytrace error` 等错误时，可通过以下方式查看详细日志：

**1. aiSim 服务日志文件**

```bash
# 日志文件位置：/var/log/aisim-<version>.log
# 例如：
tail -100 /var/log/aisim-5.9.0.log | grep -i "error\|lidar"

# 查看最近的错误
grep -A5 -B5 "error" /var/log/aisim-5.9.0.log | tail -50
```

**2. systemd journal**

```bash
# 查看服务日志
journalctl -u aisim-5.9.0.service --no-pager -n 100

# 实时跟踪日志
journalctl -u aisim-5.9.0.service -f
```

**3. 常见错误及解决方案**

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `invalid laser array in scanning pattern! Calculated dt for this laser array #N is lesser than or equal to 0.0` | Pattern 文件中多个周期的 TimeOffsetS 没有正确递增 | 确保周期 N 的 TimeOffsetS 从 `N * frame_duration` 开始 |
| `Pattern file not found` | scanning_pattern_file 路径错误 | 检查 config 中的路径，确保文件已复制到 calibrations 目录 |
| `Internal lidar raytrace error` | Pattern 文件格式或参数错误 | 查看 `/var/log/aisim-<version>.log` 获取详细错误信息 |

---

## 与其他 Skill 的集成

### lidar-converter → aisim-executor

```
lidar-converter 生成配置后，可调用 aisim-executor 进行端到端验证：

1. lidar-converter 输出：
   - output/ATX_100/ATX_100_config.json
   - output/ATX_100/ATX_100_pattern.json

2. aisim-executor 输入：
   - sensor_config: output/ATX_100/ATX_100_config.json
   - pattern_file: output/ATX_100/ATX_100_pattern.json
   - sensor_type: lidar

3. aisim-executor 输出：
   - output/ATX_100/validation/lidar_sensor_*.las
   - output/ATX_100/validation/validation_report.md
```

### 未来：camera-converter → aisim-executor

```
camera-converter 生成配置后，可调用 aisim-executor 进行端到端验证：

1. camera-converter 输出：
   - output/Camera/Bosch_Camera_RGBA_updated.json

2. aisim-executor 输入：
   - sensor_config: output/Camera/Bosch_Camera_RGBA_updated.json
   - sensor_type: camera

3. aisim-executor 输出：
   - output/Camera/validation/exports/<timestamp>/ego/<camera_name>/color/*.tga
   - output/Camera/validation/distortion_report.md（如果启用验证）

4. 验证内容：
   - 检测图像中的直线/棋盘格
   - 分析直线度误差（畸变会导致直线变弯）
   - 生成验证报告
```

---

## 依赖的验证脚本

| 传感器类型 | 验证脚本 | 位置 | 状态 |
|-----------|---------|------|------|
| LiDAR | `validate_las_pattern.py` | `../lidar-converter/scripts/` | ✅ 已实现 |
| Camera | `validate_camera_distortion.py` | `../camera-converter/scripts/` | ✅ 已实现 |
| Radar | （待实现） | - | ❌ 待实现 |

---

## 注意事项

1. **aiSim 服务端必须先启动**：
   ```bash
   # 方式 1：systemctl（⚠️ 注意使用完整版本号，如 5.9.0 而非 5.9）
   sudo systemctl start aisim-5.9.0.service

   # 方式 2：直接启动
   /opt/aiMotive/aisim-5.9.0/bin/aisim
   ```

2. **版本自动检测**：
   - 脚本会自动扫描 `/opt/aiMotive/` 目录检测已安装的 aiSim 版本
   - 可通过环境变量覆盖：`AISIM_VERSION=5.10.0`
   - 支持的环境变量：`AISIM_VERSION`, `AISIM_HOME`, `AISIM_GUI_HOME`, `TC_CORE_HOME`

3. **Pattern 文件路径处理**：
   - 脚本会自动在临时目录创建 `scanning_pattern/` 子目录
   - Pattern 文件通过符号链接引用，避免复制大文件
   - Config 自动修改为相对路径以兼容 aisim_client

4. **GPU 要求**：aiSim 需要 Vulkan 支持的 GPU

5. **无头模式**：使用 `--no_draw` 可在无显示器环境运行（需配置虚拟帧缓冲）

6. **⚠️ 常见问题快速排查**：
   | 错误信息 | 解决方案 |
   |---------|---------|
   | `Export doesn't work with realtime simulation!` | 添加 `--stepped=10000` |
   | `Lidar sensor requires VULKAN raytrace engine backend` | 添加 `--engine_raytrace_backend=vulkan` |
   | `Update interval must be the multiple of world's update interval` | 添加 `--world_update_interval=10000` |
   | `aisim-5.9.service not found` | 使用完整版本号：`aisim-5.9.0.service` |

---

## aisim_client 完整参数参考

### 核心参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-a, --address` | 服务端地址（多节点用逗号分隔） | `127.0.0.1:8888` |
| `-m, --map` | 地图名称 | - |
| `-s, --scenario` | 场景文件路径 | - |
| `--sensor_configuration` | 传感器配置文件路径 | - |
| `--output_dir` | 输出目录 | - |

### 仿真控制参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--stepped=<micro_sec>` | **步进仿真模式（导出必需）**，指定步长（微秒） | 实时模式 |
| `--world_update_interval=<micro_sec>` | 世界更新间隔（微秒） | `40000` |
| `--scenario_update_interval=<micro_sec>` | 场景更新间隔（微秒） | 同 world_update_interval |
| `--max_latency=<micro_sec>` | 实时仿真最大延迟 | `60000` |
| `--time_multiplier=<integer>` | 实时仿真时间倍率 | `1` |

### 引擎参数（⚠️ 重要）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--engine_render_backend=<vulkan/null>` | 渲染引擎后端 | `vulkan` |
| `--engine_raytrace_backend=<vulkan/null>` | **光线追踪引擎后端（LiDAR 必需 vulkan）** | `null` |

### 导出参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--export` | 启用导出模式 | - |
| `--export_configuration` | 导出配置文件路径 | - |
| `--export_start_step` | 导出起始步 | - |
| `--export_end_step` | 导出结束步 | - |
| `--export_step` | 导出步长 | - |
| `--exit_after_export_end` | 导出完成后退出 | - |
| `--jpeg_export_quality` | JPEG 导出质量 | `100` |

### 场景参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--open_scenario` | 使用 OpenSCENARIO 格式 | - |
| `--starting_speed=<km/h>` | 起始速度 | `-1` |
| `--random_seed` | 随机种子 | `0` |
| `--scenario_warmup_duration=<sec>` | 场景预热时长 | - |
| `--exit_on_scenario_finished` | 场景结束后退出 | - |

### 其他参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--no_draw` | 禁用传感器数据显示（无头模式） | - |
| `--vehicle_name` | 车辆模型名称 | `FordFusionLogo` |
| `-e, --engage=<0/1/2>` | 自动控制接管模式 | `1` |
| `--disable_ego_render` | 禁用自车渲染 | - |

---

## 关键配置约束

### ⚠️ 导出必须使用步进仿真模式

**重要**：aiSim 不支持在实时仿真模式下导出数据，必须使用 `--stepped` 参数启用步进仿真。

```bash
# 错误：实时模式下导出会报错
aisim_client --export ...
# 报错：Export doesn't work with realtime simulation!

# 正确：使用步进仿真模式
aisim_client --stepped=10000 --export ...
```

**参数配置建议**：

| 参数 | 推荐值 | 说明 |
|------|--------|------|
| `--stepped` | `10000` | 步进间隔 10ms，与 world_update_interval 一致 |
| `--world_update_interval` | `10000` | 世界更新间隔 10ms，适配大多数传感器 |
| `--scenario_update_interval` | `10000` | 场景更新间隔，建议与 stepped 一致 |

### ⚠️ update_interval 与 world_update_interval 的关系

**重要规则**：传感器的 `update_intervals` 必须是 `world_update_interval` 的整数倍。

**推荐做法**：
- **不要修改传感器的 update_intervals**（保持与手册一致）
- **修改 world_update_interval** 以适配传感器

```bash
# 默认 world_update_interval = 40000 µs (40ms)
# 如果传感器 update_interval = 100000 µs (100ms, 10Hz)
# 100000 不是 40000 的整数倍，会报错

# 解决方案：设置 world_update_interval = 10000 µs
aisim_client --world_update_interval=10000 ...
```

**常用 world_update_interval 值**：

| 值 (µs) | 说明 | 适用场景 |
|---------|------|---------|
| `10000` | 10ms，100Hz | **推荐**，适配大多数传感器 |
| `20000` | 20ms，50Hz | 适配 50Hz 传感器 |
| `40000` | 40ms，25Hz | 默认值 |

### ⚠️ LiDAR 必须使用 Vulkan Raytrace Backend

LiDAR 传感器需要光线追踪功能，**必须**在命令行中指定：

```bash
aisim_client --engine_raytrace_backend=vulkan ...
```

如果不指定，会报错：
```
Lidar sensor requires VULKAN raytrace engine backend to function correctly,
but currently it is set to null.
```

---

## 标准执行命令模板

### LiDAR 传感器导出（推荐）

```bash
cd /opt/aiMotive/toolchains/tc_core-5.9.0/clients/bin && ./aisim_client \
  --address=127.0.0.1:8888 \
  --stepped=10000 \
  --world_update_interval=10000 \
  --scenario_update_interval=10000 \
  --sensor_configuration="<config_path>" \
  --map=TestTrack_Synth_SensorCalibrationStation \
  --scenario=/opt/aiMotive/aisim_gui-5.9.0/data/openscenarios/TestTrack_Synth_SensorCalibrationStation_demo.xosc \
  --open_scenario \
  --export \
  --export_configuration="<export_config_path>" \
  --output_dir="<output_dir>" \
  --exit_after_export_end \
  --no_draw \
  --engine_raytrace_backend=vulkan
```

### Camera 传感器导出

```bash
cd /opt/aiMotive/toolchains/tc_core-5.9.0/clients/bin && ./aisim_client \
  --address=127.0.0.1:8888 \
  --stepped=10000 \
  --world_update_interval=10000 \
  --scenario_update_interval=10000 \
  --sensor_configuration="<config_path>" \
  --map=TestTrack_Synth_SensorCalibrationStation \
  --scenario=/opt/aiMotive/aisim_gui-5.9.0/data/openscenarios/TestTrack_Synth_SensorCalibrationStation_demo.xosc \
  --open_scenario \
  --export \
  --export_configuration="<export_config_path>" \
  --output_dir="<output_dir>" \
  --exit_after_export_end \
  --no_draw
```

---

## 错误处理

| 错误类型 | 处理方式 |
|---------|---------|
| **配置文件不存在** | 报错并提示正确路径 |
| **aiSim 服务未启动** | 提示启动命令，等待 30 秒后超时 |
| **aisim_client 执行失败** | 保存错误日志，返回失败状态 |
| **导出文件为空** | 警告并记录，继续执行验证 |
| **验证脚本失败** | 记录错误，仍生成部分报告 |
| **权限不足** | 提示使用 sudo 或检查目录权限 |

### 日志查看与问题排查

当遇到 `Internal lidar raytrace error` 等错误时，可通过以下方式查看详细日志：

**1. aiSim 服务日志文件**

```bash
# 日志文件位置：/var/log/aisim-<version>.log
# 例如：
tail -100 /var/log/aisim-5.9.0.log | grep -i "error\|lidar"

# 查看最近的错误
grep -A5 -B5 "error" /var/log/aisim-5.9.0.log | tail -50
```

**2. systemd journal**

```bash
# 查看服务日志
journalctl -u aisim-5.9.0.service --no-pager -n 100

# 实时跟踪日志
journalctl -u aisim-5.9.0.service -f
```

**3. 常见错误及解决方案**

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| `invalid laser array in scanning pattern! Calculated dt for this laser array #N is lesser than or equal to 0.0` | Pattern 文件中多个周期的 TimeOffsetS 没有正确递增 | 确保周期 N 的 TimeOffsetS 从 `N * frame_duration` 开始 |
| `Pattern file not found` | scanning_pattern_file 路径错误 | 检查 config 中的路径，确保文件已复制到 calibrations 目录 |
| `Internal lidar raytrace error` | Pattern 文件格式或参数错误 | 查看 `/var/log/aisim-<version>.log` 获取详细错误信息 |
| `Export doesn't work with realtime simulation!` | 实时模式下不支持导出 | 添加 `--stepped=10000` 参数启用步进仿真 |
| `Lidar sensor requires VULKAN raytrace engine backend` | 未指定 raytrace backend | 添加 `--engine_raytrace_backend=vulkan` 参数 |
| `Update interval must be the multiple of world's update interval` | 传感器更新间隔不是世界更新间隔的整数倍 | 添加 `--world_update_interval=10000` 参数 |
| `vertical_scanning_pattern_content` 为空 | Pattern 文件未被正确加载 | 检查文件权限（需 644），或重启 aiSim 服务清除缓存 |

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.3.0 | 2026-01-04 | **Camera 完整支持**：修复 camera export config（从 sensor_config 读取相机名称）；添加 `run_camera_validation` 函数；添加 `--environment-config` 参数；Camera 验证调用 `validate_camera_distortion.py` |
| 1.2.0 | 2026-01-04 | **Pandar_64 验证通过**（匹配率 99.91%）；添加 aisim_client 完整参数参考；添加 stepped 步进仿真必需说明；添加 world_update_interval 配置说明；添加 raytrace backend 必需说明；更新常见错误及解决方案；添加服务名称完整版本号说明（aisim-X.Y.Z.service） |
| 1.1.0 | 2026-01-04 | 添加 aisim_client 完整参数参考；添加 stepped 步进仿真必需说明；添加 world_update_interval 配置说明；添加 raytrace backend 必需说明；更新常见错误及解决方案 |
| 1.0.0 | 2025-12-30 | 初始版本，支持 LiDAR 导出与验证 |
