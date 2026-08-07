# VIDEODEV-5817 体育业务小屏app支持

- PMS: http://pms.qiyi.domain/browse/VIDEODEV-5817
- 修改时间: 2026-07-10 15:46:42 CST
- Codex session id: 019e829f-140c-7ea3-a3ba-6f63853d8070
- 本次修改 Codex session id: 019f1c7b-3c56-79e2-af58-3d3f61c9a32d

## 背景

现有逻辑参照 pld 配置 `sports_auth_platform_ids`，体育内容命中特定渠道时走体育鉴权 `/security/qp/authNew`。

本需求需要增加体育 `src` 白名单：白名单内的体育内容请求都走体育鉴权，不区分付费视频或免费视频。

2026-06-09 追加调整：来自小屏 `src` 白名单的请求如果访问非体育内容，需要直接返回 `A00110` 平台受限错误。

2026-07-01 追加调整：体育小屏请求在调用体育鉴权时，需要请求新的 `/xinai-video/auth/userAuth` 接口，参数和返回保持与原 `/security/qp/authNew` 一致。

## 改动

1. 在 `vis-rule-engine/src/main/lua/p918/rules/pre_check.lua` 增加 `sports_auth_src_white_list` 配置判断。
2. 体育内容请求命中 `sports_auth_platform_ids` 或 `sports_auth_src_white_list` 任一配置时，设置 `request._is_sports_auth = true`。
3. 保留原有 `lp` 为空时拦截逻辑。
4. 补充 `vis-rule-engine/src/main/lua/spec/p918/rules/pre_check_spec.lua` 单测，覆盖 pld 命中、src 命中、未命中、lp 为空拦截。
5. 追加小屏 `src` 白名单请求非体育内容时的拦截逻辑，返回 `response_utils.COPY_RIGHT_OFFLINE`，即 `A00110`。
6. 补充单测覆盖 `src` 命中白名单但内容 `vipTypes` 非体育时返回 `A00110`。
7. 在 `vis-rule-engine/src/main/lua/p918/rules/boss_proxy.lua` 中，体育鉴权请求根据 `request._sports_from_src` 分流：体育小屏 `src` 请求调用 `/xinai-video/auth/userAuth`，原 `pld` 体育鉴权继续调用 `/security/qp/authNew`。
8. 补充 `vis-rule-engine/src/main/lua/spec/p918/rules/boss_proxy_rule_spec.lua` 单测，覆盖小屏 `src` 使用新接口、`pld` 仍使用旧接口。
9. 2026-07-10 在 `vis-rule-engine/src/main/lua/p918/rules/pre_check.lua` 中补充 `VIDEODEV-5817` PMS 注释，标记体育小屏 `src` 白名单相关逻辑来源。

## 验证

- 已检查代码 diff。
- 已执行单测：`LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;vis-rule-engine/src/main/lua/spec/?/init.lua;;' ~/shells/busted vis-rule-engine/src/main/lua/spec/p918/rules/pre_check_spec.lua`
- 结果：13 successes / 0 failures / 0 errors。
- 2026-07-01 已执行单测：`LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;vis-rule-engine/src/main/lua/spec/?/init.lua;;' ~/shells/busted vis-rule-engine/src/main/lua/spec/p918/rules/pre_check_spec.lua vis-rule-engine/src/main/lua/spec/p918/rules/boss_proxy_rule_spec.lua`
- 结果：16 successes / 0 failures / 0 errors。

## 分支

`fan_5817_sports_src_auth`
