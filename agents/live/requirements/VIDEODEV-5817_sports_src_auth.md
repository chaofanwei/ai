# VIDEODEV-5817 体育业务小屏app支持

- PMS: http://pms.qiyi.domain/browse/VIDEODEV-5817
- 修改时间: 2026-06-01 18:06:48 CST
- Codex session id: 019e829f-140c-7ea3-a3ba-6f63853d8070

## 背景

现有逻辑参照 pld 配置 `sports_auth_platform_ids`，体育内容命中特定渠道时走体育鉴权 `/security/qp/authNew`。

本需求需要增加体育 `src` 白名单：白名单内的体育内容请求都走体育鉴权，不区分付费视频或免费视频。

## 改动

1. 在 `vis-rule-engine/src/main/lua/p918/rules/pre_check.lua` 增加 `sports_auth_src_white_list` 配置判断。
2. 体育内容请求命中 `sports_auth_platform_ids` 或 `sports_auth_src_white_list` 任一配置时，设置 `request._is_sports_auth = true`。
3. 保留原有 `lp` 为空时拦截逻辑。
4. 补充 `vis-rule-engine/src/main/lua/spec/p918/rules/pre_check_spec.lua` 单测，覆盖 pld 命中、src 命中、未命中、lp 为空拦截。

## 分支

`fan_5817_sports_src_auth`
