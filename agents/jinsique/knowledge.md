# 金丝雀运维知识点

## Dash-主站「已对比请求数」为空

- **展示逻辑**：`dial-i` 读 `/dash/dial/diffMainData` 的 `totalNum`；为 `null` 时页面显示 `-`。
- **数据来源**：MySQL `logsearch` 库（tiros-dial 线上 `starmap.*.db.url` 指向 `sh.dbtest1`）表 `tiros_platform_version_statistics`，`SUM(num) WHERE env_id=1 AND platform_name != 'cube'`。
- **重置**：`resetDiff` 会归档并 `deleteAllPfVerRecordsByEnvId`，本轮统计从 0 开始；未落库前接口为 `null`。
- **落库条件**（`EnvUnit.maybeFlushPlatformStatistics`）：主站 envId=1 内存合计 **>800**、其他 env **>200** 时落库；或 **本 env 有计数且距上次落库 ≥1 分钟** 也会落库（避免长期达不到 800 时页面无已对比数）。`tiros_env_lock.update_time` 会随落库刷新。
- **与游标区别**：`tiros_cursor_lock.max_cursor` 推进只说明在消费 Mongo 访问日志；**REQUEST_IGNORE**（host 黑/白名单等）也会推进游标，但**不会**调用 `setSrcPlatformStatistics`，统计不涨、不落库。
- **主站 vs 国际站数据源（易混点）**：
  - 表 `tiros_dial_datasource` 仅一条 dash：`queue=nginx_cache_access_sample`；Mongo 集合 `nginx_cache_access`（`NginxCacheAccess.group` 有 `intl`/空等）。
  - **所有 Dash envPair（含 envId=1 主站、7 国际站）共用同一 `dashAccessService`**，`queryLatest` **不按 `group` 过滤**；`ConfigService.dial_group` 配置项**代码里未使用**。
  - envId=1 白名单：`cache.video.ptqy.gitv.tv|cache.video.iqiyi.com|sdk-cache.video.ptqy.gitv.tv`；黑名单含 `iq.com`/`intel`。
  - envId=7 白名单：`.*iq.com|.*intel.*`（国际站 host）。
  - `iq.com` / `intel*-cache` 日志的 Mongo `group` 多为 **`intl`**，属于**国际站语义**，不是主站应对比的样本。
- **2026-10-10 案例**：reset tid=266 后 env_id=1 统计 0 行、游标仍推进；reset 后抽样 500 条 Mongo 日志 **`group=intl` 占满**，主站白名单 host **0 条** → 主站 env 对这些记录只会 `REQUEST_IGNORE`，**不是落库锁/游标卡死**，而是**主站在共享流里几乎捞不到大陆 host 有效样本** → `totalNum` 为空。国际站 env7 同流可对比故仍有数。
