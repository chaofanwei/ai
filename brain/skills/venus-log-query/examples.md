# Venus 日志查询示例

## 基础 curl 模板

```bash
# 主站
TOKEN="b64d1fc4dc4a4fc2842d4c8c9038630c"
URL="http://venus.cloud.qiyi.domain/log/api/v1/search/project/305/query"

# 国际站
# TOKEN="d475109b22ee43c99a15adf915d895c7"
# URL="http://venus-intl.cloud.qiyi.domain/log/api/v1/search/project/2586/query"

# 时间范围（毫秒）
START_MS=$(date -d '2026-07-08 03:35:00' +%s%3N)
END_MS=$(date -d '2026-07-08 03:40:00' +%s%3N)

# 最近 30 分钟
END_MS=$(date +%s%3N)
START_MS=$((END_MS - 30*60*1000))
```

---

## 浏览器 URL 生成

将 SQL 转为 Venus 控制台链接，浏览器登录后直接打开。

### URL 模板

```
https://{domain}/#/projects/{projectId}/new-search/{table}/{urlencode(sql)}&startTs={startMs}&endTs={endMs}&intervalSearch=1m
```

| 站点 | domain | projectId |
|------|--------|-----------|
| 主站 | `venus.cloud.qiyi.domain` | `305` |
| 国际站 | `venus-intl.cloud.qiyi.domain` | `2586` |

### 手工拼接（Python 一行）

```python
from urllib.parse import quote
domain, pid, table = "venus.cloud.qiyi.domain", 305, "log_nginx_cache_access"
sql = "select * from log_nginx_cache_access where dc is NULL"
start_ts, end_ts = 1783480453000, 1783481353000
url = f"https://{domain}/#/projects/{pid}/new-search/{table}/{quote(sql, safe='*')}&startTs={start_ts}&endTs={end_ts}&intervalSearch=1m"
print(url)
```

### 脚本生成

```bash
python3 scripts/to-venus-url.py \
  --sql "select * from log_nginx_cache_access where dc is NULL" \
  --start-ts 1783480453000 --end-ts 1783481353000
```

输出：

```
https://venus.cloud.qiyi.domain/#/projects/305/new-search/log_nginx_cache_access/select%20*%20from%20log_nginx_cache_access%20where%20dc%20is%20NULL&startTs=1783480453000&endTs=1783481353000&intervalSearch=1m
```

### 常用 URL 示例

**qpaas 请求（dc is NULL）**

```
https://venus.cloud.qiyi.domain/#/projects/305/new-search/log_nginx_cache_access/select%20*%20from%20log_nginx_cache_access%20where%20dc%20is%20NULL&startTs=1783480453000&endTs=1783481353000&intervalSearch=1m
```

**st=312 tvid Top 10 聚合**

```bash
python3 scripts/to-venus-url.py \
  --sql "select tvid, count(*) as cnt from log_nginx_cache_access where st='312' group by tvid order by cnt desc limit 10" \
  --start "2026-07-08 03:35:00" --end "2026-07-08 03:40:00"
```

**国际站最近 30 分钟总量**

```bash
python3 scripts/to-venus-url.py --site intl \
  --sql "select count(*) from log_nginx_cache_access" \
  --minutes 30 --interval 5m
```

**dash 错误日志**

```bash
python3 scripts/to-venus-url.py \
  --table log_nginx_cache_error \
  --sql "select * from log_nginx_cache_error where tvid='2163942648018300'" \
  --minutes 30
```

### 国际站连通验证（已测试通过）

```bash
TOKEN="d475109b22ee43c99a15adf915d895c7"
URL="http://venus-intl.cloud.qiyi.domain/log/api/v1/search/project/2586/query"
END_MS=$(date +%s%3N)
START_MS=$((END_MS - 30*60*1000))

curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_access\",
    \"queryString\": \"select count(*) from log_nginx_cache_access\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 1
  }"
# 返回: {"code":0,"data":{"hits":{"hits":[{"_source":{"count(*)":1073391}}]},...}}
```

---

## 1. 原始日志查询

### dash 无条件

```bash
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_access\",
    \"queryString\": \"select * from log_nginx_cache_access\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 10
  }"
```

### dash 带条件

```bash
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_access\",
    \"queryString\": \"select * from log_nginx_cache_access where st='312' and http_request='/dash'\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 50
  }"
```

### live 直播日志

```bash
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_livenewone_access\",
    \"queryString\": \"select * from log_nginx_livenewone_access where st='312'\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 50
  }"
```

### 解析 rawmessage（Python）

```python
import json

hits = resp["data"]["hits"]["hits"]
logs = [h["_source"]["rawmessage"] for h in hits if h.get("_source", {}).get("rawmessage")]
```

---

## 2. 错误日志查询（error 表）

查错误根因时用 error 表，不用 access 表。

### dash 错误日志（主站）

```bash
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_error\",
    \"queryString\": \"select * from log_nginx_cache_error where tvid='2163942648018300'\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 10
  }"
```

### 错误类型分布

```sql
select errortype, count(*) as cnt
from log_nginx_cache_error
group by errortype
order by cnt desc
limit 10
```

### live 错误日志（仅主站）

```sql
select * from log_nginx_livenewone_error where tvid='xxx'
```

国际站无 `log_nginx_livenewone_error`，查 live 错误需用主站或不支持。

### tvid 错误聚集（error 表）

```sql
select tvid, count(*) as cnt
from log_nginx_cache_error
group by tvid
order by cnt desc
limit 10
```

---

## 3. 聚合查询（推荐）

### 查总量

```sql
select count(*) from log_nginx_cache_access where st='312'
```

```bash
curl -s -X POST "$URL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{
    \"tableName\": \"log_nginx_cache_access\",
    \"queryString\": \"select count(*) from log_nginx_cache_access where st='312'\",
    \"startTime\": $START_MS,
    \"endTime\": $END_MS,
    \"size\": 1
  }"
```

返回示例：`{"_source": {"count(*)": 21041}}`

### tvid Top 10

```sql
select tvid, count(*) as cnt
from log_nginx_cache_access
where st='312'
group by tvid
order by cnt desc
limit 10
```

实测结果（2026-07-08 03:35~03:40）：

| tvid | cnt |
|------|-----|
| 90000100 | 20978 |
| 1795748523901300 | 52 |
| 15890900400 | 5 |

### 多维度 Top（tvid + 域名）

```sql
select tvid, host_domain, count(*) as cnt
from log_nginx_cache_access
where st='312'
group by tvid, host_domain
order by cnt desc
limit 10
```

### 按分钟趋势

```sql
select date_trunc('minute', from_unixtime(timestamp/1000)) as minute, count(*) as cnt
from log_nginx_cache_access
where st='312' and tvid='90000100'
group by 1
order by 1
```

### 去重用户数

```sql
select tvid, count(distinct k_uid) as uv, count(*) as pv
from log_nginx_cache_access
where st='312'
group by tvid
order by pv desc
limit 10
```

### 条件聚合（Trino FILTER 语法）

```sql
select tvid,
       count(*) filter (where host_domain like '%retry%') as retry_cnt,
       count(*) as total_cnt
from log_nginx_cache_access
where st='312'
group by tvid
order by total_cnt desc
limit 10
```

### 按 st 分布

```sql
select st, count(*) as cnt
from log_nginx_cache_access
where http_request='/dash'
group by st
order by cnt desc
limit 20
```

---

## 3. 实战：错误聚集分析

场景：今天早上 3:35~3:40，`st=312` 是否在 tvid 维度聚集？

```bash
START_MS=$(date -d '2026-07-08 03:35:00' +%s%3N)
END_MS=$(date -d '2026-07-08 03:40:00' +%s%3N)

# Step 1: 总量
curl -s -X POST "$URL" -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{\"tableName\":\"log_nginx_cache_access\",\"queryString\":\"select count(*) from log_nginx_cache_access where st='312'\",\"startTime\":$START_MS,\"endTime\":$END_MS,\"size\":1}"

# Step 2: tvid Top
curl -s -X POST "$URL" -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{\"tableName\":\"log_nginx_cache_access\",\"queryString\":\"select tvid, count(*) as cnt from log_nginx_cache_access where st='312' group by tvid order by cnt desc limit 10\",\"startTime\":$START_MS,\"endTime\":$END_MS,\"size\":10}"

# Step 3: 下钻 Top1 按分钟
curl -s -X POST "$URL" -H 'Content-Type: application/json' \
  -H "Authorization: Token $TOKEN" \
  -d "{\"tableName\":\"log_nginx_cache_access\",\"queryString\":\"select date_trunc('minute', from_unixtime(timestamp/1000)) as minute, count(*) as cnt from log_nginx_cache_access where st='312' and tvid='90000100' group by 1 order by 1\",\"startTime\":$START_MS,\"endTime\":$END_MS,\"size\":10}"
```

结论：`90000100` 占 20978/21041 ≈ 99.7%，强聚集。

---

## 4. 实战：错误聚集分析

```python
import json, urllib.request, subprocess

TOKEN = "b64d1fc4dc4a4fc2842d4c8c9038630c"
URL = "http://venus.cloud.qiyi.domain/log/api/v1/search/project/305/query"

def to_ms(timestr):
    return int(subprocess.check_output(["date", "-d", timestr, "+%s%3N"]).decode().strip())

def venus_query(table, query_string, start_ms, end_ms, size=100):
    body = json.dumps({
        "tableName": table,
        "queryString": query_string,
        "startTime": start_ms,
        "endTime": end_ms,
        "size": size,
    }).encode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {TOKEN}",
    }
    req = urllib.request.Request(URL, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)

def parse_hits(response):
    return [h["_source"] for h in response.get("data", {}).get("hits", {}).get("hits", [])]

# 示例
start = to_ms("2026-07-08 03:35:00")
end = to_ms("2026-07-08 03:40:00")
r = venus_query(
    "log_nginx_cache_access",
    "select tvid, count(*) as cnt from log_nginx_cache_access where st='312' group by tvid order by cnt desc limit 10",
    start, end, size=10,
)
for row in parse_hits(r):
    print(row)
```

---

## 6. 常见坑

| 问题 | 原因 | 解决 |
|------|------|------|
| `code: 100007` | Token 错误或不匹配站点 | 主站/国际站 Token 不通用 |
| `code: 100012` | 表不存在 | 国际站无 `log_nginx_livenewone_error` |
| `code: 0` 但 hits 为空 | 时间范围无数据 | 换最近时间或放宽条件 |
| 原始日志只有 5000 条 | 触达 size 上限 | 改用 `group by` 聚合 |
| `select top 10` 无排序 | 语法不含 order by | 用 `order by cnt desc limit 10` |
| shell 单引号嵌套报错 | JSON 转义问题 | 用双引号包裹 + 变量，或 Python 发请求 |
| st 聚集查错表 | access/error 混用 | st 分布用 access，错误根因用 error |
