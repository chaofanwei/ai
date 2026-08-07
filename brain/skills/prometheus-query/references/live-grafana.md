# 直播 Grafana 指标速查

Grafana 看板参考：`直播总体监控`。本文件记录 `总体`、`实例维度`、`熔断` 分组中可通过 Prometheus 直接查询的直播指标。

主要数据源是直播 Prometheus：`starmap.qiyi.domain/ops/prometheus`。看板中 Prometheus 数据源名为 `Prometheus-2`。

通用过滤：

| 变量 | 含义 |
|---|---|
| `$src` | 流量来源：`qiyi`、`qiyi_qpaas`；`All`=`.*` |
| `$unit` | 单元 |
| `$dc` | 机房 |
| `$group` | 小站/分组 |
| `$instance` | 实例 |
| `$api_code` | 业务返回码 |
| `$mode` | 流量类型：`0`=正常流量，`1`=压测流量，`All`=`.*` |

直播核心 project：`project="VideoPlay-live-nginx1"`。

大陆看板常用过滤：`dc!~"singapore.*|sgp-.*|iqiyi-use.*"`；部分实例/缓存面板排除：`dc!~"singapore_aliyun|singapore_huawei|singapore_huaweiyun|ali-sg|intel-huawei"` ，要查国际站时刚好把dc反过来就行。

直播核心接口过滤：

```promql
api=~"/real_live_lp|/real_live_lc|/live/epg/|/jp/live|/live"
```

## 总体

| 面板/用途 | 指标与用法 |
|---|---|
| QPS、分机房 QPS | `nginx_http_request_api_duration_seconds_count`，`sum(irate(...[5m]))`；分机房 `by(dc)`，整体不分组 |
| 分小站 QPS | 同 QPS，加 `dc=~"$dc"`，按 `group` |
| 平均 QPS 分机房 | `avg by(dc)(sum(rate(nginx_http_request_api_duration_seconds_count[2m])) by(instance,dc))` |
| 平均 QPS 分小站 | `avg(sum(irate(nginx_http_request_api_duration_seconds_count[5m])) by(instance,group)) by(group)` |
| lp 类型 code 百分率 | `nginx_http_requests_api_code_total{type="lp"}`，按 `api_code` / 全量 `api_code`，乘 `100` |
| lc 类型 code 百分率 | `nginx_http_requests_api_code_total{type="lc"}`，按 `api_code` / 全量 `api_code`，乘 `100` |
| 直播 st 返回值 QPS | `nginx_http_requests_total`，`sum(irate(...[5m])) by(st)`；整体不分组 |
| 直播 st 返回值占比 | `nginx_http_requests_total`，按 `st` / 全量，乘 `100` |
| HTTP code 错误率 | `nginx_http_requests_total`，按 `status` / 全量，乘 `100` |
| 平均响应时间分机房 | `sum(rate(nginx_http_request_api_duration_seconds_sum[5m]) * 1000) by(dc) / sum(rate(nginx_http_request_api_duration_seconds_count[5m])) by(dc)` |
| 平均响应时间分小站 | 同平均响应时间，加 `dc=~"$dc"` 后按 `group` |
| P99 响应时间分机房 | `histogram_quantile(0.99, sum(rate(nginx_http_request_api_duration_seconds_bucket[5m])) by(le,dc)) * 1000` |
| P99 响应时间分小站 | 同 P99，加 `dc=~"$dc"` 后按 `group` |
| P9999 响应时间分机房 | `histogram_quantile(0.9999, sum(rate(nginx_http_request_api_duration_seconds_bucket[5m])) by(le,dc)) * 1000` |
| P9999 响应时间分小站 | 同 P9999，加 `dc=~"$dc"` 后按 `group` |
| 各接口 P99 响应时间 | `histogram_quantile(0.99, sum(rate(nginx_http_request_api_duration_seconds_bucket{api=~"..."}[5m])) by(le,api)) * 1000` |
| 各接口 P9999 响应时间 | `histogram_quantile(0.9999, sum(rate(nginx_http_request_api_duration_seconds_bucket{api=~"..."}[5m])) by(le,api)) * 1000` |

## 实例维度

| 面板/用途 | 指标与用法 |
|---|---|
| 实例 QPS | `nginx_http_requests_api_total`，`sum(irate(...[5m])) by(instance)` |
| 实例平均响应时间 | `nginx_http_request_api_duration_seconds_sum/count`，按 `instance` 计算平均耗时毫秒 |
| 实例 P99 响应时间 | `histogram_quantile(0.99, sum(rate(nginx_http_request_api_duration_seconds_bucket[5m])) by(le,instance)) * 1000` |
| 实例业务 code 错误率 | `nginx_http_requests_api_code_total{api_code!=""}`，按 `api_code` / 全量，常按 `api_code` 展示 |
| 指定业务 code 实例错误率 | `nginx_http_requests_api_code_total{api_code=~"$api_code"}`，按 `instance` / 全量，定位异常实例 |
| 本地缓存命中率 | `nginx_http_cache_counter{cache_label="LC_HIT"}` / `nginx_http_cache_counter{cache_label="VISIT_TOTAL"}` |
| cb 缓存命中率 | `nginx_http_cache_counter{cache_label="CB_HIT"}` / `nginx_http_cache_counter{cache_label="CB_TOTAL"}` |
| 后台穿透率 | `nginx_http_cache_counter{cache_label="BACKEND_TOTAL"}` / `nginx_http_cache_counter{cache_label="VISIT_TOTAL"}` |

## 熔断

| 面板/用途 | 指标与用法 |
|---|---|
| 运行态 failover 监控 | `nginx_http_failover_counter`，`sum(increase(...[2m])) by(failover_label)`，支持按 `dc`、`group`、`instance` 过滤 |

# 直播调用第三方 Grafana 指标速查

Grafana 看板参考：`直播第三方`。本节记录直播服务调用第三方服务的 Prometheus 指标，核心指标前缀为 `http_outer_request_label_*`，并统一带 `project="VideoPlay-live-nginx1"`。

通用变量：

| 变量 | 含义 |
|---|---|
| `$src` | 流量来源：`qiyi`、`qiyi_qpaas`、`qiyi_qsm`；`All`=`.*` |
| `$dc` | 机房 |
| `$label` | 第三方服务 label |

## 直播第三方服务 label 列表

可用 `sum by(label)(irate(http_outer_request_label_status_total{project="VideoPlay-live-nginx1"}[5m]))` 查看当前有指标返回的服务 label。

| 服务 label | 描述 |
|---|---|
| `boss_service` | 请求会员鉴权 |
| `cdn_dispatch` | 请求cdn调度（开播加速使用） |
| `drm_service` | 请求drm |
| `real_live_lc` | 请求直播后台lc |
| `real_live_lp` | 请求直播后台lp |
| `sports_auth_check` | 请求体育接口对体育赛事包场景的鉴权 |
| `sports_check_right` | 请求体育对体育内容进行鉴权 |
| `user_check_119` | 请求会员判断用户是否新老会员 |

## 直播第三方 QPS 与错误率

| 面板/用途 | 指标与用法 |
|---|---|
| HTTP 状态码 QPS | `http_outer_request_label_status_total{project="VideoPlay-live-nginx1",dc=~"$dc",label=~"$label",src=~"$src"}`，整体 `sum(irate(...[5m]))`，按状态码 `by(status)` |
| HTTP 非 200 错误率 | `http_outer_request_label_status_total{status!~"200"}` / `http_outer_request_label_status_total`，按 `status` 展示 |
| 平均耗时 | `sum(increase(http_outer_request_label_duration_seconds_sum[5m])) * 1000 / sum(increase(http_outer_request_label_duration_seconds_count[5m]))` |
| 业务 code QPS | `http_outer_request_label_code_total{project="VideoPlay-live-nginx1",dc=~"$dc",label=~"$label",src=~"$src"}`，`sum(increase(...[5m])) by(code)` |
