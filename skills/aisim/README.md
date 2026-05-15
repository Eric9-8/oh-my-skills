# aiSim Skills

面向 aiSim 仿真平台的工具链 Skills 集合，覆盖从项目初始化 → 传感器配置 → 仿真执行 → 数据验证的完整工作流。

## Skills 概览

| Skill | 作用 | 典型触发时机 |
|-------|------|-------------|
| `lidar-converter` | LiDAR 产品手册 → aiSim 仿真配置（扫描模式 + 传感器配置） | 拿到新 LiDAR 手册需要生成 aiSim 配置 |
| `camera-converter` | 相机标定参数（YAML）→ aiSim Camera 配置 JSON | 需要更新/生成相机内参外参配置 |
| `aisim-executor` | 执行 aiSim 仿真、导出传感器数据、触发验证 | 配置生成后需要端到端验证 |
| `init-toolchain` | 初始化 aiSim 工具链项目骨架 | 从零开始创建新的工具链项目 |
| `new-plugin` | 创建传感器/执行器插件脚手架 | 需要添加新的 camera/lidar/radar 插件 |
| `new-client` | 创建客户端应用脚手架 | 需要添加新的 runner/configurator/monitor 等应用 |

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

### 新项目初始化

```
init-toolchain  →  new-plugin  →  new-client  →  业务逻辑开发
     ↓                  ↓              ↓
   项目骨架        传感器插件      客户端应用
```

## 已验证案例

| 传感器 | 型号 | 类型 | 验证状态 |
|--------|------|------|---------|
| LiDAR | Hesai ATX100 | Flash (1D 摆镜) | ✅ 100% 匹配率 |
| LiDAR | Hesai Pandar64 | Rotating (机械旋转) | ✅ 99.91% 匹配率 |
| Camera | Bosch 11 相机 | Pinhole + Fisheye | ✅ 三层验证通过 |

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
