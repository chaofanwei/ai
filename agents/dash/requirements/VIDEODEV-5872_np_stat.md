# VIDEODEV-5872 统计np各值的占比信息及端信息

- PMS标题：统计np各值的占比信息及端信息
- PMS链接：http://pms.qiyi.domain/browse/VIDEODEV-5872
- 修改时间：2026-07-17 09:59:33 CST
- Codex session Id：当前环境未暴露可读取的 session id

## 背景

需要统计 dash 起播参数 `np` 各值的请求次数，并按端信息统计对应次数。

## 改动

1. 在 `p911/rules/post/log.lua` 的通用日志阶段，把请求参数 `np` 写入 `ngx.ctx.np`，与已有 `ngx.ctx.pf` 一起供 log 阶段 metrics 使用。
2. 在 `metrics/metrics.lua` 新增 Prometheus counter：
   - 指标名：`http_dash_np_pf_total`
   - label：`np`, `pf`
   - 含义：统计 dash 请求中各 `np` 值在各 `pf` 端上的请求次数。

## 实现过程

1. 按需求从最新 `master` 创建分支 `fan_5872_np_stat`。
2. 用户确认统计维度只需要 `np + pf`。
3. 采用已有 metrics 链路，不改 dash 业务流程和响应结构。

## 验证

1. `luac -p vis-rule-engine/src/main/lua/p911/rules/post/log.lua` 通过。
2. `luac -p vis-rule-engine/src/main/lua/metrics/metrics.lua` 通过。
3. 已检查 diff，仅涉及 `np/pf` metrics 采集，不改 dash 响应结构。
