# aisim_client 命令行参考

> aiSim 官方客户端工具参数快速参考

---

## 基本信息

**路径**：`/opt/aiMotive/toolchains/tc_core-5.9.0/clients/bin/aisim_client`

**用途**：连接 aiSim 服务端，执行仿真、导出传感器数据

---

## 常用参数分类

### 通用选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `-h, --help` | 显示帮助 | |
| `-a, --address` | 服务端地址 | `--address=127.0.0.1:8888` |

### 仿真控制

| 参数 | 说明 | 示例 |
|------|------|------|
| `--stepped` | 步进仿真（微秒） | `--stepped=40000` |
| `--max_latency` | 最大延迟（微秒） | |
| `--time_multiplier` | 时间倍率 | `--time_multiplier=2` |
| `--simulation_config` | 仿真配置文件 | |
| `--exit_on_scenario_finished` | 场景结束后退出 | |

### 场景与地图

| 参数 | 说明 | 示例 |
|------|------|------|
| `-m, --map` | 地图名称 | `--map=TestTrack_Synth_SensorCalibrationStation` |
| `-s, --scenario` | 场景文件路径 | `--scenario=/path/to/scenario.xosc` |
| `--open_scenario` | 使用 OpenSCENARIO 格式 | |
| `--environment_config_path` | 环境配置路径 | |

### 车辆与传感器

| 参数 | 说明 | 示例 |
|------|------|------|
| `--vehicle_name` | 车辆模型名称 | |
| `--vehicle_color` | 车辆颜色 | |
| `--sensor_configuration` | 传感器配置文件 | `--sensor_configuration=/path/to/config.json` |
| `-e, --engage` | 自动驾驶控制 | `--engage=1` |

### 导出控制（重点）

| 参数 | 说明 | 示例 |
|------|------|------|
| `--export` | **启用导出模式** | |
| `--export_configuration` | 导出配置文件 | `--export_configuration=/path/to/export.json` |
| `--output_dir` | 输出目录 | `--output_dir=/path/to/output` |
| `--export_start_step` | 导出起始步 | `--export_start_step=5` |
| `--export_end_step` | 导出结束步 | `--export_end_step=20` |
| `--export_step` | 导出步长 | `--export_step=1` |
| `--exit_after_export_end` | **导出完成后退出** | |
| `--jpeg_export_quality` | JPEG 质量 | `--jpeg_export_quality=90` |

### 显示选项

| 参数 | 说明 | 示例 |
|------|------|------|
| `--no_draw` | **无窗口模式** | |
| `--screen_capture` | 截屏导出 | |

### 渲染引擎

| 参数 | 说明 | 示例 |
|------|------|------|
| `--engine_render_backend` | 渲染后端 | `--engine_render_backend=vulkan` |
| `--engine_raytrace_backend` | 光追后端 | `--engine_raytrace_backend=vulkan` |

---

## 常用命令模板

### 1. 基本 LiDAR 导出

```bash
/opt/aiMotive/toolchains/tc_core-5.9.0/clients/bin/aisim_client \
  --address=127.0.0.1:8888 \
  --sensor_configuration=/path/to/lidar_config.json \
  --map=TestTrack_Synth_SensorCalibrationStation \
  --scenario=/opt/aiMotive/aisim_gui-5.9.0/data/openscenarios/TestTrack_Synth_SensorCalibrationStation_demo.xosc \
  --open_scenario \
  --export \
  --export_configuration=/path/to/lidar_export.json \
  --output_dir=/path/to/output \
  --exit_after_export_end \
  --no_draw
```

### 2. 指定导出范围

```bash
aisim_client \
  --address=127.0.0.1:8888 \
  --sensor_configuration=config.json \
  --map=TestTrack_Synth_SensorCalibrationStation \
  --scenario=scenario.xosc \
  --open_scenario \
  --export \
  --export_start_step=10 \
  --export_end_step=50 \
  --export_step=2 \
  --output_dir=output \
  --exit_after_export_end
```

### 3. 多传感器导出

```bash
aisim_client \
  --address=127.0.0.1:8888 \
  --sensor_configuration=multi_sensor_config.json \
  --export \
  --export_configuration=export_all_sensors.json \
  --output_dir=output \
  --exit_after_export_end
```

---

## 导出配置文件格式

```json
{
    "vehicles": {
        "ego": {
            "sensors": [
                {
                    "sensor_name": "lidar_sensor",
                    "subtypes": [
                        {"subtype_name": "las", "extension": "las"},
                        {"subtype_name": "json", "extension": "json"}
                    ]
                },
                {
                    "sensor_name": "camera_sensor",
                    "subtypes": [
                        {"subtype_name": "color", "extension": "tga"}
                    ]
                }
            ],
            "export_step": 1,
            "start": 5,
            "end": 20
        }
    }
}
```

### 传感器子类型

| 传感器类型 | 子类型 | 扩展名 | 说明 |
|-----------|--------|--------|------|
| **LiDAR** | las | .las | LAS 1.4 点云格式 |
| | json | .json | JSON 点云格式 |
| **Camera** | color | .tga | 彩色图像 |
| | seg | .tga | 语义分割 |
| | depth | .dds | 深度图 |
| | bbox | .json | 边界框 |
| | lane | .json | 车道线 |
| **Radar** | radar | .json | 雷达目标 |

---

## 服务端启动方式

### 方式 1：systemctl（推荐）

```bash
# 启动
sudo systemctl start aisim-5.9.service

# 停止
sudo systemctl stop aisim-5.9.service

# 状态
sudo systemctl status aisim-5.9.service
```

### 方式 2：直接启动

```bash
/opt/aiMotive/aisim-5.9.0/bin/aisim \
  --port=8888 \
  --asset_dirs="/path/to/assets"
```

---

## 常见问题

### Q1: "Connection refused" 错误

**原因**：aiSim 服务端未启动

**解决**：
```bash
sudo systemctl start aisim-5.9.service
# 或
/opt/aiMotive/aisim-5.9.0/bin/aisim
```

### Q2: "Pattern file not found" 错误

**原因**：`scanning_pattern_file` 路径不正确

**解决**：
1. 确保 pattern 文件在 `calibrations://scanning_pattern/` 目录
2. 或使用绝对路径并创建符号链接

### Q3: 导出文件为空

**可能原因**：
1. 传感器配置错误
2. 导出范围过小（start > end）
3. 传感器名称不匹配

**解决**：检查传感器配置中的 `sensor_name` 与导出配置一致

### Q4: GPU 相关错误

**解决**：
1. 确保有支持 Vulkan 的 GPU
2. 安装正确的显卡驱动
3. 检查 `--engine_render_backend=vulkan`

---

## 环境变量

| 变量 | 说明 |
|------|------|
| `LD_LIBRARY_PATH` | 需要包含 aiSim 库路径 |
| `DISPLAY` | X11 显示（即使 no_draw 也可能需要） |

---

## 版本信息

- **aiSim 版本**：5.9.0
- **更新日期**：2025-12-30
