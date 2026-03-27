# oh-my-skills

一个面向研究型 Agent 工作流的轻量分享仓库，打包了我在 `3DGS_ADAS_HiL_Tier1` 项目里实际使用的一组 Skills 与 MCP 用法，重点不是“工具清单”，而是“让 Agent 在 Plan 模式下自主编排能力”。

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
│   ├── question-refiner/SKILL.md
│   ├── got-controller/SKILL.md
│   ├── research-executor/SKILL.md
│   ├── synthesizer/SKILL.md
│   └── citation-validator/SKILL.md
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

| Skill | 作用 | 典型触发时机 |
|---|---|---|
| `question-refiner` | 把模糊问题变成结构化研究任务 | 用户只有方向，没有明确边界 |
| `got-controller` | 把单链路研究改成多分支研究 | 主题复杂、需要兼顾广度与深度 |
| `research-executor` | 执行完整研究流程并产出目录化结果 | 问题边界已经明确 |
| `synthesizer` | 把多路结果收口成统一叙事 | 多个子研究已经完成 |
| `citation-validator` | 检查事实与引用质量 | 报告定稿前、对外分享前 |

## Included MCP

| MCP | 作用 | 在链路里的位置 |
|---|---|---|
| `grok-search` | 获取时间敏感信息、外部证据、实时搜索结果 | Agent 判断“需要外部事实”时调用 |

## 快速使用

1. 把 `skills/` 下需要的目录拷贝到你的 Skill 目录。
2. 参照 `mcp/grok-search/.env.example` 配置 MCP，不要提交真实密钥。
3. 给 Agent 一个研究目标，让它先做计划，再决定是否调用这些 Skill 和 MCP。
4. 参考 `docs/3DGS_ADAS_HiL_Tier1-case-study.md` 理解整套工作流是如何长成一套交付物的。

## 安全说明

- 本仓库只保留 **脱敏模板**，不包含任何真实 API Key。
- 如果你要继续扩展新的 MCP，请优先提交配置模板和说明文档，不要提交本地密钥文件。
- 如果你要分享到团队外部，先确认 Skill 内容里没有公司特定路径、客户名称或内部文档链接。
