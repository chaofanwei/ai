---
name: prometheus-query
description: 查询VRS内部 Prometheus 指标。用于写 PromQL、调用 Prometheus HTTP API、查询 instant/range 指标、解析 vector/matrix 返回、排查监控数据。触发场景：Prometheus 查询、promql、PromQL、普罗查询、指标查询、query_range、/api/v1/query。
---

# Prometheus 查询

用于查询VRS监控指标的 Prometheus 服务。

## 先选入口

| 场景 | 推荐方式 |
|---|---|
| 直接查当前值 | `GET /api/v1/query` |
| 查一段时间的序列、峰值、均值 | `GET /api/v1/query_range` |

## 数据源

| 名称 | server/base |
|---|---|
| dash 数据源（主站和国际站 dash 指标都在这里） | `starmap.qiyi.domain/ops/prometheus/dash` |
| 直播专用数据源 | `starmap.qiyi.domain/ops/prometheus` |

完整接口由 `http://<server>/api/v1/query` 或 `http://<server>/api/v1/query_range` 组成。

dash 数据源同时包含主站和国际站。按 `dc` 区分：

| 范围 | dc 过滤 |
|---|---|
| 主站/大陆 | `dc!~"singapore.*|xjp|sgp-.*|iqiyi-use.*"` |
| 国际站 | `dc=~"singapore.*|xjp|sgp-.*|iqiyi-use.*"` |

## HTTP API

### Instant Query

```bash
curl -G 'http://starmap.qiyi.domain/ops/prometheus/dash/api/v1/query' \
  --data-urlencode 'query=sum(irate(http_request_duration_seconds_count{api="dash"}[5m]))' \
  --data-urlencode 'time=1783480800'
```

参数：

| 参数 | 说明 |
|---|---|
| `query` | PromQL，必须 URL encode；用 `curl -G --data-urlencode` 最稳 |
| `time` | 秒级 Unix 时间戳；不传时 Prometheus 使用当前时间 |

返回是 vector，取值路径：

```text
data.result[].metric
data.result[].value[0]  # timestamp
data.result[].value[1]  # string value
```

### Range Query

```bash
curl -G 'http://starmap.qiyi.domain/ops/prometheus/dash/api/v1/query_range' \
  --data-urlencode 'query=sum(irate(http_request_duration_seconds_count{api="dash"}[5m])) by (dc)' \
  --data-urlencode 'start=1783477200' \
  --data-urlencode 'end=1783480800' \
  --data-urlencode 'step=60'
```

参数：

| 参数 | 说明 |
|---|---|
| `start` / `end` | 秒级 Unix 时间戳 |
| `step` | 采样间隔；可用秒数如 `60`、`300`，也可用 Prometheus duration 字符串如 `1m`、`5m` |
| `timeout` | 可选；长窗口查询可传如 `15m` |

返回是 matrix，取值路径：

```text
data.result[].metric
data.result[].values[][0]  # timestamp
data.result[].values[][1]  # string value
```

## 常用 PromQL 模式

QPS：

```promql
sum(irate(http_request_duration_seconds_count{api="dash"}[5m])) by (dc)
```

平均耗时毫秒：

```promql
sum(irate(http_request_duration_seconds_sum{api="dash"}[5m])) * 1000
/
sum(irate(http_request_duration_seconds_count{api="dash"}[5m]))
```

错误码比例万分比：

```promql
10000 * sum(irate(http_requests_code_st_total{api="dash", st="800"}[2m])) by (instance)
/
sum(irate(http_requests_code_st_total{api="dash"}[2m])) by (instance)
```

机器 CPU 使用率：

```promql
(1 - avg(irate(node_cpu_seconds_total{mode="idle"}[10m])) by (instance)) * 100
```

## 引用资料

- 需要查询 Dash 主站/国际站服务 qps、耗时、错误码指标、TOP 数据、ptid/src 维度、实例级别、运行状态或播放流程时，读取 [dash-main-grafana.md](references/dash-main-grafana.md)。
- 需要查询直播服务 Grafana 的总体、实例维度、熔断指标时，读取 [live-grafana.md](references/live-grafana.md)。


## 排查流程

1. 明确 server：dash 主站/国际站指标默认优先用 `/ops/prometheus/dash`，live 指标用 `/ops/prometheus`。
2. 先做 instant query 验证 PromQL 是否有数据，再扩展到 range query。
3. range query 的窗口和 step 要匹配问题粒度：分钟级排查常用 `step=60` 或 `1m`；较长窗口可用 `300` 或 `5m` 降低返回量。
4. 聚合时保留必要 label，例如 `by (dc)`、`by (instance)`、`by (pod)`；后续解析依赖这些 label。
5. 解析数值时使用 `value[1]` 或 `values[][1]`，它们是字符串；注意空数组、`NaN`、`+Inf`、`-Inf`。
