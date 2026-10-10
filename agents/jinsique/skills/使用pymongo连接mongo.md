# 使用 PyMongo 连接拨测 Mongo（monitor.tiros）

用于查询 Dash/Live 拨测写入的访问日志（如 `nginx_cache_access`），与线上一致。配置来源与 `tiros-dial` 中 `MongodbClientFactory` / `MonitorTirosMongoResource` 相同。

## 1. 环境与版本（必读）

线上集群为 **MongoDB 3.2.x**（副本集 `vrs_service_monit`）。

| PyMongo 版本 | 结果 |
|--------------|------|
| **4.x** | 易出现 `connection closed`，**不要用** |
| **3.12～3.13** | 与 tiros Java 驱动行为一致，**推荐** |

安装：

```bash
pip install 'pymongo>=3.12,<4'
python3 -c "import pymongo; print(pymongo.version)"   # 应输出 3.x
```

## 2. 连接串从哪里来

`tiros-dial` 配置文件（以线上为准）：

- `tiros/tiros-dial/src/main/resources/application-product.properties`
- 键名：`mongodb.monitor.tiros`

示例格式（**无** `mongodb://` 前缀，tiros 自行解析）：

```text
vrs-service-monit-1.qiyi.mongo:27002,vrs-service-monit-2.qiyi.mongo:27002/tiros/用户名:密码?authSource=admin
```

tiros 解析后会等价于（注意 **`readPreference=secondaryPreferred`**）：

```text
mongodb://用户名:密码@vrs-service-monit-1.qiyi.mongo:27002,vrs-service-monit-2.qiyi.mongo:27002/tiros?authSource=admin&readPreference=secondaryPreferred
```

密码不要写进文档或提交 git；本地用环境变量或读配置即可，例如：

```bash
export MONGO_USER=vrs_service_monit
export MONGO_PASSWORD='从 application-product.properties 或密钥系统获取'
```

Compass 常用单节点 URI（`directConnection=true`、`readPreference=primary`）在 **PyMongo 4** 下也可能失败；脚本侧请用 **双节点 + PyMongo 3.x**，与 tiros 一致。

## 3. 连接与 ping

```python
import os
import pymongo

user = os.environ["MONGO_USER"]
password = os.environ["MONGO_PASSWORD"]

uri = (
    f"mongodb://{user}:{password}@"
    "vrs-service-monit-1.qiyi.mongo:27002,"
    "vrs-service-monit-2.qiyi.mongo:27002/tiros"
    "?authSource=admin&readPreference=secondaryPreferred"
)

client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=15000, connectTimeoutMS=15000)
client.admin.command("ping")
db = client["tiros"]
print("ping ok")
```

## 4. 拨测相关库表

| 项 | 值 |
|----|-----|
| 数据库 | `tiros` |
| Dash 访问日志集合 | `nginx_cache_access`（实体 `NginxCacheAccess`，字段含 `group`、`message`、`timestamp` 等） |
| 差异结果集合 | `dial_result`（字段 `envPairId` 等，见 `Readme-diff-check.md`） |

MySQL 侧 env / 游标 / 统计在 `logsearch` 库，见 `skills/调用接口修改表数据.md` 与 `knowledge.md`，**不要与 Mongo 混淆**。

## 5. 常用查询示例

### 5.1 某时间段按 `group` 计数

```python
RESET_TS = 1791620850000   # 按实际 reset 时间改
now = int(__import__("time").time() * 1000)

pipeline = [
    {"$match": {"timestamp": {"$gte": RESET_TS, "$lte": now}}},
    {"$group": {"_id": "$group", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
]
for doc in db.nginx_cache_access.aggregate(pipeline, allowDiskUse=True):
    print(doc)
```

### 5.2 主站白名单 host（与 envId=1 hostWhiteRule 一致）

```python
mainland_re = r"cache\.video\.ptqy\.gitv\.tv|cache\.video\.iqiyi\.com|sdk-cache\.video\.ptqy\.gitv\.tv"
n = db.nginx_cache_access.count_documents({
    "timestamp": {"$gte": RESET_TS, "$lte": now},
    "message": {"$regex": mainland_re},
})
print("mainland whitelist host count:", n)
```

### 5.3 国际站常见 host（粗略）

```python
intl_re = r"cache-video\.iq\.com|intel.*-cache\.video"
n = db.nginx_cache_access.count_documents({
    "timestamp": {"$gte": RESET_TS, "$lte": now},
    "message": {"$regex": intl_re},
})
print("intl-like host count:", n)
```

## 6. Java 等价验证（可选）

与 PyMongo 同配置的单测（不依赖 PyMongo 版本）：

```bash
cd tiros && mvn -q install -DskipTests -pl tiros-mongo,tiros-dao,tiros-common,tiros-dial -am
cd tiros/tiros-dial && mvn -q test -Dtest=MongoNginxAccessStatsTest#verifyMainlandVsIntlSamplesSinceReset
```

测试类：`tiros/tiros-dial/src/test/java/com/qiyi/tiros/dial/MongoNginxAccessStatsTest.java`

## 7. 故障排查

| 现象 | 处理 |
|------|------|
| `connection closed`，TCP 27002 通 | 先查 PyMongo 是否 4.x，降为 3.13 |
| 单节点 URI 失败 | 改用双节点 + `readPreference=secondaryPreferred` |
| 与 Compass 不一致 | Compass 可能用 primary；tiros 默认读 secondaryPreferred |
| 本机仍失败 | 确认 VPN/办公网；与 tiros 部署机出口是否同一策略 |

## 8. 安全

- 勿将 `MONGO_PASSWORD` 写入 skill 副本外的公开仓库。
- 只读排查优先用 `aggregate` / `find`；写操作需变更流程，勿在生产 Mongo 上随意改数。
