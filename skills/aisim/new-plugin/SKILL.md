---
name: new-plugin
description: 创建aiSim工具链的新传感器/执行器插件。生成完整的插件目录结构，包括CMakeLists.txt、头文件、源文件、消息定义和代理接口。当用户需要添加新的camera/lidar/radar/gnss等传感器插件时使用。
---

# new-plugin（aiSim插件生成器）

## 快速使用

```bash
# 基本用法
/aisim:new-plugin <plugin_type> <plugin_name> <namespace> [target_dir]

# 示例
/aisim:new-plugin camera hdmi_camera bosch::sensors /path/to/toolchain/plugins/sensors
/aisim:new-plugin lidar my_lidar example::sensors
/aisim:new-plugin radar can_radar senseauto::sensors
```

## 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| plugin_type | 是 | 插件类型 | camera, lidar, radar, gnss, custom |
| plugin_name | 是 | 插件名称（小写下划线） | hdmi_camera, my_lidar |
| namespace | 是 | C++命名空间 | bosch::sensors, example::sensors |
| target_dir | 否 | 目标目录 | 默认为当前目录 |

## 生成的文件结构

```
{target_dir}/{plugin_name}/
├── CMakeLists.txt
├── include/{namespace_path}/{plugin_name}/
│   └── {plugin_name}_sensor.h
├── interface/{namespace_path}/{plugin_name}/interface/
│   ├── {plugin_name}_messages.h
│   └── {plugin_name}_proxy.h
└── src/
    ├── {plugin_name}_sensor.cpp
    └── {plugin_name}_factory.cpp
```

## 插件类型特性

### camera
- 基类: `AsyncInitSensor`
- 输出: `ColorImage`, `DepthImage`
- 依赖: `aisim::resources_camera_interface`

### lidar
- 基类: `AsyncInitSensor`
- 输出: `PointCloud`
- 依赖: `aisim::resources_lidar_interface`

### radar
- 基类: `AsyncInitSensor`
- 输出: `RadarDetections`
- 依赖: `aisim::resources_radar_interface`

### gnss
- 基类: `SimpleSensor`
- 输出: `GNSSData`
- 依赖: `aisim::resources_gnss_interface`

### custom
- 基类: 用户指定
- 输出: 用户定义
- 依赖: 最小依赖集

## 生成的代码模板

### CMakeLists.txt 模板
```cmake
add_toolchain_plugin(
    {toolchain_name}_sensors_{plugin_name}
    INTERFACE_HEADERS
        interface/{namespace_path}/{plugin_name}/interface/{plugin_name}_messages.h
        interface/{namespace_path}/{plugin_name}/interface/{plugin_name}_proxy.h
    INTERFACE_LINK_LIBRARIES
        aisim::sensors_common_interface
    LIB_HEADERS
        include/{namespace_path}/{plugin_name}/{plugin_name}_sensor.h
    SOURCES
        src/{plugin_name}_sensor.cpp
        src/{plugin_name}_factory.cpp
    LINK_LIBRARIES
        PUBLIC
            aisim::network
            aisim::logger
            aisim::scheduler
            aisim::sensors_common
            aisim::sensors_common_internal_interface
            aisim::resources_{plugin_type}_interface
            aisim::simulation_internal_interface
            aisim::ego_vehicle_internal_interface
)
```

### 消息定义模板 (messages.h)
```cpp
#pragma once
#include <aimotive/simulator/network/interface/message_templates.h>
#include <aimotive/simulator/sensors/common/interface/common_messages.h>

namespace {namespace}::{plugin_name}::interface {

constexpr auto g_library_name = "{TOOLCHAIN_NAME}/{plugin_name}@{VERSION}";

enum class MessageType : std::uint32_t {
    INIT,
    SUBSCRIBE,
    GET_CONFIG,
    SENSOR_DATA
};

struct Config { /* 配置字段 */ };
struct InitRequest { std::optional<Config> m_config; };
struct InitResponse { std::string m_error_message; };
struct SensorCaptureData { /* 输出数据 */ };

}
```

## 使用流程

1. 执行skill生成插件框架
2. 根据需求修改Config结构体
3. 实现Capture和ProcessDataAsync方法
4. 添加特定的硬件/协议集成代码
5. 更新父级CMakeLists.txt添加add_subdirectory

## 参考实现

- SXPF Camera: `/aiSim_proFrame_injection_toolchain/plugins/camera/`
- 官方示例: `/Release_5.9.0/Toolchains/example/src/.../plugins/sensors/simple_camera/`
