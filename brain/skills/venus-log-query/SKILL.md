---
name: venus-log-query
description: 查询爱奇艺 Venus 日志平台（Iceberg + Trino SQL）。用于查 nginx 访问/错误日志、聚合 Top N、错误聚集分析、按 tvid/st/时间维度统计。触发场景：Venus 日志、venus 查询、dash/live 日志排查。
---

# Venus 日志查询

查询爱奇艺内部 Venus 日志平台，底层为 **Iceberg + Trino**（非 ES DSL）。`queryString` 使用标准 SQL。

## 认证与接口

### 主站

| 项 | 值 |
|---|---|
| API | `POST http://venus.cloud.qiyi.domain/log/api/v1/search/project/305/query` |
| Project ID | `305` |
| Token | `b64d1fc4dc4a4fc2842d4c8c9038630c` |
| 日志表 | 见下方「日志表」章节 |

### 国际站

| 项 | 值 |
|---|---|
| API | `POST http://venus-intl.cloud.qiyi.domain/log/api/v1/search/project/2586/query` |
| Project ID | `2586` |
| Token | `d475109b22ee43c99a15adf915d895c7` |
| 日志表 | 见下方「日志表」章节（无 `log_nginx_livenewone_error`） |

主站与国际站 **Token 不通用**，需按站点分别配置。

### 公共 Header

| Header | 值 |
|---|---|
| `Content-Type` | `application/json` |
| `Authorization` | `Token <token>` |


## 请求体

```json
{
  "tableName": "log_nginx_cache_access",
  "queryString": "select ... from log_nginx_cache_access where ...",
  "startTime": 1783452900000,
  "endTime": 1783453200000,
  "size": 100
}
```

| 字段 | 说明 |
|---|---|
| `tableName` | 日志表名，与 `queryString` 中 `from` 一致 |
| `queryString` | Trino SQL（原始日志或聚合） |
| `startTime` / `endTime` | 毫秒时间戳 |
| `size` | 返回行数上限，原始日志最大 5000 |

时间转换：

```bash
date -d '2026-07-08 03:35:00' +%s%3N   # startTime
date -d '2026-07-08 03:40:00' +%s%3N   # endTime
```

## 日志表

### 主站（4 张表）

| 表名 | 类型 | 说明 |
|------|------|------|
| `log_nginx_cache_access` | dash access | 点播访问日志，含 st/code 等业务状态 |
| `log_nginx_cache_error` | dash error | 点播错误日志，记录请求错误原因（如 st=800、网络超时） |
| `log_nginx_livenewone_access` | live access | 直播访问日志 |
| `log_nginx_livenewone_error` | live error | 直播错误日志，记录请求错误原因 |

### 国际站（3 张表）

| 表名 | 类型 | 说明 |
|------|------|------|
| `log_nginx_cache_access` | dash access | 点播访问日志 |
| `log_nginx_cache_error` | dash error | 点播错误日志 |
| `log_nginx_livenewone_access` | live access | 直播访问日志 |

国际站**没有** `log_nginx_livenewone_error`。

### access vs error 选型

| 排查目标 | 用哪张表 |
|----------|----------|
| 看请求量、st 分布、tvid 聚集 | `*_access` |
| 查错误根因（超时、WAF 拦截等） | `*_error` |
| st=312 等业务码统计 | `*_access`（st 在 access 日志的 porsche_detail 中） |
| st=800 等原因分析 | `*_error`（记录详细错误信息） |


## 两种查询模式

### 1. 原始日志（看详情）

```sql
select * from log_nginx_cache_access where st='312'
```

- 解析路径：`data.hits.hits[]._source.rawmessage`
- 受 `size` 上限（5000）限制，大数据量会截断
- 适用：看单条请求参数、抽样排查

### 2. 聚合查询（看 Top / 分布）— 优先使用

```sql
select tvid, count(*) as cnt
from log_nginx_cache_access
where st='312'
group by tvid
order by cnt desc
limit 10
```

- 解析路径：`data.hits.hits[]._source`（含 `tvid`、`cnt` 等聚合字段）
- 不受原始日志 5000 条截断影响，服务端直接统计
- 适用：Top N、总量、趋势、多维度分布

**注意**：`select top 10 ... group by tvid` 不会按 count 排序；必须用 `order by cnt desc limit 10`。

## 常用字段（log_nginx_cache_access）

完整字段说明见 [fields.md](fields.md)。

| 字段 | 含义 |
|------|------|
| `tvid` | 视频 ID |
| `code` | 一层错误码（如 A00000） |
| `st` | 二层 st 错误码（如 101、312） |
| `status` | HTTP 状态码（通常 200） |
| `src` | 请求端标识 ptid |
| `uid` | 用户 ID，空=未登录 |
| `k_uid` / `deviceid` | 用户设备 ID |
| `xforward` | 用户真实 IP |
| `host_domain` | 请求域名 |
| `http_request` | 请求 path（/dash） |
| `http_user_agent` | UA |
| `request_time` | 请求耗时（秒） |
| `rate_duration` | 视频时长（秒） |
| `host` | 虚机 IP（仅虚机部署） |
| `v_k8s_podip` | k8s Pod IP（仅 qpaas/k8s） |
| `v_k8s_cluster` | k8s 集群名 |
| `dc` | 虚机机房（qpaas 为 NULL） |
| `logtype` | 日志来源（dash-k8s = qpaas） |
| `rawmessage` | nginx 原始日志行 |

## 响应结构

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "hits": { "hits": [ { "_source": { ... } } ] },
    "sql": "实际执行的 SQL",
    "exectime": 0.912
  }
}
```

常见错误码：

| code | 含义 |
|---|---|
| `0` | 成功 |
| `100007` | Token 认证失败 |
| `100000` | 请求格式错误 |
| `100012` | 表不存在（如国际站查 `log_nginx_livenewone_error`） |

## 分析工作流

聚集/异常排查推荐顺序：

1. **聚合看总量**：`select count(*) from ... where ...`
2. **聚合看 Top**：`group by tvid order by cnt desc limit N`
3. **下钻主对象**：对 Top1 加条件，按 `host_domain`、分钟、`src` 再 group by
4. **原始日志抽样**：仅对关键 tvid 拉少量 `select *` 看 `rawmessage`

不要先拉 5000 条原始日志再本地统计。

## 浏览器 URL（可视化查询）

将 SQL 转为 Venus 控制台可直接打开的链接，便于分享和人工排查。

### URL 格式

```
https://{domain}/#/projects/{projectId}/new-search/{tableName}/{urlencode(sql)}&startTs={startMs}&endTs={endMs}&intervalSearch={interval}
```

| 站点 | domain | projectId |
|------|--------|-----------|
| 主站 | `venus.cloud.qiyi.domain` | `305` |
| 国际站 | `venus-intl.cloud.qiyi.domain` | `2586` |

- SQL 做 URL 编码（`*` 不编码）
- `startTs` / `endTs`：毫秒时间戳
- `intervalSearch`：时间粒度，常用 `1m`、`5m`、`15m`

### 示例

```
https://venus.cloud.qiyi.domain/#/projects/305/new-search/log_nginx_cache_access/select%20*%20from%20log_nginx_cache_access%20where%20dc%20is%20NULL&startTs=1783480453000&endTs=1783481353000&intervalSearch=1m
```

对应 SQL：

```sql
select * from log_nginx_cache_access where dc is NULL
```

### 生成脚本

```bash
# 主站，指定时间戳
python3 scripts/to-venus-url.py \
  --sql "select * from log_nginx_cache_access where dc is NULL" \
  --start-ts 1783480453000 --end-ts 1783481353000

# 主站，指定时间字符串
python3 scripts/to-venus-url.py \
  --sql "select tvid, count(*) as cnt from log_nginx_cache_access where st='312' group by tvid order by cnt desc limit 10" \
  --start "2026-07-08 03:35:00" --end "2026-07-08 03:40:00"

# 国际站，最近 30 分钟
python3 scripts/to-venus-url.py --site intl \
  --sql "select count(*) from log_nginx_cache_access" \
  --minutes 30
```

回复用户时，给出可点击的完整 URL，方便直接在浏览器打开 Venus 控制台。

## 快速 curl 模板

### 主站

```bash
TOKEN="b64d1fc4dc4a4fc2842d4c8c9038630c"
URL="http://venus.cloud.qiyi.domain/log/api/v1/search/project/305/query"
```

### 国际站

```bash
TOKEN="d475109b22ee43c99a15adf915d895c7"
URL="http://venus-intl.cloud.qiyi.domain/log/api/v1/search/project/2586/query"
```

### 查询示例

```bash
START_MS=$(date -d '2026-07-08 03:35:00' +%s%3N)
END_MS=$(date -d '2026-07-08 03:40:00' +%s%3N)

curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_access\",
    \"queryString\": \"select tvid, count(*) as cnt from log_nginx_cache_access where st='312' group by tvid order by cnt desc limit 10\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 10
  }"
```


## 更多资料

- 完整 SQL 示例：[examples.md](examples.md)
- API 与字段参考：[reference.md](reference.md)
- access 表字段详解：[fields.md](fields.md)
