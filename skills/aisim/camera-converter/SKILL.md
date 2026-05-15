---
name: camera-converter
description: 将相机标定参数（YAML/Excel）转换或更新为 aiSim Camera 传感器配置 JSON（优先生成/更新 Bosch_Camera_RGBA；可生成 Bosch_Camera_RAW12 但需先确认 RAW 前置与 raw_transform 细节）。当用户提到 aiSim Camera、camera config JSON、Bosch_Camera_RGBA/Bosch_Camera_RAW12、标定参数 YAML、相机内参/外参、RAW12/raw_transform 时使用。
---

# Camera Converter（aiSim）

## 目标与输出物

生成或更新 aiSim Camera 配置 JSON（`{ "sensors": { ... } }` 结构），主要覆盖：
- 内参（`camera_config.model`、`camera_config.distortion_parameters`、分辨率）
- 外参（`camera_config.position` / `camera_config.rotation`，可选更新）

## 文件结构

```
camera-converter/
├── CLAUDE.md                    # 模块文档
├── SKILL.md                     # 本文件（Skill 定义）
├── scripts/
│   ├── update_camera_config.py      # 核心转换脚本
│   ├── validate_camera_config.py    # 第一层：参数对照验证
│   └── validate_camera_distortion.py # 第三层：图像畸变验证
├── knowledge/
│   ├── aiSim_5.9_Camera.md      # aiSim Camera 参数参考
│   └── raw_camera_need_pre.md   # RAW12 前置材料清单
└── templates/
    ├── Bosch_Camera_RGBA.json   # 已验证的 RGBA 模板（11 个相机）
    ├── Bosch_Camera_RAW12.json  # RAW12 模板（需补全 raw_transform）
    └── Bosch_Camera_temp.json   # 单相机模板
```

## 必读参考

- 参数与字段定义：`camera-converter/knowledge/aiSim_5.9_Camera.md`（未来版本更新时以最新文档为准）
- RAW12 前置材料清单：`camera-converter/knowledge/raw_camera_need_pre.md`
- 模块详细文档：`camera-converter/CLAUDE.md`

## 关键约束（姿态角）

`templates/Bosch_Camera_RGBA.json` 中的姿态角已在 aiSim 中验证为正确基准。

执行转换时默认以 **JSON 模板的 rotation 为准**，不要直接采用 Excel 中的 roll/pitch/yaw，除非用户明确确认其欧拉角定义与 aiSim 一致。

## 运行依赖（仅脚本本地执行需要）

脚本依赖 `pandas/openpyxl/pyyaml`。如果运行时报 `ModuleNotFoundError`，先在当前 Python 环境安装依赖：

```bash
python3 -m pip install pandas openpyxl pyyaml
```

## 快速执行（推荐：只更新内参）

执行脚本并基于 YAML 更新内参，外参保持与模板 JSON 一致：

```bash
python3 "camera-converter/scripts/update_camera_config.py" \
  --json "camera-converter/templates/Bosch_Camera_RGBA.json" \
  --yaml-dir "input/Camera/标定参数" \
  --output "output/Camera/Bosch_Camera_RGBA_updated.json"

# 验证 JSON 语法
python3 -m json.tool "output/Camera/Bosch_Camera_RGBA_updated.json" > /dev/null

# 验证内参与原始 YAML 一致性
python3 "camera-converter/scripts/validate_camera_config.py" \
  --json "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --yaml-dir "input/Camera/标定参数" \
  --out "output/Camera/validation_report.md"
```

> **注意**：脚本默认参数已设置为安全值（`--camera-source yaml`、`--position-source template`、`--rotation-source template`），无需显式指定。

## 验证生成结果

使用 `validate_camera_config.py` 验证生成的 JSON 配置与原始 YAML 标定参数的一致性：

```bash
python3 "camera-converter/scripts/validate_camera_config.py" \
  --json "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --yaml-dir "input/Camera/标定参数" \
  --out "output/Camera/validation_report.md"
```

验证内容：
- 模型类型映射（PINHOLE → OpenCVPinhole, SCARAMUZZA → OcamFisheye）
- 分辨率一致性（image_width/height）
- 内参参数一致性：
  - Pinhole: focal_length, principal_point, distortion_coefficients, rational_model_coefficients
  - OCam: principal_point, polynomial_coefficients, inv_polynomial_coefficients
- OcamFisheye 的 environment_mapping_type 是否为 Cube_6_Face

验证报告示例：
```
| 相机名称 | YAML 文件 | 模型 | 分辨率 | 内参 | 状态 |
|---------|----------|------|--------|------|------|
| side_view_camera_front_left | front_left.yaml | ✅ | ✅ | ✅ | ✅ |
```

## 可选：使用 YAML 的平移覆盖 position（rotation 仍以模板为准）

当 `input/Camera/标定参数/*.yaml` 包含 `T_v_c`（OpenCV 4x4 矩阵）时，可用其平移覆盖 position：

```bash
python3 "camera-converter/scripts/update_camera_config.py" \
  --json "camera-converter/templates/Bosch_Camera_RGBA.json" \
  --yaml-dir "input/Camera/标定参数" \
  --position-source yaml \
  --output "output/Camera/Bosch_Camera_RGBA_pos_from_yaml.json"
```

## 可选：参考 Excel（谨慎）

当需要用 `input/整车传感器参数.xlsx` 作为摄像头清单或位置来源时：

1. 明确向用户确认 Excel 中 roll/pitch/yaw 的欧拉角约定（旋转顺序、轴定义、单位、正负号）
2. 未确认前，固定 `--rotation-source template`

示例（仅使用 Excel 的 position，rotation 保持模板）：

```bash
python3 "camera-converter/scripts/update_camera_config.py" \
  --json "camera-converter/templates/Bosch_Camera_RGBA.json" \
  --excel "input/整车传感器参数.xlsx" \
  --yaml-dir "input/Camera/标定参数" \
  --camera-source excel \
  --position-source excel \
  --output "output/Camera/Bosch_Camera_RGBA_pos_from_excel.json"
```

## RAW12（需要先确认前置材料）

生成 `Bosch_Camera_RAW12.json` 前，先向用户收集并确认 `camera-converter/knowledge/raw_camera_need_pre.md` 中的关键材料，尤其是：
- RAW 数据位宽/对齐方式（LSB/MSB aligned）
- 端序、PWL/HDR 压缩与曲线参数
- Black level / pedestal 的定义位置（压缩前/后）

确认完成后，再基于 `camera-converter/templates/Bosch_Camera_RAW12.json` 模板生成目标文件，并在输出中明确记录 raw_transform 的假设与来源。

示例（仅在确认 RAW 前置材料后执行）：

```bash
python3 "camera-converter/scripts/update_camera_config.py" \
  --json "camera-converter/templates/Bosch_Camera_RAW12.json" \
  --yaml-dir "input/Camera/标定参数" \
  --output "output/Camera/Bosch_Camera_RAW12_updated.json"

# 验证 JSON 语法
python3 -m json.tool "output/Camera/Bosch_Camera_RAW12_updated.json" > /dev/null
```

## 常见问题快速排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 相机朝向错误 | 使用了 Excel 的姿态角 | 使用 `--rotation-source template` |
| 找不到 YAML 文件 | camera_name 不匹配 | 确保 YAML 中的 `camera_name` 与模板 JSON 一致 |
| OcamFisheye 渲染异常 | 未使用 Cube_6_Face | 脚本会自动设置，检查输出 JSON |
| RAW12 输出异常 | raw_transform 配置错误 | 确认 LSB/MSB 对齐方式 |

---

## 三层验证体系

Camera 配置生成后，可通过三层验证确保配置正确：

### 第一层：参数对照验证（离线）

验证生成的 JSON 配置与原始 YAML 标定参数的一致性：

```bash
python3 "camera-converter/scripts/validate_camera_config.py" \
  --json "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --yaml-dir "input/Camera/标定参数" \
  --out "output/Camera/validation_report.md"
```

**验证内容**：模型类型、分辨率、内参参数（焦距、主点、畸变系数）

### 第二层：仿真渲染验证（需要 aiSim）

使用 `aisim-executor` 导出 Camera 图像，验证配置能正常工作：

```bash
python3 "aisim-executor/scripts/run_export.py" \
  --sensor-config "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --sensor-type camera \
  --output-dir "output/Camera/export/" \
  --export-start 5 --export-end 8 --export-step 1
```

**验证内容**：11 个相机全部成功导出图像

### 第三层：图像畸变验证（需要 OpenCV）

分析导出的图像，检测棋盘格线条直线度：

```bash
# 安装依赖
pip install opencv-python numpy

# 运行验证
python3 "camera-converter/scripts/validate_camera_distortion.py" \
  --image-dir "output/Camera/export/" \
  --config "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --out "output/Camera/distortion_report.md"
```

**验证内容**：
- 检测棋盘格角点
- 分析角点排列的直线度（畸变会导致直线变弯）
- 直线度误差 < 2.0 像素为通过

### 一键验证（第二层 + 第三层）

使用 `aisim-executor` 的 `--validate` 参数自动执行导出和验证：

```bash
python3 "aisim-executor/scripts/run_export.py" \
  --sensor-config "output/Camera/Bosch_Camera_RGBA_updated.json" \
  --sensor-type camera \
  --output-dir "output/Camera/validation/" \
  --environment-config "aisim-executor/configs/Garage.json" \
  --export-start 5 --export-end 8 \
  --validate
```

**输出**：
- `output/Camera/validation/exports/<timestamp>/ego/<camera_name>/color/*.tga` - 导出的图像
- `output/Camera/validation/distortion_report.md` - 畸变验证报告
- `output/Camera/validation/execution_summary.json` - 执行摘要

**注意**：`--environment-config` 参数用于指定环境配置（如 Garage.json），可控制光照等渲染参数。

### 验证场景说明

默认使用 `TestTrack_Synth_SensorCalibrationStation` 场景（四面棋盘格环境）：
- 大部分相机可以看到完整或部分棋盘格
- `front_tele`（长焦）和 `rear` 可能只看到部分棋盘格，但仍有线条可用于验证
- 环视相机（surround_*）因俯视角度，主要看到墙面下部
