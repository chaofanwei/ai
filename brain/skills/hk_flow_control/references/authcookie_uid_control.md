# Authcookie 与 UID 校验及发布

## 目录

- [适用范围](#适用范围)
- [校验矩阵](#校验矩阵)
- [实现约束](#实现约束)
- [Passport 调用与诊断](#passport-调用与诊断)
- [Nginx 限流冲突](#nginx-限流冲突)
- [测试与验收](#测试与验收)
- [代码单文件发布](#代码单文件发布)
- [2026-08-06 操作记录](#2026-08-06-操作记录)

## 适用范围

- 目标源码目录：`~/ai/brain/skills/hk_flow_control/luna-rule`。
- 固定分支：`fan_5891_oversea_abuse_block`。
- 目标文件：`vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua`。
- 目标 src：`01080031010000000000`。
- 不要把“mac-src”理解成 macOS 客户端 src。`01032001010000000000` 在仓库中虽标注为 PC OSX/macOS，但不是本策略目标。
- 校验必须位于 `pre_check:process()` 前部，在请求 VP 之前执行。
- 错误响应在 `pre_check.lua` 内定义为 `A00000 / st=522`，保持生产发布只需同步一个 Lua 文件。

## 校验矩阵

Authcookie 存在性必须覆盖四个入口：

1. 查询参数 `pck`；
2. 请求头 `pck`，在 request 中为 `http_pck`；
3. Cookie `P00001`，在 request 中为 `cookie_P00001`；
4. Cookie `I00001`，在 request 中为 `cookie_I00001`。

Lua 策略如下：

| 条件 | Passport | Lua 结果 |
|---|---|---|
| 非目标 src | 不调用 | 放行 |
| `uid` 为空 | 不调用 | 放行 |
| `uid` 非空、四种 authcookie 均为空 | 不调用 | `st=522` |
| `uid` 非空、存在 authcookie、Passport HTTP 调用失败且无响应 body | 调用失败 | 降级放行 |
| Passport 返回 body，但不是合法 JSON | 已返回 | `st=522` |
| Passport 返回业务错误或 JSON 中没有 `data.uid` | 已返回 | `st=522` |
| Passport UID 与请求 UID 不一致 | 已返回 | `st=522` |
| Passport UID 与请求 UID 一致 | 已返回 | 放行 |

比较 UID 时统一 `tostring`，避免 JSON 数字与查询参数字符串因类型不同被误判。

“Passport 无响应”与“Passport 有业务响应但无 UID”必须区分：前者用于服务故障降级，后者表示凭证无效或响应异常，应拦截。

## 实现约束

- 使用已有 `p911.http.passport:auth_cookie_uid(request)`，不要重复实现 HTTP 客户端。
- 该方法请求 `am.passport.qiyi.domain:80/apis/user/inner/uid.action`。
- 使用 `pcall(cjson.decode, body)`，非法 JSON 不得导致 Lua 请求异常。
- 收到响应 body 后，只有 `auth_data.data.uid` 非空才算 Passport 校验成功。
- 设置 `request._auth_cookie_uid_checked = true`，避免后续逻辑误以为尚未检查。
- Passport HTTP 无响应时保留 fail-open；如要改为 fail-close，必须单独评估 Passport 故障对 Dash 全量播放的影响。
- 保持错误模板在 `pre_check.lua` 内，不为该策略修改公共 `response_utils.lua`，方便远端单文件同步。
- 单测文件：`vis-rule-engine/src/main/lua/spec/p911/rules/pre/pre_check_spec.lua`。
- 单测至少覆盖：UID 一致、UID 不一致、无 cookie、UID 为空、非目标 src、HTTP 无响应、响应无 UID、非法 JSON。

## Passport 调用与诊断

诊断某个 pck 时，应使用和线上模块相同的参数与签名规则：

- `authCookie`：待检查 pck；
- `ptid`：`01080031010000000000`；
- `deviceId`：请求的 `k_uid`；
- `dfp`：请求的 `dfp`，没有则为空；
- `level=1`；
- `source=vrs-dash`；
- `timestamp`：当前毫秒时间；
- `sign`：严格按 `passport.lua` 中字段顺序和密钥计算 MD5。

只输出 Passport 的 `code`、`data.uid` 和 `msg`，不要在命令输出、Markdown、提交或通知中保存完整 pck。

已失效 pck 的典型响应是 `code=A00001` 且 `data.uid` 为空。此类响应属于“收到 JSON 但取不到 UID”，应返回 522，不得按网络故障放行。

## Nginx 限流冲突

现有 Nginx `limit_req` 也会匹配目标 src 的“不完整登录形态”。UID 非空但无 authcookie 时，请求可能在进入 Lua 前被 Nginx 拦截并包装为：

```json
{"code":"A00003","data":{"st":1513},"msg":["513"]}
```

因此要区分两件事：

- Lua 代码策略确实会对“UID 非空、无 cookie”返回 522；
- 线上通过普通 `/dash` 请求观察时，Nginx 可能先返回 1513，无法用该请求证明 Lua 的 522。

如果业务要求外部请求必须稳定看到 522，需要同步调整 Nginx 的 map/limit_req 条件，让“UID 非空、无 authcookie”不进入该限流 zone，交给 `pre_check.lua` 拦截。这会改变已有黑产限流行为，必须取得明确授权后再改。

不要为了测试临时关闭线上限流。用户明确接受跳过该功能验收时，仍需执行 MD5、`nginx -t`、reload 和备份门禁，并在交付中说明未验证外部 522。

## 测试与验收

本地运行：

```bash
cd ~/ai/brain/skills/hk_flow_control/luna-rule/vis-rule-engine/src/main/lua
~/shells/busted -v spec/p911/rules/pre/pre_check_spec.lua
```

项目规则要求在沙箱外执行该测试。2026-08-06 最终本地结果为 `32 successes / 0 failures / 0 errors`。

线上签名优先使用 Nobug `POST http://nobug.qiyi.domain/api/url/sign`：

- `src=01080031010000000000`；
- `v=a1`；
- `service=dash`；
- URL 更新 `tm` 并移除旧 `vf` 后再签名。

不要持久化测试 pck。有效凭证应由用户临时提供，测试完成后只记录场景和返回码。

可验收场景：

| 场景 | 预期 |
|---|---|
| 有效 pck + Passport 对应 UID | 正常响应，实测 `st=101` |
| 有效 pck + 其他 UID | `st=522` |
| 失效 pck，Passport 有 JSON 但无 UID | `st=522` |
| UID 非空、无 authcookie | Lua 预期 `st=522`；线上可能先被 Nginx 返回 `st=1513` |
| UID 为空 | 不进入 Lua 本策略；可能被现有 Nginx 限流 |

日志至少检查：

```text
auth_cookie_uid http failure
runtime error
not enough memory
lua entry thread aborted
stack traceback
```

## 代码单文件发布

- 跳板机：`ssh root@10.63.5.53 -p 443`。
- Pod 代码路径：`/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua`。
- 跳板机临时文件可用：`/tmp/pre_check.mac_uid.lua`。
- 每次发布前重新调用 Paas appunit details 接口获取 Ready Pod，不复用历史列表。
- 先计算本地 MD5，再上传跳板机并校验临时文件 MD5。
- 每台覆盖前备份为 `pre_check.lua.bak.YYYYmmddHHMMSS`。
- 先上传到 Pod 临时路径并核对 MD5，再覆盖目标文件。
- 每台执行 `/opt/soft/nginx/sbin/nginx -t`，成功后执行 `nginx -s reload`。
- `nginx -t` 或 reload 失败时，立即恢复该台备份并 reload，停止后续发布。
- 默认先灰度一台并验收，通过后再扩剩余 Pod；只有用户明确要求跳过功能验收时才可直接全量，但不能跳过备份、MD5、配置检查和 reload。
- 全量完成后逐台核对代码 MD5，避免新 Pod 或漏发机器仍运行旧版。

代码发布不需要同步 `/data/all.ip.txt`。IP 清单更新与该 Lua 单文件发布是两个独立动作，不要因为修改校验策略而覆盖 IP 文件。

## 2026-08-06 操作记录

当天确认并固化了以下知识：

1. 最初误把目标解释成 macOS src `01032001010000000000`，灰度后立即回滚；正确目标始终是本技能定义的 `01080031010000000000`。
2. 将校验从 `fetch_data_validate.lua` 移到 `pre_check.lua`，确保发生在 VP 请求前。
3. 将 `st=522` 错误模板内聚到 `pre_check.lua`，远端只需发布一个生产文件。
4. 第一版只在 Passport 成功取到 UID 后比较；随后修正为“只要有响应 body 但取不到 UID也失败”。
5. 最终新增“UID 非空但无 authcookie直接失败”，不调用 Passport。
6. 发现线上 Nginx 的未完整登录限流会先于 Lua 返回 `st=1513`；用户明确要求跳过该功能请求验收后，执行了全量发布。

版本和发布状态：

| 版本 | MD5 | 说明 |
|---|---|---|
| 已推送修正提交 `bd15c3613` 时的基线 | `c842d6b03f0a8a76289d3d27d9627f43` | 正确目标 src，UID 不一致返回 522 |
| Passport 有响应但无 UID 也失败 | `d5404eb0493bf844519063091512b271` | 曾全量发布并完成三场景验收 |
| UID 非空且无 authcookie直接失败 | `90d5bf92ebad6bfd9c27caa2b76375a5` | 2026-08-06 最终全量发布到 10 个 Pod |

最终发布时 10 台均完成备份、MD5 校验、`nginx -t` 和 reload；功能请求验收按用户明确要求跳过。Pod IP 是动态状态，不把当天列表当作下次发布目标，下次仍需通过 Paas 接口重新获取。

截至记录时，后两项优化仍是本地未提交修改；继续开发或跨机器同步前，先检查 `git status`，完成代码复核后再提交和推送，避免线上版本领先于仓库。
