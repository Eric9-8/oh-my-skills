---
name: new-client
description: 创建aiSim工具链的客户端应用（runner/configurator/monitor/exporter等）。生成完整的客户端目录结构和代码框架。当用户需要添加新的客户端应用时使用。
---

# new-client（aiSim客户端生成器）

## 快速使用

```bash
# 基本用法
/aisim:new-client <app_type> <app_name> [target_dir]

# 示例
/aisim:new-client runner my_runner /path/to/toolchain/clients/apps
/aisim:new-client configurator my_configurator
/aisim:new-client monitor sensor_monitor
```

## 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| app_type | 是 | 应用类型 | runner, configurator, monitor, exporter, subscriber |
| app_name | 是 | 应用名称 | my_runner, sensor_monitor |
| target_dir | 否 | 目标目录 | 默认为当前目录 |

## 应用类型说明

### runner
- 功能：运行仿真循环，处理传感器数据
- 基类：`RunnerApplication`
- 钩子：PreStart, PostStart, PreStep, PostStep

### configurator
- 功能：配置和启动仿真
- 基类：`ConfiguratorApplication`
- 特性：注册传感器配置器

### monitor
- 功能：实时监控传感器输出
- 基类：`MonitorApplication`
- 特性：可视化数据流

### exporter
- 功能：导出传感器数据到文件
- 基类：`ExporterApplication`
- 特性：支持多种格式

### subscriber
- 功能：订阅特定传感器数据
- 基类：自定义
- 特性：灵活的数据处理

## 生成的文件结构

```
{target_dir}/{app_name}/
├── CMakeLists.txt
└── {app_name}.cpp
```

## 生成的代码模板

### Runner模板
```cpp
#include <runner_application.h>

class MyRunner : public aim::sim::runner_application::RunnerApplication {
public:
    using RunnerApplication::RunnerApplication;
private:
    void PreStart() override { }
    void PostStart() override { }
    void PreStep() override { }
    void PostStep() override { }
};

int main(int argc, char** argv) {
    MyRunner runner{ argc, argv };
    return runner.Run();
}
```

### Configurator模板
```cpp
#include <configurator_application.h>
#include <sensor_proxy.h>

int main(int argc, char** argv) {
    aim::sim::configurator_application::ConfiguratorApplication app(argc, argv);
    app.SetConfiguratorCreatorForAimLikeSensorWithSchema<SensorProxy>("sensor_type");
    return app.Run();
}
```

## 使用流程

1. 执行skill生成客户端框架
2. 根据需求添加传感器代理包含
3. 实现具体的业务逻辑
4. 更新父级CMakeLists.txt添加add_subdirectory
5. 更新copy_clients_dependencies添加新应用

## 参考实现

- SXPF Runner: `/aiSim_proFrame_injection_toolchain/clients/apps/runner/`
- 官方示例: `/Release_5.9.0/Toolchains/example/src/.../clients/apps/my_runner/`
