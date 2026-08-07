# Dash 主站/国际站 Grafana 指标速查

Grafana 看板参考：`A-DASH-大陆` / `1 前端服务-主站`。本文件只记录可通过 Prometheus 直接查询的面板指标。

dash 数据源同时包含主站和国际站指标，通过 `dc` 过滤区分：

| 范围 | dc 过滤 |
|---|---|
| 主站/大陆 | `dc!~"singapore.*|xjp|sgp-.*|iqiyi-use.*"` |
| 国际站 | `dc=~"singapore.*|xjp|sgp-.*|iqiyi-use.*"` |

下面的面板表达式多数来自大陆看板，默认使用主站/大陆过滤。查国际站时，把相关 PromQL 中的大陆排除条件替换为国际站匹配条件。

通用变量：

| 变量 | 含义 |
|---|---|
| `$src` | 流量来源，如主站、OTT 等 |
| `$unit` | 单元 |
| `$dc` | 机房 |
| `$group` | 小站/分组 |
| `$instance` | 实例 |
| `$code` | 第一层业务 code，如 `A00000` |
| `$st` | 第二层业务 st，如 `101`、`312`、`800` |
| `$mode` | 流量类型：`0`=正常流量，`1`=压测流量，`All`=`.*` |
| `$duration` | 延时桶阈值，如 `00.100` |

大陆 dash 面板常排除海外机房：`dc!~"singapore.*|xjp|sgp-.*|iqiyi-use.*"`；国际站查询使用：`dc=~"singapore.*|xjp|sgp-.*|iqiyi-use.*"`。

## QPS 与错误率

| 面板/用途 | 指标与用法 |
|---|---|
| 总体 QPS、分机房 QPS | `http_request_duration_seconds_count`，`sum(irate(...{api="dash"}[3m]))`；分机房 `by(dc)`，整体不分组 |
| 小站 QPS | 同上，加 `dc=~"$dc"`，按 `by(group)` 分组 |
| 机器平均 QPS | `http_request_duration_seconds_count`，`avg(irate(...[5m]))`；分机房 `by(dc)` |
| 小站平均 QPS | 同机器平均 QPS，加 `dc=~"$dc"`，按 `by(group)` |
| 机房/小站 QPS 占比 | `http_request_duration_seconds_count` 的 `sum(irate(...[5m]))`，Grafana 饼图按 `dc` 或 `group` 展示占比 |
| 第一层 CODE QPS | `http_requests_code_st_total{code!="A00000"}`，`sum(irate(...[5m])) by(code)`；整体量用 `http_requests_code_st_total / 100` 作对照 |
| 第一层 code 错误率 | 分子 `http_requests_code_st_total{code!="A00000"}`，分母 `http_request_duration_seconds_count`，按 `code`、`dc` 或 `group` 聚合；部分 TOP 面板会乘 `1000` 表示千分比 |
| 指定第一层 code 分布 | 加 `code=~"$code"`，按 `dc` 或 `group` 展示错误率分布 |
| 第二层 CODE QPS | `http_requests_code_st_total{st!="101"}`，`sum(irate(...[5m])) by(st)`；分母或整体量常用 `http_request_duration_seconds_count / 100` |
| 第二层重点 CODE 错误率 | `http_requests_code_st_total{st=~"800|801|802|803|806|807|512|1500|2502|313|501|502"}` / `http_request_duration_seconds_count`，按 `st` |
| 第二层非重点 CODE 错误率 | `http_requests_code_st_total{st!~"101|800|801|802|803|806|512|1500|2502|313|501|502"}` / `http_request_duration_seconds_count`，按 `st` |
| 指定第二层 st 分布 | 加 `st=~"$st"` 且 `st!="101"`，按 `dc` 或 `group` 展示错误率 |
| HTTP code QPS | `http_requests_status_total{status!="200"}`，`sum(irate(...[5m])) by(status)` |
| HTTP code 错误率 | `http_requests_status_total{status!="200"}` / `http_requests_status_total`，按 `dc` 或整体 |
| 宕机机器列表 | `up{src=~"$src"} == 0`，按 `instance` / `job` 展示 |

## 耗时

| 面板/用途 | 指标与用法 |
|---|---|
| 平均响应时间 | `sum(rate(http_request_duration_seconds_sum[5m]) * 1000) / sum(rate(http_request_duration_seconds_count[5m]))`；按 `dc`、`group` 或 `instance` 聚合 |
| 响应时间分位数 | `histogram_quantile(0.5/0.99/0.999, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) * 1000` |
| 请求延时超时率 | `(1 - sum(increase(http_request_duration_seconds_bucket{le=~"$duration"}[5m])) / sum(increase(http_request_duration_seconds_count[5m]))) * 10000`；按 `dc` 或 `group`，单位是万分比 |

## TOP 数据

| 面板/用途 | 指标与用法 |
|---|---|
| 依赖 upstream 错误 top10 | `topk(10, increase(dashUpstreamErrorCounter{service=~"$st"}[3m]))`，按 `upstream` |
| 单台 QPS top10 | `topk(10, avg(irate(http_request_duration_seconds_count{api="dash"}[5m])) by(instance))` |
| 单台接口延时 top10 | `topk(10, sum(irate(http_request_duration_seconds_sum[5m]) * 1000) by(instance) / sum(irate(http_request_duration_seconds_count[5m])) by(instance))` |
| 单台一层错误率 top10 | `topk(10, sum(irate(http_requests_code_st_total{code!="A00000",code=~"$code"}[5m])) by(instance) * 1000 / sum(irate(http_request_duration_seconds_count[5m])) by(instance))` |
| 单台二层错误率 top10 | `topk(10, sum(irate(http_requests_code_st_total{st!="101",st=~"$st"}[5m])) by(instance) * 1000 / sum(irate(http_request_duration_seconds_count[5m])) by(instance))` |

## ptid 维度数据

| 面板/用途 | 指标与用法 |
|---|---|
| 平台请求占比 | Prometheus 指标 `http_dash_pf_code_st_total`，`sum(increase(...[15m])) by(pf)` |
| 平台请求 QPS | Prometheus 指标 `http_dash_pf_code_st_total`，`sum(irate(...[5m])) by(pf)` |

## 实例级别数据

| 面板/用途 | 指标与用法 |
|---|---|
| 单台 QPS | `avg(irate(http_request_duration_seconds_count{instance=~"$instance"}[5m])) by(instance)` |
| 单台平均响应时间 | `rate(http_request_duration_seconds_sum{instance=~"$instance"}[5m]) * 1000 / rate(http_request_duration_seconds_count{instance=~"$instance"}[5m])` |
| 单台第一层 code 错误率 | `irate(http_requests_code_st_total{code!="A00000",instance=~"$instance"}[5m]) * 1000 / scalar(irate(http_request_duration_seconds_count{instance=~"$instance"}[5m]))` |
| 单台第二层重点 CODE 错误率 | `http_requests_code_st_total{st=~"800|801|802|803|304|110|512|501|502"}` / `http_request_duration_seconds_count`，按 `st`，乘 `1000` |
| 单台第二层非重点 CODE 错误率 | `http_requests_code_st_total{st!~"101|800|801|802|803|304|110|512|501|502"}` / `http_request_duration_seconds_count`，按 `st`，乘 `1000` |
| 指定 dc/st 的实例错误率 | `http_requests_code_st_total{st=~"$st",dc=~"$dc"}` / `http_request_duration_seconds_count{dc=~"$dc"}`，按 `instance` |

## 运行状态监控

| 面板/用途 | 指标与用法 |
|---|---|
| 运行时错误 QPS | `http_dash_other_error`，`sum(irate(...[5m])) by(label)` |
| 码流选择结果 QPS | `http_dash_selected_rate_counter`，`sum(irate(...[5m])) by(code)` |
| 码流选择结果百分比 | `sum(irate(http_dash_selected_rate_counter[5m])) by(code) * 100 / scalar(sum(irate(http_dash_selected_rate_counter[5m])))` |
| 码流选择结果 24h 比例 | `sum(increase(http_dash_selected_rate_counter[24h])) by(code)` |
| 码流选择 ff QPS/比例 | `http_dash_selected_rate_counter`，按 `ff`，QPS 用 `irate[5m]`，比例用 `increase[24h]` |
| 各流程 QPS | `match_process_counter`，`sum(irate(...[5m])) by(label)` |
| 流程 24h 占比 | `match_process_counter`，`sum(increase(...[24h])) by(label)` |

## 播放流程

| 面板/用途 | 指标与用法 |
|---|---|
| 新引擎流程 QPS（分机房） | `match_process_counter`，`sum by(label)(irate(...{dc=~"$dc"}[5m]))` |
| 新引擎流程 QPS（分小站） | `match_process_counter`，`sum by(label)(irate(...{group=~"$group"}[5m]))` |

# Dash 请求第三方服务 Grafana 指标速查

Grafana 看板参考：`A-DASH-第三方-大陆`。本节记录 dash 请求第三方服务的 Prometheus 指标，核心指标前缀为 `http_outer_request_label_*`。

通用变量：

| 变量 | 含义 |
|---|---|
| `$src` | 流量来源：`qiyi`、`qiyi_qpaas`、`ott` |
| `$unit` | 单元 |
| `$label` | 第三方服务名/依赖服务标识，例如看板默认值 `mus` |
| `$dc` | 机房 |
| `$group` | 小站/分组 |
| `$bg` | 背景/分组标记：`g1`、`g2`、`default` |
| `$instance` | 实例 |

大陆看板常用过滤：`dc!~"singapore_.*|.*_dog|hongkong_megaplus"`。查国际站时按 dash 数据源规则改为匹配海外机房，例如 `dc=~"singapore.*|xjp|sgp-.*|iqiyi-use.*"`，并结合实际第三方看板变量过滤。

## 第三方服务 label 列表

可用 `sum by(label)(irate(http_outer_request_label_status_total[5m]))` 查看当前有指标返回的服务 label。

| 服务 label | 描述 |
|---|---|
| `boss_ckts` | 请求会员鉴权 |
| `cdn_dispatch` | 请求cdn调度（开播加速使用） |
| `dashstable` | 请求dashstable |
| `door_open` | 请求后门（跳过播控） |
| `drm` | 请求drm |
| `fshark_vp` | 请求飞鲨vp |
| `get_vipTypes` | 请求会员获取用户身份类型 |
| `honey_pot_uid_token` | 请求蜜罐接口 |
| `interaction` | 请求互动接口 |
| `mus` | 请求mus |
| `passport` | 请求passport |
| `sports_auth_check` | 请求体育接口对体育赛事包场景的鉴权 |
| `sports_auth_check2` | 请求体育对体育内容进行鉴权 |
| `user_check_119` | 请求会员判断用户是否新老会员 |

## 第三方服务 QPS 与错误率

| 面板/用途 | 指标与用法 |
|---|---|
| 总体 QPS、分机房 QPS | `http_outer_request_label_status_total`，`sum(irate(...{src=~"$src",unit=~"$unit",label=~"$label"}[5m]))`；分机房 `by(dc)` |
| 总体 QPS、分小站 QPS | `http_outer_request_label_status_total`，加大陆机房过滤和 `bg=~"$bg"`，整体不分组，小站 `by(group)` |
| 分机房 QPS 占比 | `http_outer_request_label_status_total`，`sum(irate(...[5m])) by(dc)` |
| 指定机房下小站 QPS 占比 | `http_outer_request_label_status_total{dc=~"$dc"}`，`sum(irate(...[5m])) by(group)` |
| 业务 CODE QPS | `http_outer_request_label_code_total{code!~"A00000|101"}`，`sum(irate(...[5m])) by(code)` |
| 业务 code 分机房错误率 | `http_outer_request_label_code_total{code!~"A00000|101"}` / `http_outer_request_label_code_total`，按 `dc`，乘 `1000` 表示千分比 |
| 业务 code 分小站错误率 | 同业务 code 错误率，加 `dc=~"$dc"` 后按 `group`，乘 `1000` |
| HTTP code QPS | `http_outer_request_label_status_total{status!="200"}`，按 `status` |
| HTTP code 分机房错误率 | `http_outer_request_label_status_total{status!="200"}` / `http_outer_request_label_status_total`，按 `dc`，乘 `10000` 表示万分比 |
| HTTP code 分小站错误率 | 同 HTTP code 错误率，加 `dc=~"$dc"`、`group=~"$group"` 后按 `group`，乘 `10000` |

## 第三方服务耗时

| 面板/用途 | 指标与用法 |
|---|---|
| 分机房平均响应时间 | `sum(rate(http_outer_request_label_duration_seconds_sum[5m]) * 1000) by(dc) / sum(rate(http_outer_request_label_duration_seconds_count[5m])) by(dc)` |
| 整体平均响应时间 | `sum(rate(http_outer_request_label_duration_seconds_sum[5m]) * 1000) / sum(rate(http_outer_request_label_duration_seconds_count[5m]))` |
| 分小站平均响应时间 | 加 `dc=~"$dc"`、`label=~"$label"` 后，按 `group` 聚合 `duration_seconds_sum/count` |
| 小站中实例平均响应时间 | 加 `group=~"$group"`、`instance=~"$instance"` 后，按 `instance` 聚合 `duration_seconds_sum/count` |

## 第三方服务单机监控

| 面板/用途 | 指标与用法 |
|---|---|
| 单机 QPS | `http_outer_request_label_status_total{instance=~"$instance",label=~"$label"}`，`sum(irate(...[5m]))`，按 `instance` 展示 |
| 单机响应时间 | `http_outer_request_label_duration_seconds_sum/count{instance=~"$instance"}`，按 `label` 计算平均耗时毫秒 |
| 单机 HTTP code QPS | `http_outer_request_label_status_total{instance=~"$instance",label=~"$label",status!="200"}`，按 `status` |
| 单机业务码 QPS | `http_outer_request_label_code_total{label="$label",code!~"A00000|101",instance=~"$instance"}`，按 `code` |
