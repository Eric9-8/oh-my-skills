# aiSim Skills

面向 aiSim 仿真平台的工具链 Skills 集合，覆盖从项目初始化 → 传感器配置 → 仿真执行 → 数据验证的完整工作流。

## Skills 概览

| Skill | 作用 | 典型触发时机 |
|-------|------|-------------|
| `lidar-converter` | LiDAR 产品手册 → aiSim 仿真配置（扫描模式 + 传感器配置） | 拿到新 LiDAR 手册需要生成 aiSim 配置 |
| `camera-converter` | 相机标定参数（YAML）→ aiSim Camera 配置 JSON | 需要更新/生成相机内参外参配置 |
| `radar-convertor` | aiSim Radar 配置/导出 → RadarService MCAP，并与真实 MCAP 做结构和字段分布对标 | 需要让算法直接回放仿真 radar 数据 |
| `aisim-executor` | 执行 aiSim 仿真、导出传感器数据、触发验证 | 配置生成后需要端到端验证 |
| `init-toolchain` | 初始化 aiSim 工具链项目骨架 | 从零开始创建新的工具链项目 |
| `new-plugin` | 创建传感器/执行器插件脚手架 | 需要添加新的 camera/lidar/radar 插件 |
| `new-client` | 创建客户端应用脚手架 | 需要添加新的 runner/configurator/monitor 等应用 |
| `aisim-map-importer` | 将中文供应商 GPKG / PLY 点云导入 aiSim（含 OSM 路网构建、atlas 修复、gs3d.json 生成） | 拿到新采集场景需要导入 aiSim 地图 |
| `aisim-hil-mcap-packager` | aiSim HIL 导出 → 对齐真实路测 MCAP 的 raw sensor / vehicle 回放包，并生成字段级自检报告 | 需要把仿真数据交付给算法回放时 |

## 推荐工作流

### LiDAR 配置与验证（完整链路）

```
lidar-converter                aisim-executor
┌──────────────────┐         ┌──────────────────────┐
│ 手册 → config     │────────▶│ 仿真 → LAS 导出       │
│       → pattern   │         │      → 验证报告       │
│       → checklist │         └──────────────────────┘
└──────────────────┘
```

1. **lidar-converter** 将 LiDAR 手册转为 `_config.json` + `_pattern.json`
2. **aisim-executor** 加载配置执行仿真，导出 LAS 点云并验证

### Camera 配置与验证（三层验证体系）

```
camera-converter              aisim-executor
┌──────────────────┐         ┌──────────────────────┐
│ YAML → JSON       │────────▶│ 仿真 → 图像导出       │
│      → 参数验证   │         │      → 畸变检测       │
└──────────────────┘         └──────────────────────┘
```

1. **camera-converter** 从标定 YAML 更新 Camera 配置 JSON（第一层验证）
2. **aisim-executor** 导出图像（第二层验证）+ 畸变检测（第三层验证）

### Radar 配置、MCAP 转换与真实数据对标

```
radar-convertor              aisim-executor              radar-convertor
┌──────────────────┐       ┌──────────────────────┐     ┌──────────────────────┐
│ 6 路 Advanced     │──────▶│ 仿真 → JSON 导出      │────▶│ RadarService MCAP     │
│ radar 配置生成    │       │                      │     │ 结构验证 + 真实对标    │
└──────────────────┘       └──────────────────────┘     └──────────────────────┘
```

1. **radar-convertor** 基于 AdvancedRadarRaytracer 模板生成 6 路 radar 配置，重点对齐外参、帧率、FOV、距离范围和 RCS/SNR 输出能力
2. **aisim-executor** 执行仿真并导出每路 radar JSON
3. **radar-convertor** 将 aiSim `captured_objects`/`targets` 转成 `hv_sensor_msgs/msg/RadarService` MCAP
4. **radar-convertor** 验证 6 路 topic、800 帧、2012B payload、schema 名称，并输出与真实 MCAP 的字段分布对比报告

当前版本能完成结构对齐和基础内容映射，但仍依赖逆向得到的 RadarService 格式；真实雷达内容分布、噪声模型、外参标定精度需要结合实车数据继续校准。


### HIL MCAP 打包与交付自检

```
aisim-executor / GUI export        aisim-hil-mcap-packager
┌──────────────────────────┐     ┌──────────────────────────────┐
│ camera-only / no-camera  │────▶│ MCAP build + validation       │
│ split export             │     │ CDR/time/calibration/dry-run  │
└──────────────────────────┘     └──────────────────────────────┘
```

1. **aisim-executor** 或 aiSim GUI 分别导出 camera-only 与 no-camera 数据，避免 full perception 在重地图上耗尽 VRAM。
2. **aisim-hil-mcap-packager** 使用真实 MCAP 合同、IMU 外参、recorder 标定元数据和 per-camera CRF 策略打包 MCAP。
3. 交付前必须通过结构 validator、time/calibration validator、字段级 dry-run 和 HTML 自检报告。

### 新项目初始化

```
init-toolchain  →  new-plugin  →  new-client  →  业务逻辑开发
     ↓                  ↓              ↓
   项目骨架        传感器插件      客户端应用
```

### 地图导入（GPKG + 3DGS 点云）

```
aisim-map-importer
┌─────────────────────────────────────────────────────┐
│ 中文 GPKG ──► 标准 GPKG (convert_chinese_gpkg.py)    │
│ 无 GPKG    ──► OSM GeoJSON ──► GPKG (convert_geojson_gpkg.py) │
│ HPGS PLY  ──► 注入 Offset comment (patch_ply_sh.py) │
│           ──► gs3d.json (generate_gs3d_json.py)     │
│           ──► atlas_cmd_tool  ──► aiSim 资产目录     │
└─────────────────────────────────────────────────────┘
```

1. **convert_chinese_gpkg.py** 将中文图层名转为 aiSim 英文标准层（Paths / RoadShapes / RoadMarks / Crosswalks / MapInfo）
2. **convert_geojson_gpkg.py** 从 Overpass Turbo GeoJSON 构建最小可用 GPKG（无中文 GPKG 时的回退路径）
3. **patch_ply_sh.py** 为缺少 `f_rest_*` 系数的 PLY 补零填充 SH degree-3
4. **generate_gs3d_json.py** 计算 RT 矩阵（HPGS Offset + 地面 z）生成 `gs3d.json`
5. `atlas_cmd_tool` 完成最终导入并输出 aiSim 资产

## 已验证案例

| 传感器 | 型号 | 类型 | 验证状态 |
|--------|------|------|---------|
| LiDAR | Hesai ATX100 | Flash (1D 摆镜) | ✅ 100% 匹配率 |
| LiDAR | Hesai Pandar64 | Rotating (机械旋转) | ✅ 99.91% 匹配率 |
| Camera | Bosch 11 相机 | Pinhole + Fisheye | ✅ 三层验证通过 |
| Radar | FVR30/CVR30 对标 | AdvancedRadarRaytracer → RadarService MCAP | ⚠️ 结构对齐，内容分布待实车校准 |
| HIL MCAP | raw camera/lidar/radar/vehicle | aiSim export → ROS2-profile MCAP | ✅ 结构、时间、CDR、dry-run 自检通过 |

## 安装

将需要的 Skill 目录复制到你的 AI Agent Skills 目录即可：

```bash
# 安装单个 Skill
cp -R skills/aisim/lidar-converter ~/.claude/skills/

# 或安装全部
cp -R skills/aisim/* ~/.claude/skills/
```

## 前置依赖

- **aiSim 5.9+**：仿真引擎
- **tc_core toolchain**：`aisim_client` 命令行工具
- **Python 3.8+**：脚本运行环境
- **Vulkan GPU**：LiDAR 光线追踪必需
