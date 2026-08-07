# tiros 拨测对比 Agent

在本目录启动 cursor-agent，用于分析 **tiros-dial 线上技术对比差异**。

## 启动

```bash
cd ~/ai/agents/tiros
cursor-agent
```

然后直接描述问题，例如：

- 「看下 dash 主站技术对比 `JSON.data.content.croIds`」
- 「国际站 `video[X]._selected` 为什么不一致」

## 目录

| 路径 | 作用 |
|--|--|
| `AGENTS.md` | 角色、权限、工作方式 |
| `skills/dial-diff-analyze.md` | 连库/查样本/重放/结论模板（核心） |
| `tiros/` | tiros 源码副本（分析用） |
| `tiros/tiros-dial/Readme-diff-check.md` | 完整排查手册 |
| `knowledge.md` | 已确认知识点 |
| `.cursor/rules/` / `.cursor/skills/` | 让 cursor-agent 自动加载 |
| `temp/` | 临时脚本与中间结果 |

源码在 `./tiros/`，agent 配置在本层，与 `~/ai/agents/starmap`（源码在 `./star-map`）同一模式。
