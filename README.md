# oh-my-skills

一个面向研究型 Agent 工作流 + aiSim 仿真工具链的轻量分享仓库，打包了我在 `3DGS_ADAS_HiL_Tier1` 项目里实际使用的一组 Skills 与 MCP 用法，重点不是”工具清单”，而是”让 Agent 在 Plan 模式下自主编排能力”。

## 仓库目标

- 快速分享一套可复用的研究工作流资产
- 让同事能直接看到每个 Skill 的职责与触发时机
- 提供一个可落地的 MCP 配置模板，而不是把密钥直接暴露出去
- 用 `3DGS_ADAS_HiL_Tier1` 作为真实案例说明产物链路

## 包含内容

```text
oh-my-skills/
├── README.md
├── .gitignore
├── skills/
│   ├── aisim/
│   │   ├── README.md
│   │   ├── aisim-executor/SKILL.md
│   │   ├── lidar-converter/SKILL.md
│   │   ├── camera-converter/SKILL.md
│   │   ├── init-toolchain/SKILL.md
│   │   ├── new-plugin/SKILL.md
│   │   └── new-client/SKILL.md
│   ├── question-refiner/SKILL.md
│   ├── got-controller/SKILL.md
│   ├── research-executor/SKILL.md
│   ├── synthesizer/SKILL.md
│   ├── citation-validator/SKILL.md
│   └── patent-architect/
│       ├── README.md
│       └── SKILL.md
├── mcp/
│   └── grok-search/
│       ├── README.md
│       └── .env.example
└── docs/
    └── 3DGS_ADAS_HiL_Tier1-case-study.md
```

## 这套工作流解决什么问题

直接问模型时，复杂研究通常会遇到这些问题：

- 问题边界不稳，回答容易跑偏
- 推理路径单一，覆盖面不足
- 外部信息不够新，尤其是法规、论文、行业动态
- 输出常常停留在“答案”，没有沉淀成可交付物

把 Skill 和 MCP 接入 Agent 工作流之后，推荐的主链路是：

`用户给出研究目标 -> Agent 进入 Plan 模式 -> Skills 负责问题澄清/拆分/执行/综合/校验 -> MCP 在需要外部事实时补证 -> 生成结构化交付物`

## Included Skills

### aiSim 工具链

| Skill | 作用 | 典型触发时机 |
|---|---|---|
| `lidar-converter` | LiDAR 手册 → aiSim 仿真配置（扫描模式 + 传感器配置） | 拿到新 LiDAR 手册需要生成配置 |
| `camera-converter` | 相机标定参数 → aiSim Camera 配置 JSON | 更新/生成相机内参外参配置 |
| `aisim-executor` | 执行 aiSim 仿真、导出传感器数据、触发验证 | 配置生成后需要端到端验证 |
| `init-toolchain` | 初始化 aiSim 工具链项目骨架 | 从零创建新工具链项目 |
| `new-plugin` | 创建传感器/执行器插件脚手架 | 添加 camera/lidar/radar 等插件 |
| `new-client` | 创建客户端应用脚手架 | 添加 runner/configurator 等应用 |

### 研究工作流

| Skill | 作用 | 典型触发时机 |
|---|---|---|
| `question-refiner` | 把模糊问题变成结构化研究任务 | 用户只有方向，没有明确边界 |
| `got-controller` | 把单链路研究改成多分支研究 | 主题复杂、需要兼顾广度与深度 |
| `research-executor` | 执行完整研究流程并产出目录化结果 | 问题边界已经明确 |
| `synthesizer` | 把多路结果收口成统一叙事 | 多个子研究已经完成 |
| `citation-validator` | 检查事实与引用质量 | 报告定稿前、对外分享前 |
| `patent-architect` | 做专利挖掘、可专利性评估和中文专利材料整理 | 需要从项目或方案里提炼创新点时 |

## Included MCP

| MCP | 作用 | 在链路里的位置 |
|---|---|---|
| `grok-search` | 获取时间敏感信息、外部证据、实时搜索结果 | Agent 判断“需要外部事实”时调用 |

## 快速使用

### 研究工作流

1. 把 `skills/` 下需要的目录拷贝到你的 Skill 目录。
2. 参照 `mcp/grok-search/.env.example` 配置 MCP，不要提交真实密钥。
3. 给 Agent 一个研究目标，让它先做计划，再决定是否调用这些 Skill 和 MCP。
4. 参考 `docs/3DGS_ADAS_HiL_Tier1-case-study.md` 理解整套工作流是如何长成一套交付物的。
5. 如果你要做研发成果沉淀或专利预研，直接查看 `skills/patent-architect/`。

### aiSim 工具链

1. 安装 aiSim Skills：`cp -R skills/aisim/* ~/.claude/skills/`
2. 按照 `lidar-converter → aisim-executor` 链路完成 LiDAR 配置与端到端验证
3. 或按照 `camera-converter → aisim-executor` 链路完成 Camera 配置与三层验证
4. 新项目使用 `init-toolchain → new-plugin → new-client` 快速搭建工具链骨架
5. 详见 `skills/aisim/README.md`

## 安全说明

- 本仓库只保留 **脱敏模板**，不包含任何真实 API Key。
- 如果你要继续扩展新的 MCP，请优先提交配置模板和说明文档，不要提交本地密钥文件。
- 如果你要分享到团队外部，先确认 Skill 内容里没有公司特定路径、客户名称或内部文档链接。

## 推荐分享方式

- 面向工程师例会：先讲“为什么直接问模型不够”，再讲“Agent 如何自主编排 Skill 与 MCP”
- 面向团队落地：直接从 `question-refiner + research-executor + citation-validator + 一个搜索型 MCP` 的最小闭环开始
- 面向新同学：先看案例文档，再看具体 Skill
- 面向创新管理或专利预研：补充 `patent-architect`，把“研究结论”继续延伸到“创新点沉淀”
