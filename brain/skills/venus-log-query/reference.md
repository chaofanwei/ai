# Venus 日志查询参考

## 平台架构

Venus 日志平台底层为 **Iceberg 数据湖 + Trino 查询引擎**（已从 ElasticSearch 演进）。用户提交的 `queryString` 会被翻译为 Trino SQL 执行。

- 原始日志查询：约 5 秒（亿级）
- 聚合查询：约 30 秒内

## API 详情

### Endpoint

```
POST http://venus.cloud.qiyi.domain/log/api/v1/search/project/305/query
```

`305` 为项目 ID（Tiros 项目使用此 ID）。

### 认证

```
Authorization: Token b64d1fc4dc4a4fc2842d4c8c9038630c
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `tableName` | string | 是 | 日志表名 |
| `queryString` | string | 是 | Trino SQL |
| `startTime` | long | 是 | 开始时间（毫秒） |
| `endTime` | long | 是 | 结束时间（毫秒） |
| `size` | int | 是 | 返回行数，原始日志最大 5000 |

Venus 会自动追加分区条件：

```sql
WHERE dt >= '2026-07-08' AND dt <= '2026-07-08'
  AND timestamp >= <startTime> AND timestamp <= <endTime>
  AND (<用户 where 条件>)
```

### 响应字段

| 路径 | 说明 |
|------|------|
| `code` | 0=成功 |
| `message` | 状态描述 |
| `data.hits.hits` | 结果数组 |
| `data.hits.hits[]._source` | 单条结果 |
| `data.hits.hits[]._source.rawmessage` | 原始日志（仅 select * 时有） |
| `data.sql` | 实际执行的 SQL |
| `data.exectime` | 执行耗时（秒） |
| `data.noData` | `"true"` 表示无数据 |

## 日志表

| 表名 | 类型 | Tiros 常量 |
|------|------|-----------|
| `log_nginx_cache_access` | dash 点播 nginx 访问日志 | `LOG_FROM_DASH` |
| `log_nginx_livenewone_access` | live 直播 nginx 访问日志 | `LOG_FROM_LIVE` |


## SQL 语法

遵循 **Trino SQL**，支持：

| 能力 | 示例 |
|------|------|
| 条件过滤 | `where st='312' and tvid='90000100'` |
| 聚合 | `count(*)`, `count(distinct k_uid)`, `sum()`, `avg()` |
| 分组 | `group by tvid` |
| 排序 | `order by cnt desc` |
| 限制 | `limit 10` |
| 时间分桶 | `date_trunc('minute', from_unixtime(timestamp/1000))` |
| 条件聚合 | `count(*) filter (where ...)` |
| 别名 | `count(*) as cnt` |

不支持 ES DSL（`aggs`、`terms` 等）。

### queryString 写法对照

| 场景 | queryString |
|------|-------------|
| 原始日志 | `select * from log_nginx_cache_access where st='312'` |
| 计数 | `select count(*) from log_nginx_cache_access where st='312'` |
| Top N | `select tvid, count(*) as cnt from ... group by tvid order by cnt desc limit 10` |
| 去重用户 | `select tvid, count(distinct k_uid) uv from ... group by tvid` |
| 分钟趋势 | `select date_trunc('minute', from_unixtime(timestamp/1000)) as minute, count(*) cnt from ... group by 1 order by 1` |


## 常用日志字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `rawmessage` | string | nginx 完整日志行 |
| `tvid` | string | 视频 ID |
| `vid` | string | 视频 vid |
| `st` | string | 业务状态码（porsche_detail 中 st-xxx） |
| `status` | int | HTTP 状态码 |
| `code` | string | 业务返回码（如 A00000） |
| `host_domain` | string | 请求域名 |
| `http_request` | string | 请求路径（/dash 等） |
| `http_method` | string | GET/POST |
| `src` | string | 终端 src 标识 |
| `ori` | string | 来源（pcw 等） |
| `uid` | string | 用户 ID |
| `k_uid` | string | 设备用户 ID |
| `bid` | int | 码流 |
| `timestamp` | long | 日志时间（毫秒） |
| `dt` | string | 日期分区（yyyy-MM-dd） |
| `remote_addr` | string | 客户端 IP |
| `request_time` | float | 请求耗时 |

### st vs status

- `status`：HTTP 层，通常 200
- `st`：业务层错误码，如 `st=312` 表示特定业务异常
- 两者独立：可能出现 `status=200, st=312`

## 错误码

| code | message | 处理 |
|------|---------|------|
| 0 | success | 正常 |
| 100007 | Token 认证失败 | 检查 token |
| 100000 | JSON/请求格式错误 | 检查请求体 |


## 性能建议

1. **聚集分析优先用 `group by`**，避免拉原始日志
2. 缩小时间范围（5~30 分钟粒度）
3. 下钻时逐步加 where 条件（先 tvid，再 host_domain）
4. `size` 按实际需要设置，聚合 Top 10 设 10 即可
5. 原始日志抽样用 `size=10~50`，不必拉满 5000
