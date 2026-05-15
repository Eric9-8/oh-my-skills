---
name: init-toolchain
description: 初始化一个新的aiSim工具链项目骨架。生成完整的项目目录结构，包括根级CMakeLists.txt、plugins、clients、thirdparties等目录。当用户需要从零开始创建新的aiSim工具链项目时使用。
---

# init-toolchain（aiSim工具链初始化器）

## 快速使用

```bash
# 基本用法
/aisim:init-toolchain <toolchain_name> <sdk_version> [target_dir]

# 示例
/aisim:init-toolchain Bosch_toolchain 5.9.0 /path/to/projects
/aisim:init-toolchain SenseAuto_toolchain 5.7.0
```

## 参数说明

| 参数 | 必填 | 说明 | 示例 |
|------|------|------|------|
| toolchain_name | 是 | 工具链名称 | Bosch_toolchain, SenseAuto_toolchain |
| sdk_version | 是 | aiSim SDK版本 | 5.9.0, 5.7.0 |
| target_dir | 否 | 目标目录 | 默认为当前目录 |

## 生成的目录结构

```
{toolchain_name}/
├── CMakeLists.txt              # 根级构建配置
├── cmake/
│   ├── postinst                # Debian安装后脚本
│   └── postrm                  # Debian卸载后脚本
├── thirdparties/
│   └── CMakeLists.txt          # 第三方依赖
├── plugins/
│   ├── CMakeLists.txt
│   └── sensors/
│       └── CMakeLists.txt      # 传感器插件目录
├── clients/
│   ├── CMakeLists.txt
│   ├── apps/
│   │   └── CMakeLists.txt      # 客户端应用目录
│   └── data/
│       ├── scenarios/          # 场景配置
│       ├── sensor_configurations/  # 传感器配置
│       └── segmentation_settings/  # 分割设置
└── doxygen/                    # 文档生成（可选）
    └── CMakeLists.txt
```

## 根级CMakeLists.txt功能

1. **SDK加载**：通过FetchContent从URL加载aiSim SDK
2. **项目定义**：设置项目名称、版本、编译宏
3. **子目录编译**：按顺序编译thirdparties → plugins → clients
4. **CPack打包**：生成clients和plugins两个独立包

## 使用流程

1. 执行skill生成项目骨架
2. 使用 `aisim:new-plugin` 添加传感器插件
3. 使用 `aisim:new-client` 添加客户端应用
4. 配置SDK_URI并构建项目

## 构建命令

```bash
cd {toolchain_name}
mkdir build && cd build
cmake .. -DSDK_URI=file:///path/to/aiSim_sdk-{version}.tar.xz
make -j$(nproc)
```

## 参考项目

- SXPF工具链: `/aiSim_proFrame_injection_toolchain/`
- 官方示例: `/Release_5.9.0/Toolchains/example/src/toolchain_example_src-1.0.0/`
- UDP工具链: `/aiSim_upd_toolchain/`
