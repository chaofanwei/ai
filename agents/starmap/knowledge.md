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

## VRS Dash 小站请求耗时报警阈值

2026-05-18 定位过 `VRS_Dash_GROUP_DURATION_2`：

- 表：`promethues_alert_rules`
- 条件：`id = 313 and alertname = "VRS_Dash_GROUP_DURATION_2"`
- 用途：Dash 小站维度请求耗时 critical 报警。
- 阈值字段：`threshold`
- 当前阈值：`200.0`
- 线上 Prometheus 规则已加载为 `> 200`，规则文件在 `/data/prometheus/alerts/vrs_rules.yml`，规则组为 `VRS_rules`。
- `summary` / `description` 里仍写着 `超80ms`，只是报警文案不一致，不代表真实触发阈值还是 80。

查询 SQL：

```sql
select id, alertname, threshold, summary, description, status, update_time
from promethues_alert_rules
where id = 313;
```

## VRS OTT Dash QPS 环比波动报警增加绝对差值条件

2026-05-19 处理过 `VRS_OTT_Dash_QPS_DRASTIC_CHANGE`：

- 表：`promethues_alert_rules`
- 条件：`id = 211 and alertname = "VRS_OTT_Dash_QPS_DRASTIC_CHANGE"`
- 规则组：`VRS_rules`
- 原逻辑：只判断 Dash OTT 分机房 QPS 环比波动 `> 30`
- 新逻辑：`(环比波动 > 30) and (当前 5m QPS 与 offset 5m QPS 的绝对差值 > 50)`
- 修改方式：把原波动率表达式整体包成布尔条件放入 `promsql`，同时把绝对差值表达式作为最终数值，设置 `sign = ">"`、`threshold = 50.0`
- 文案同步改成“QPS环比波动超过30%且相差大于50”

执行记录：

- 操作时间：`2026-05-19 11:28:59`
- 操作人：`weichaofan`
- 历史记录：`st_sql_operation_history.id = 5`
- 影响行数：`1`
- 修改后调用 `/apis/promethues/reloadAlertRuleFile` 成功，返回 `A00000`

查询 SQL：

```sql
select id, alertname, promsql, sign, threshold, summary, description, show_content, status, group_name, update_time
from promethues_alert_rules
where id = 211 and alertname = "VRS_OTT_Dash_QPS_DRASTIC_CHANGE";
```

## VRS Dash 小站 QPS 环比波动报警差值阈值

2026-05-21 处理过 `VRS_Dash_GROUP_QPS_CHANGE`：

- 表：`promethues_alert_rules`
- 条件：`id = 309 and alertname = "VRS_Dash_GROUP_QPS_CHANGE"`
- 规则组：`VRS_rules`
- 逻辑：Dash 非 OTT 小站维度，当前 5m QPS 与 offset 5m QPS 环比波动 `> 40%`，并且绝对差值超过指定门槛。
- 本次修改：绝对差值门槛从 `> 50` 调整为 `> 100`；`threshold = 40.0` 保持不变。
- 注意：报警文案里的 `{{$value}}` 显示的是 PromQL 最终返回值。因为表达式前半段用了 `差值 > 100 and 百分比表达式`，Prometheus 在报警中可能展示匹配侧的绝对差值，容易被误读成百分比。

执行记录：

- 操作时间：`2026-05-21 09:25:47`
- 操作人：`weichaofan`
- 历史记录：`st_sql_operation_history.id = 8`
- 影响行数：`1`
- 修改后调用 `/apis/promethues/reloadAlertRuleFile` 成功，返回 `A00000 / OK`

查询 SQL：

```sql
select id, alertname, promsql, sign, threshold, status, group_name, update_time
from promethues_alert_rules
where id = 309 and alertname = "VRS_Dash_GROUP_QPS_CHANGE";
```
