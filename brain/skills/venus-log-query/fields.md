# log_nginx_cache_access 表字段说明

dash 点播访问日志（access 表）主要字段。live 表 `log_nginx_livenewone_access` 字段结构类似。

## 请求与用户

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `tvid` | string | 视频 ID | `6150706909133800` |
| `http_request` | string | 请求 path | `/dash` |
| `host_domain` | string | 请求域名 | `cache.video.iqiyi.com` |
| `http_user_agent` | string | HTTP Header UA | `QYPlayer/Android/5.3.0405;BT/mcto;...` |
| `uid` | string | 用户 ID，空表示未登录 | `123` 或空 |
| `k_uid` | string | 用户设备 ID | `ab9b4b5337217164af9782dcbe71de3a1109` |
| `deviceid` | string | 用户设备 ID（同 k_uid 体系） | `ab9b4b5337217164af9782dcbe71de3a1109` |
| `src` | string | 请求端标识（ptid） | `02022001010000000000` |
| `xforward` | string | 用户真实 IP | `42.48.221.225` |

## 错误码

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `code` | string | 一层错误码 | `A00000` |
| `st` | string | 二层 st 错误码 | `101` |
| `status` | int | HTTP 状态码 | `200` |

### code vs st

- `code`：一层业务返回码
- `st`：二层细分状态码（如 101 正常、312 异常）
- `status`：HTTP 层状态码，与 st 独立，常见 `status=200, st=312`

## 性能与视频

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `request_time` | float | 请求耗时（秒） | `0.032` |
| `rate_duration` | int | 请求视频时长（秒） | `63` |

## 服务端 / 部署环境

| 字段 | 类型 | 说明 | 示例 | 备注 |
|------|------|------|------|------|
| `host` | string | 处理请求的虚机 IP | `10.71.102.96` | **仅虚机**部署时有值 |
| `v_k8s_podip` | string | qpaas/k8s Pod IP | `10.192.103.64` | **仅 qpaas/k8s** 时有值 |
| `v_k8s_cluster` | string | k8s 集群名 | `cnhz1-public-prod03` | qpaas/k8s 环境 |
| `dc` | string | 服务端机器所在机房 | `bdxs` | **仅虚机**有值；qpaas 请求为 NULL |
| `logtype` | string | 日志来源标识 | `dash-k8s` | `dash-k8s` 表示来自 qpaas/k8s |
| `v_k8s_podname` | string | pod 的名称 | `dash-u2-az-6dbc548965-ccs7m` | 前缀dash-u2可以用于区分是哪个环境/单元 |

### 虚机 vs qpaas/k8s 判断

| 部署方式 | 有值字段 | 空/NULL 字段 |
|----------|----------|--------------|
| 虚机 | `host`, `dc` | `v_k8s_podip` |
| qpaas/k8s | `v_k8s_podip`, `v_k8s_cluster`, `logtype=dash-k8s` | `dc` 为 NULL |


## 原始日志

| 字段 | 类型 | 说明 |
|------|------|------|
| `rawmessage` | string | nginx 完整原始日志行，含请求参数和 porsche_detail |

示例（截断）：

```
10.198.9.91 - - [08/Jul/2026:11:04:55 +0800] "GET /dash?tvid=6150706909133800&... HTTP/1.0" 200 4631 4795 3.34 "-" "cache.video.iqiyi.com" "QYPlayer/Android/..." "2408:8435:..." "-" "-" rspt:- rqtt:0.032 ... porsche_detail:code-A00000 st-101 rate_code-1 ...
```

prio:- quantum:v-4,boss_ts-10  表示的是当前请求调用了哪些第三方接口以及耗时信息，boss_ts 表示当前视频是付费视频，并请求了会员接口进行鉴权

## 常用查询字段组合

| 排查场景 | 推荐字段 |
|----------|----------|
| 错误聚集 | `st`, `tvid`, `code` |
| 用户影响面 | `k_uid`, `deviceid`, `uid`, `xforward` |
| 终端分布 | `src`, `http_user_agent` |
| 域名/CDN | `host_domain` |
| 服务端定位 | `v_k8s_podip`, `v_k8s_cluster`, `host`, `dc` |
| 性能 | `request_time`, `rate_duration` |
| 慢请求 | `where request_time > 1` |

## 查询示例

```sql
-- 按 st 分布
select st, count(*) as cnt from log_nginx_cache_access group by st order by cnt desc limit 20

-- 按终端 src 分布
select src, count(*) as cnt from log_nginx_cache_access where st='312' group by src order by cnt desc limit 10

-- 按 k8s 集群
select v_k8s_cluster, count(*) as cnt from log_nginx_cache_access where st='312' group by v_k8s_cluster order by cnt desc

-- 慢请求
select tvid, request_time, host_domain, rawmessage from log_nginx_cache_access where request_time > 2 limit 10

-- 虚机 vs k8s 占比
select case when dc is not null then 'vm' else 'k8s' end as deploy, count(*) as cnt
from log_nginx_cache_access group by 1
```


# log_nginx_livenewone_access 表字段说明

字段大致和dash的access一样，只是用的lp字段表示的是哪个直播节目
