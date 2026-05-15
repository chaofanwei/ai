# 巡检报告中的阈值调整方式

巡检报告里的 warning/critical 阈值来自巡检报警规则配置。忽略 `/prometheus/patrol/alert/update` 页面接口，按没有该接口处理。

## 修改入口

使用数据库查询接口定位数据，最终修改通过数据库修改接口 `/apis/db/execute` 执行。最终 execute 必须先给出 SQL 和影响范围，等用户确认后再执行。

## 操作步骤

1. 先用数据库查询接口定位要改的 `patrol_alert_manager.id`，条件一般来自报告里的服务站点、指标、机房。
2. 查询当前阈值，确认只命中目标规则。
3. 生成精确的 `UPDATE` SQL，说明会修改的表、条件、旧值和新值。
4. 等用户确认后，调用 `/apis/db/execute` 执行。
5. 再次查询确认 `critical` 已生效。

## 相关数据库接口

查询接口：

```bash
curl -X POST "http://starmap.qiyi.domain/apis/db/query" \
  -H "Content-Type: application/json" \
  -d '{"sql":"select 1 as ok"}'
```

修改 SQL 接口：

```bash
curl -X POST "http://starmap.qiyi.domain/apis/db/execute" \
  -H "Content-Type: application/json" \
  -d '{"sql":"update table_name set column_name = value where id = 1"}'
```

注意：调整巡检报警阈值时，查询可以直接执行；最终 `/apis/db/execute` 修改必须等用户确认。

## execute 登录态要求

`/apis/db/query` 可以直接通过 curl 查询；`/apis/db/execute` 会在 controller 中调用 `getUserName(request)`，从 session 的 `adminUser` 取用户名。没有登录态的 curl 调用会返回系统错误 `A00101`，且不会写入 `st_sql_operation_history`。

因此执行修改时需要使用已登录浏览器的 session cookie，或让已登录用户在可用环境中执行对应 curl。

## VRS 点播国际站 304 qpaas 阈值记录

2026-05-08 已处理过一次：VRS 巡检报告里 `点播国际站 / 304 / inter-qpaas-ali` 和 `inter-qpaas-hw` 连续 3 日超过 Critical 阈值，目标是把 critical 从 `100.0` 调到 `1000.0`。

最终定位：

- 表：`patrol_metrics_info_rules_v2`
- 条件：`id = 347 and service = "dash" and name = "st-304"`
- 旧规则里没有 `inter-qpaas-ali` / `inter-qpaas-hw`，这两个机房会命中 `default`，即 `warning=50.0`、`critical=100.0`。
- 修改方式不是改 `default`，而是新增两条专属规则，避免影响其他默认机房。

新增后的关键规则：

```json
{"name":"inter-qpaas-ali","warning":50.0,"critical":1000.0}
{"name":"inter-qpaas-hw","warning":50.0,"critical":1000.0}
```

执行记录：

- 操作时间：`2026-05-08 16:33:51`
- 操作人：`weichaofan`
- 历史记录：`st_sql_operation_history.id = 4`
- 影响行数：`1`

注意：`PatrolRulesCacheService` 规则缓存每 10 分钟刷新一次，修改后报告/巡检侧可能需要等待缓存刷新生效。
