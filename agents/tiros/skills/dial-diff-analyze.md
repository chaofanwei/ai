# Skill：Dash 技术对比差异分析

用户描述「主站/国际站某个 `JSON.data...` 差异」时执行本流程。  
详细背景见 `./tiros/tiros-dial/Readme-diff-check.md`。  
源码根目录：`./tiros/`（只读分析）。临时脚本写到 `./temp/`。

---

## 0. 连接与环境（分析必备）

### MySQL（配置 / reset / 符合预期）

```
host: sh.dbtest1.w.qiyi.db
port: 8381
db:   logsearch
user: logsearch
pass: dfyIkF3Y
```

常用表：

| 表 | 用途 |
|--|--|
| `tiros_dial_env_pair` | ignore / uri_fields_rule / env1 / env2 |
| `tiros_reset_diff_record` | 当前对比周期（`end_time IS NULL`） |
| `tiros_meet_expectation` | UI「符合预期」 |

### Mongo（差异结果）

```
mongodb://vrs_service_monit:8RJNmlh98j6t@vrs-service-monit-1.qiyi.mongo:27002,vrs-service-monit-2.qiyi.mongo:27002/tiros?authSource=admin
collection: dial_result
注意字段名是 envPairId（不是 envId）
```

### env 对照

| envId | 名称 | 说明 |
|--|--|--|
| 1 | 预发布-dash（主站） | 默认 |
| 7 | 国际站-dash | 用户提国际站时用 |

运行时 `env1`/`env2` IP 以库为准：

```sql
SELECT id, name, env1, env2, `ignore` FROM tiros_dial_env_pair WHERE id IN (1,7);
SELECT id, env_id, create_time, end_time FROM tiros_reset_diff_record
 WHERE env_id IN (1,7) AND end_time IS NULL;
```

### 工具链

本机通常有：

- JDK：`/data/soft/jdk1.8.0_131/bin/java`
- MySQL driver：`~/.m2/repository/mysql/mysql-connector-java/8.0.29/mysql-connector-java-8.0.29.jar`
- Mongo driver：`~/.m2/repository/org/mongodb/mongo-java-driver/3.11.2/mongo-java-driver-3.11.2.jar`
- Fastjson1：`~/.m2/repository/com/alibaba/fastjson/1.2.83/fastjson-1.2.83.jar`
- 临时脚本可写到 `./temp/`

若无 pymongo/pymysql，用上面 Java 驱动即可。

---

## 1. 标准排查步骤（按顺序）

### Step A：锁定样本

1. 取当前 reset：`create_time` 作为 `since`，`id` 作为 `tid`
2. 查 Mongo：

```
envPairId = {1|7}
updateTime > since
simpleUnequalKey 匹配用户给的 key（可用 regex，注意 [X]）
优先 tag=0；若无则看最新任意 tag
```

输出：条数、tag/retryNum 分布、最新几条的 tvid / unequalKey / updateTime。

### Step B：判差异形态

对每条样本解析 `productRespnse`（线上）与 `prereleaseResponse`（预发）：

1. `code` / `st` 是否一致  
2. 目标字段是 **值不同** 还是 **一侧缺失**  
3. 若在 `program.video/audio` 下：按 **vid** 对齐后再比（与代码 `CommonComparator` 一致）  
4. 同时看 `_selected` / `ft` / `etid` / `play` / `bid` / `ff`  
5. 从 `message` 抽参数：`vt` / `bid` / `abid` / `src` 等  

### Step C：对照规则是否本应忽略

1. 读库里 `ignore`，用 `Pattern.matches(ignore, path)` 测：  
   - `JSON.data....video[0].xxx`（把 `[X]` 换成 `[0]`）  
2. 记住：**ignore 要求两边节点都非 null**；缺失型盖不住  
3. 浅对比规则见代码 `JsonCompareUtil.SHALLOW_COMPARE_RULES`：  
   - 只在两边都是对象时生效；一侧 null 仍报  
4. `vt=4`：若代码已部署，技术对比应只比 code/st；仍出现 JSON 差异说明未部署或请求不是 vt=4  

### Step D：需要时查 VP 底数

区分「VP 就不一样」还是「dash 裁的」：

| 环境 | URL | Host |
|--|--|--|
| 预发 VP | `http://10.72.11.143/cache?tvId={tvid}` | `fshark.video.qiyi.smart` |
| 线上 VP | `http://vp-bdxs.qsm.qiyi.middle/cache?tvId={tvid}` | `vp-bdxs.qsm.qiyi.middle`（解析多为 `10.61.232.34`） |

注意：

- 参数名必须 `tvId`（不是 `tvid`）  
- 线上 Host 用 fshark 会 404  
- 预发冷 cache 可能空 body：先打预发 dash 再查  

### Step E：需要时重放 dash

1. 从 Mongo `message` 抽 `/dash?...`  
2. nobug 重签：`POST http://nobug.qiyi.domain/api/url/sign`  
   body: `{"url":"<去vf并更新tm后的path>","src":"<src>","v":"1","service":"dash"}`  
3. Header 带 `Host`、`pck`（日志 `hpck:`）、`x-real-ip`（remote）、`User-Agent`  
4. 打 `env1` / `env2` IP，对比目标字段是否仍不一致  

空壳特征：`ctl.num=3` 且无 `program` → 签名/鉴权/header 不对，不能当结论。

### Step F：输出结论模板

用中文，尽量短：

1. **一句话根因**  
2. **证据表**（tvid / 两边值或有无 / retryNum / 是否 vt=4）  
3. **归类**：选流 / VP 底数 / ignore 未覆盖 / 瞬时（看 tag=1）/ 其它  
4. **建议**：人工判断 / 加 ignore / 标符合预期 / 找 dash 或 VP 同学  
5. 用户若要转发，再给**可复制纯文本表格**（含 IP/Host）  

---

## 2. 常见根因速查

| 差异 key | 常见原因 |
|--|--|
| `video/audio[X].ms` | 签名 query，应 ignore；检查 ignore 是否含 `ms` |
| `bmsg.*` | 缓存指纹；现多用浅对比 depth=2 |
| `video[X].etid` / `ft` / `play` / `_selected` | **选流不一致**（`_selected=true` 落在不同 vid；常伴随 ff/bid/ft 不同）。`vt=4` 尤甚 |
| `video[X].uea` | 打标集合不一致；不全是选中流专属；多为有无差异 |
| `content.croIds` | 常为 **VP content 就不一致**（线上有、预发无） |
| `p.nsdl.timestamp` | 时间戳，应 ignore |
| 裸 `video[X].play` | 旧 ignore `play.\S+` 匹配不到裸 play；或一侧缺 play 节点（人工） |

选流判定要点：

- 每边有且仅有（或极少）`_selected=true` 的码流  
- 对齐后若 true 落在不同 vid → 报 `_selected`/`ft`/`etid`/`play` 都正常  
- `ft` 常只在选中流；选中流常无 `etid`  

tag 含义：`0` 未处理；`1` 重试后一致；`2` 符合预期；`3` 不符合预期。  
`retryNum=10` 表示自动重试已耗尽，**不是瞬时抖动**。

---

## 3. 自动重试（知道即可）

`DialResultTimer.doDiffTask` 约 10s 一次：对 `tag=0 && retryNum<10` 用原 message **重新 HTTP 两边再比**（默认不 resign）。  
变 EQUAL → `tag=1`；否则只加 `retryNum`。

分析时先看 `tag`/`retryNum`，避免把已消掉的差异当现行故障。

---

## 4. 批量「符合预期」（需用户确认）

正规接口：`/apis/dial/ignore_diff_group`  
本质：Mongo `tag=0→2` + 写 `tiros_meet_expectation`（`tid`=当前 reset，`from_type=1`，`diff_type=1`）。

**不要**在未确认时批量改线上数据。

---

## 5. 代码阅读入口

| 文件 | 看什么 |
|--|--|
| `tiros/tiros-dial/.../DashEnvOperation.java` | compare 流程、vt=4、bmsg 短路 |
| `tiros/tiros-dial/.../JsonCompareUtil.java` | ignore / 浅对比 / 数组 sort |
| `tiros/tiros-dial/.../CommonComparator.java` | 按 vid 排序 |
| `tiros/tiros-dial/.../DialResultTimer.java` | 差异重试 |
| `tiros/tiros-dial/.../DashSignUtil.java` | nobug 重签 |

---

## 6. 最小可运行查询骨架（Java）

把脚本写到 `temp/`，用 JDK + mongo/mysql/fastjson jar 编译运行。典型流程：

1. MySQL 取 `since` / `ignore` / `env1`/`env2`  
2. Mongo 按 `simpleUnequalKey` 拉最新样本  
3. fastjson 解析 pro/pre，按 vid 打印目标字段与 `_selected`  
4. 需要则 curl VP / 重放 dash  

具体字段解析逻辑参考本 skill 第 1 节与 `./tiros/tiros-dial/Readme-diff-check.md`。
