---
name: radar-convertor
description: 将 aiSim Radar 配置/导出转换为目标项目真实 RadarService MCAP，并对齐 FVR30/CVR30、AdvancedRadarRaytracer、BLF/DBC、RadarService_format、6 路 radar topic、真实 MCAP 对标。当用户提到 aiSim Radar、RadarService、radar JSON、FVR30/CVR30、AdvancedRadarRaytracer、NeuralRadar、BLF/DBC、Radar MCAP 回放或算法接收仿真 radar 数据时使用。
---

# Radar Convertor（aiSim → RadarService MCAP）

## 目标

把 aiSim Radar 配置和导出数据转换成算法可回放的 `hv_sensor_msgs/msg/RadarService` MCAP，并用真实 MCAP 对标结构和字段分布。

默认主线：
- 使用 `AdvancedRadarRaytracer`
- 6 路 radar
- 20Hz
- 每路 800 帧
- RadarService payload 固定 2012B
- 输出 6 个真实 topic

## 当前局限

先阅读 `knowledge/current_limitations.md`，尤其是：
- 结构已对齐，但内容分布仍未完全接近真实雷达。
- aiSim `captured_objects` 数量显著少于真实 RadarService 固定槽位。
- 后向/后侧向目标在当前场景中较稀疏。
- 外参仍是 `design_default`，不是实测标定。
- 私有 `RadarService` IDL 未获得，当前格式来自真实 MCAP/BLF/DBC 逆向证据。

## 常用工作流

### 1. 生成 6 路 Advanced radar 配置

```bash
python3 radar-convertor/scripts/generate_aisim_radar_config.py \
  --extrinsics radar-convertor/templates/radar_extrinsics.yaml \
  --template /opt/aiMotive/aisim_gui-5.11.0/data/calibrations/radar_sensor_advanced.json \
  --update-hz 20 \
  --output output/aisim_radar_config_advanced_6radar.json
```

参数对应关系见 `knowledge/radar_parameter_mapping.md`。

### 2. 检查 aiSim 导出是否可进入转换

必须确认：
- `ego/` 下有 6 路目录：`radar_front`、`radar_front_left`、`radar_front_right`、`radar_rear`、`radar_rear_left`、`radar_rear_right`
- 每路至少 800 个 JSON，编号连续。
- 每帧包含 `captured_objects` 和 `targets`。
- Advanced `targets` 的 `rcs/snr/id` 有效。

### 3. 转换为 6 路 RadarService MCAP

```bash
python3 radar-convertor/scripts/radar_to_mcap.py \
  --input-dir <aisim_export>/ego \
  --output output/sim_radar_6radar_800f.mcap \
  --source objects_with_targets \
  --expected-frames 800 \
  --frame-limit 800 \
  --format radar-convertor/templates/RadarService_format.json
```

转换规则：
- 前向最多 40 个对象槽。
- 侧向最多 32 个非空对象槽。
- 超过上限时按距离优先选择，不静默扩展槽位。
- `objects_with_targets` 会把 Advanced `targets` 的 RCS/SNR/velocity 聚合到对象字段。

### 4. 验证结构

```bash
python3 radar-convertor/scripts/validate_radar_mcap.py \
  --input output/sim_radar_6radar_800f.mcap \
  --format radar-convertor/templates/RadarService_format.json \
  --expected-count 800
```

必须通过：
- 6 路 topic 齐全。
- 每路 800 message。
- payload 固定 2012B。
- schema 为 `hv_sensor_msgs/msg/RadarService`。

### 5. 与真实 MCAP 对标

```bash
python3 radar-convertor/scripts/compare_radar_mcap.py \
  --real <real.mcap> \
  --sim output/sim_radar_6radar_800f.mcap \
  --format radar-convertor/templates/RadarService_format.json \
  --real-count 800 \
  --sim-count 800 \
  --output output/radar_6radar_validation_report.md
```

报告必须明确结构是否通过，以及对象数量、confidence、score、距离、速度、动态属性等字段分布差异。

## 必读参考

- `knowledge/workflow.md`：完整流程与验收门槛
- `knowledge/radar_parameter_mapping.md`：aiSim 参数与 FVR30/CVR30 参数对应关系
- `knowledge/radarservice_format.md`：RadarService 2012B payload 格式
- `knowledge/current_limitations.md`：当前局限与后续升级方向
