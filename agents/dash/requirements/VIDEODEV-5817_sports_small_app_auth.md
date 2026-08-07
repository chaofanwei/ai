# VIDEODEV-5817 体育业务小屏app支持

- PMS: VIDEODEV-5817
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5817
- 需求标题: 体育业务小屏app支持
- 开发分支: fan_5817_sports_small_app_auth
- 修改时间: 2026-07-03 15:31:51 CST
- Codex session Id: 019f26a5-da06-7b03-be91-da99206c7f5f

## 背景

现有体育鉴权链路参照 pld：请求携带的 `platformId` 命中 `sports_cvt_skip_boss_platformid_list` 后，走体育 `authNew` 鉴权，并通过 `_cvt_sports_skip_boss` 跳过 boss 付费判断，后续在码流权益阶段按体育鉴权结果处理。

本需求要求为体育小屏 app 增加 `src` 白名单。只要请求 `src` 在白名单内，就复用上述体育鉴权链路，不区分付费视频和免费视频。

## 改动

1. `p911.vip.vip_right`
   - 新增本地函数 `should_sports_auth_check_by_platformid(request)`，统一判断是否走体育 `authNew` 鉴权。
   - 保留原有 `platformId` 白名单逻辑。
   - 新增 `src` 白名单配置 `sports_auth_src_white_list`，命中后设置 `_cvt_sports_skip_boss = true` 并调用 `sports_auth_check_by_platformid`。
   - `platformId` 参数逻辑不变：不做 `pf -> platformId` 映射兜底，请求未传 `platformId` 时不额外生成。
   - 体育小屏 `src` 白名单命中时，体育鉴权接口从 `/security/qp/authNew` 切到 `/xinai-video/auth/userAuth`；原 `platformId` 白名单仍使用 `/security/qp/authNew`。

2. `spec/p911/vip/vip_right_spec.lua`
   - 补充 `platformId` 白名单原逻辑覆盖。
   - 补充 `src` 白名单命中后走体育鉴权链路覆盖。
   - 补充 `src` 白名单命中但请求未传 `platformId` 时不做兜底的覆盖。
   - 补充体育小屏 `src` 白名单请求新接口、`platformId` 白名单保持旧接口的断言。

3. `p911.rules.pre.fetch_data_validate`
   - 在飞鲨数据获取并校验成功后，新增体育小屏请求非体育内容校验。
   - `src` 命中 `sports_auth_src_white_list` 且内容 `vipTypes` 不包含 `{1, 2, 6}` 时，直接返回 `st=501`。

4. `p911.util.response_utils`
   - 新增 `SPORTS_SMALL_APP_NON_SPORTS_CONTENT` 错误响应，返回 `code=A00000,data.st=501`。

5. `spec/p911/rules/pre/fetch_data_validate_spec.lua`
   - 覆盖体育小屏请求非体育内容返回 501。
   - 覆盖体育小屏请求体育内容继续流程。
   - 覆盖非小屏请求非体育内容不受该规则影响。

## 验证

- `luac -p vis-rule-engine/src/main/lua/p911/vip/vip_right.lua vis-rule-engine/src/main/lua/spec/p911/vip/vip_right_spec.lua`
- `busted spec/p911/vip/vip_right_spec.lua`
- `luac -p vis-rule-engine/src/main/lua/p911/util/response_utils.lua vis-rule-engine/src/main/lua/p911/rules/pre/fetch_data_validate.lua vis-rule-engine/src/main/lua/spec/p911/rules/pre/fetch_data_validate_spec.lua`
- `busted spec/p911/rules/pre/fetch_data_validate_spec.lua spec/p911/vip/vip_right_spec.lua`

## 修改记录

### 2026-06-04 16:20:17 CST

- Codex session Id: 019e91b3-5fa5-76c3-800e-ae540e0c8116
- 背景: 调整 `sports_auth_check` 的前置鉴权条件作用范围，避免影响 `platformId/src` 白名单走体育 `authNew` 的逻辑。
- 改动:
  - 将 `(request.spt and request.spt ~= "" or request['_tsa'] == "01" or request._is_mainland_tv_or_tv_touping)` 从 `sports_auth_check` 外层条件下沉到非白名单分支的 `bossStatus == 0` 判断中。
  - `platformId/src` 白名单命中后仍可直接设置 `_cvt_sports_skip_boss` 并调用 `sports_auth_check_by_platformid`，不受上述条件限制。
  - 补充单测覆盖 `src` 白名单无 `spt` 仍走 `authNew`、非白名单无鉴权条件跳过旧体育鉴权、非白名单免费且有 `spt` 保持旧体育鉴权。

### 2026-06-09 13:59:48 CST

- Codex session Id: 019eaae0-8f23-7333-aa05-ee6ba54f573f
- 背景: 新增需求点，来自体育小屏 app 的请求如果请求到非体育内容，需要前置返回 `st=501` 错误码，不进入后续体育鉴权和码流处理。
- 改动:
  - 在 `pre.fetch_data_validate` 获取并校验飞鲨数据后增加体育小屏内容类型校验。
  - 使用 `sports_auth_src_white_list` 判断体育小屏 app 请求来源，复用 `request_utils.is_sports_content(response)` 的体育内容口径，即 `vipTypes` 包含 `{1, 2, 6}`。
  - 新增 `response_utils.SPORTS_SMALL_APP_NON_SPORTS_CONTENT`，返回 `code=A00000,data.st=501`。
  - 新增 `spec/p911/rules/pre/fetch_data_validate_spec.lua`，覆盖小屏非体育内容返回 501、小屏体育内容继续流程、非小屏非体育内容不受影响。

### 2026-07-03 15:31:51 CST

- Codex session Id: 019f26a5-da06-7b03-be91-da99206c7f5f
- 背景: 体育小屏请求调用体育鉴权时，需要切换到新接口 `/xinai-video/auth/userAuth`，参数和返回沿用原 `/security/qp/authNew`。
- 改动:
  - `sports_auth_check_by_platformid` 改为由调用方显式传入鉴权接口路径，函数内不做默认路径兜底。
  - `sports_auth_src_white_list` 命中时传入 `/xinai-video/auth/userAuth`。
  - 原 `sports_cvt_skip_boss_platformid_list` 命中时继续传入 `/security/qp/authNew`。
  - 更新 `vip_right_spec.lua`，断言体育小屏 `src` 白名单请求新接口、平台白名单仍请求旧接口。

### 2026-07-10 15:35:48 CST

- Codex session Id: 本轮会话未暴露
- 背景: 按要求在 `vip_right.lua` 的 5817 判断逻辑处补充 PMS 注释，便于后续定位需求来源。
- 改动:
  - 在 `should_sports_auth_check_by_platformid` 函数前新增 `PMS VIDEODEV-5817 体育业务小屏app支持` 注释。
