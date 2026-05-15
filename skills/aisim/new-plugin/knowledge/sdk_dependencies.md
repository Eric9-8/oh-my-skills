# aiSim SDK 依赖配置参考

本文档列出 aiSim 5.9 SDK 中各类型传感器插件的推荐依赖配置。

## 依赖来源

aiSim 插件的依赖来自两个包：
- `aisim::*` - 核心 SDK 库（通过 `find_package(aisim ... COMPONENTS sdk)` 加载）
- `tc_core::*` - 工具链核心库（通过 `find_package(tc_core ... COMPONENTS sdk)` 加载）

## 传感器类型依赖配置

### Camera 传感器

```cmake
INTERFACE_LINK_LIBRARIES
    aisim::sensors_common_interface

LINK_LIBRARIES
    PUBLIC
        aisim::network
        aisim::logger
        aisim::scheduler
        aisim::sensors_common
        aisim::sensors_common_internal_interface
        aisim::resources_camera_interface
        aisim::simulation_internal_interface
        aisim::ego_vehicle_internal_interface
        aisim::utils_formatters_internal_interface
        aisim::segmentation_settings
```

### LiDAR 传感器

```cmake
INTERFACE_LINK_LIBRARIES
    tc_core::lidar_sensor_interface

LINK_LIBRARIES
    PUBLIC
        aisim::network
        aisim::logger
        aisim::scheduler
        aisim::sensors_common
        aisim::sensors_common_internal_interface
        tc_core::lidar_sensor_interface
        aisim::simulation_internal_interface
        aisim::ego_vehicle_internal_interface
        aisim::utils_formatters_internal_interface
        aisim::segmentation_settings
        aisim::resources_lidar_raytracer
        aisim::sensor_api
```

### Radar 传感器

```cmake
INTERFACE_LINK_LIBRARIES
    aisim::sensors_common_interface
    aisim::resources_common_frustum_culling_interface
    aisim::resources_radar_target_provider_interface

LINK_LIBRARIES
    PUBLIC
        aisim::network
        aisim::logger
        aisim::sensor_api
        aisim::scheduler
        aisim::sensors_common
        aisim::sensors_common_internal_interface
        aisim::simulation_internal_interface
        aisim::ego_vehicle_internal_interface
        aisim::utils_formatters_internal_interface
        aisim::resources_common_frustum_culling
        aisim::resources_radar_target_provider
```

### GNSS/IMU/VMPS 传感器

```cmake
INTERFACE_LINK_LIBRARIES
    aisim::sensors_common_interface

LINK_LIBRARIES
    PUBLIC
        aisim::network
        aisim::logger
        aisim::sensor_api
        aisim::scheduler
        aisim::sensors_common
        aisim::sensors_common_internal_interface
        aisim::simulation_internal_interface
        aisim::ego_vehicle_internal_interface
        aisim::utils_formatters_internal_interface
```

### 简单/最小化传感器（参考官方示例）

如果你的传感器非常简单，可以只链接核心库：

```cmake
# 无需 INTERFACE_LINK_LIBRARIES

LINK_LIBRARIES
    tc_core::lidar_sensor  # 或 tc_core::camera_sensor 等
```

## 常见依赖说明

| Target | 说明 |
|--------|------|
| `aisim::sdk` | 自动添加，包含核心接口 |
| `aisim::network` | UDP/TCP 网络功能 |
| `aisim::logger` | 日志功能（SIM_INFO 等宏） |
| `aisim::scheduler` | 调度器 |
| `aisim::sensor_api` | 传感器 API（获取 Actor 等） |
| `aisim::sensors_common` | 传感器公共基类 |
| `aisim::simulation_internal_interface` | 仿真内部接口 |
| `aisim::ego_vehicle_internal_interface` | 自车内部接口 |
| `aisim::resources_lidar_raytracer` | LiDAR 光线追踪 |
| `aisim::resources_camera_interface` | Camera 资源接口 |
| `aisim::resources_radar_target_provider` | Radar 目标提供器 |
| `aisim::resources_common_frustum_culling` | 视锥剔除 |
| `tc_core::lidar_sensor_interface` | LiDAR 传感器接口 |
| `tc_core::camera_sensor_interface` | Camera 传感器接口 |

## ⚠️ 常见错误

### 1. 不存在的 target

以下 target 名称**不存在**，是常见的拼写错误：

| 错误名称 | 正确名称 |
|---------|---------|
| `aisim::sensors_lidar_interface` | `tc_core::lidar_sensor_interface` |
| `aisim::resources_lidar` | `aisim::resources_lidar_raytracer` |
| `aisim::sensors_camera_interface` | `tc_core::camera_sensor_interface` 或 `aisim::resources_camera_interface` |

### 2. 大小写敏感

CMake target 名称大小写敏感：
- ✅ `Bosch_toolchain::client_sdk`
- ❌ `bosch_toolchain::client_sdk`

项目名称必须与 `project()` 中定义的完全一致。

## 查找可用 Target

如果不确定某个 target 是否存在，可以在 SDK 的 cmake 文件中搜索：

```bash
grep -r "add_library.*::" build/aisim_sdk-src/opt/aiMotive/aisim-*/lib/cmake/
grep -r "add_library.*::" build/aisim_sdk-src/opt/aiMotive/toolchains/tc_core-*/lib/cmake/
```
