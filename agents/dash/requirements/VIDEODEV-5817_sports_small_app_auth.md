# VIDEODEV-5817 体育业务小屏app支持

- PMS: VIDEODEV-5817
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5817
- 需求标题: 体育业务小屏app支持
- 开发分支: fan_5817_sports_small_app_auth
- 修改时间: 2026-06-04 16:20:17 CST
- Codex session Id: 019e82b1-f54d-7ba2-8abb-8c2d01e57544

## 背景

现有体育鉴权链路参照 pld：请求携带的 `platformId` 命中 `sports_cvt_skip_boss_platformid_list` 后，走体育 `authNew` 鉴权，并通过 `_cvt_sports_skip_boss` 跳过 boss 付费判断，后续在码流权益阶段按体育鉴权结果处理。

本需求要求为体育小屏 app 增加 `src` 白名单。只要请求 `src` 在白名单内，就复用上述体育鉴权链路，不区分付费视频和免费视频。

## 改动

1. `p911.vip.vip_right`
   - 新增本地函数 `should_sports_auth_check_by_platformid(request)`，统一判断是否走体育 `authNew` 鉴权。
   - 保留原有 `platformId` 白名单逻辑。
   - 新增 `src` 白名单配置 `sports_auth_src_white_list`，命中后设置 `_cvt_sports_skip_boss = true` 并调用 `sports_auth_check_by_platformid`。
   - `platformId` 参数逻辑不变：不做 `pf -> platformId` 映射兜底，请求未传 `platformId` 时不额外生成。

2. `spec/p911/vip/vip_right_spec.lua`
   - 补充 `platformId` 白名单原逻辑覆盖。
   - 补充 `src` 白名单命中后走体育 `authNew` 覆盖。
   - 补充 `src` 白名单命中但请求未传 `platformId` 时不做兜底的覆盖。

## 验证

- `luac -p vis-rule-engine/src/main/lua/p911/vip/vip_right.lua vis-rule-engine/src/main/lua/spec/p911/vip/vip_right_spec.lua`
- `busted spec/p911/vip/vip_right_spec.lua`

## 修改记录

### 2026-06-04 16:20:17 CST

- Codex session Id: 019e91b3-5fa5-76c3-800e-ae540e0c8116
- 背景: 调整 `sports_auth_check` 的前置鉴权条件作用范围，避免影响 `platformId/src` 白名单走体育 `authNew` 的逻辑。
- 改动:
  - 将 `(request.spt and request.spt ~= "" or request['_tsa'] == "01" or request._is_mainland_tv_or_tv_touping)` 从 `sports_auth_check` 外层条件下沉到非白名单分支的 `bossStatus == 0` 判断中。
  - `platformId/src` 白名单命中后仍可直接设置 `_cvt_sports_skip_boss` 并调用 `sports_auth_check_by_platformid`，不受上述条件限制。
  - 补充单测覆盖 `src` 白名单无 `spt` 仍走 `authNew`、非白名单无鉴权条件跳过旧体育鉴权、非白名单免费且有 `spt` 保持旧体育鉴权。
