# VIDEODEV-5813 国际站 dash 兼容新的内网域名

- PMS: VIDEODEV-5813
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5813
- 需求标题: 国际站：dash代码兼容新的内网域名相关逻辑
- 开发分支: fan_5813_intel2_cache_domain
- 修改时间: 2026-05-18 10:56:08 CST
- Codex session Id: 019e38fb-0800-7903-85c0-a3fa68bfedbe

## 背景

国际站已有内网域名 `intel-cache.video.qiyi.domain` 在线上使用，本次新增内网域名 `intel2-cache.video.qiyi.domain`，新域名内部走网关转发请求。代码层面要求新老内网域名功能保持一致。

## 实现原则

只在代码已经针对老内网域名逻辑做处理的位置补充新域名。对于只精确处理 `intel-cache.video.iqiyi.com` 的逻辑，不纳入本次改动，避免扩大到公网国际站域名行为。

## 改动

1. `utils/ip_address.lua`
   - 老逻辑通过国际站域名判断处理 `intel-cache.video.*` 域名下的 IP 兜底。
   - 改为调用 `utils.dash_utils.is_inter_domain(host)`，使 `intel2-cache.video.qiyi.domain` 走同样逻辑。

2. `p911/util/request_utils.lua`
   - `request_utils.is_inter_domain()` 改为复用 `utils.dash_utils.is_inter_domain(host)`。
   - 保证依赖国际站域名识别的功能对新内网域名与老内网域名保持一致。

3. `values/rule_value_collect.lua`
   - IP 采集流程中，老逻辑对国际站域名使用 `remote_addresses_intel`。
   - 改为调用 `utils.dash_utils.is_inter_domain(host)`，使新内网域名同样按国际站 IP 头优先级采集。

4. `utils/dash_utils.lua`
   - 新增 `dash_utils.is_inter_domain(host)` 公共方法，统一收敛国际站域名判断：
     - `intel%-cache.video.`
     - `intel2%-cache.video.`
     - `cache%-video.iq.com`

5. `AGENTS.md`
   - 更新分支命名规则：`fan_$PMS_NO_$需求描述简写` 中的 `PMS_NO` 只保留数字，不带 `VIDEODEV-` 前缀。

## 验证

- 使用 `rg` 确认 `intel%-cache.video.`、`intel2%-cache.video.`、`cache%-video.iq.com` 判断已收敛到 `utils/dash_utils.lua`。
- 查看 git diff，确认未改动只针对 `intel-cache.video.iqiyi.com` 的公网国际站逻辑。
- 执行 `luac -p` 检查 3 个 Lua 改动文件语法通过。
- 执行 `git diff --check`，项目代码仓库和知识库仓库均无空白问题。
