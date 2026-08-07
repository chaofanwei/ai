# VIDEODEV-5869 VR端新src申请添加各项VR白名单

## 背景

- PMS 标题: VR端新src申请添加各项VR白名单
- PMS 链接: http://pms.qiyi.domain/browse/VIDEODEV-5869
- 需求: 新申请的 `vr-pico-src=08023381010000000000` 需要和已有 VR 端功能一致，补齐各项 VR 白名单。

## 改动

修改源码仓库 `~/lua/projects/luna-rule-2/luna-rule`，基于最新 `master` 新建分支 `fan_5869_vr_pico_src_whitelist`。

1. 在 `p911/constants/constants.lua` 的 `vr_ptids` 中新增 `08023381010000000000`，使通用 VR 判断可识别新 src。
2. 在 VR 码流过滤与选择白名单中新增新 src：
   - `p911/rules/filter/format.lua`
   - `p911/rules/filter/vr.lua`
   - `p911/rules/filter/clarity.lua`
   - `p911/rules/video/select_rate.lua`
   - `p911/rules/video/vr_select_rate.lua`
3. 在 VR 音频、字幕、水印逻辑白名单中新增新 src：
   - `p911/rules/audio/vip.lua`
   - `p911/rules/subtitle/pre_filter.lua`
   - `p911/rules/video/watermark.lua`
4. 在 `p911/vip/dash_ctl.lua` 的 `vr_ptid_new` 中新增新 src，复用通用 VR 会员码流权益策略。
5. 未把新 src 加入 `09023871010000000000` 的奇遇专属会员规则，避免把专属 `ut=55` 策略误扩展给 pico。

## 验证

1. `luac -p` 检查以下文件通过：
   - `vis-rule-engine/src/main/lua/p911/constants/constants.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/audio/vip.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/filter/clarity.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/filter/format.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/filter/vr.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/subtitle/pre_filter.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/video/select_rate.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/video/vr_select_rate.lua`
   - `vis-rule-engine/src/main/lua/p911/rules/video/watermark.lua`
   - `vis-rule-engine/src/main/lua/p911/vip/dash_ctl.lua`
2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/video/vr_select_rate_spec.lua`，结果 `4 successes / 0 failures / 0 errors`。

## 修改时间

2026-07-17 14:08:32 CST

## 二次优化

- 修改时间: 2026-07-17 15:16:21 CST
- 背景: 新增 pico ptid 对标 `08020661010000000000`，同时确认部分文件内的 VR 本地 map 与 `constants.vr_ptids` 完全一致，可先做低风险统一。
- 改动:
  1. 在 `p911/constants/constants.lua` 中基于 `vr_ptids` 生成 `vr_ptid_map`，保留 O(1) 查表用法。
  2. 将以下 5 个完全一致的本地 VR map 替换为 `constants.vr_ptid_map`：
     - `p911/rules/filter/clarity.lua`
     - `p911/rules/filter/format.lua` 的 `vr_src`
     - `p911/rules/video/select_rate.lua`
     - `p911/rules/video/vr_select_rate.lua`
     - `p911/rules/audio/vip.lua`
  3. 未替换 `format.lua` 的 `vr_src_all`、`subtitle/pre_filter.lua` 的 VR 集合、`filter/vr.lua` 的规则 src 列表及奇遇专属逻辑，因为这些集合与 `constants.vr_ptids` 语义不完全一致。
- 验证:
  1. `luac -p` 检查 `constants.lua` 及上述 5 个业务文件通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/video/vr_select_rate_spec.lua`，结果 `4 successes / 0 failures / 0 errors`。

## 三次优化

- 修改时间: 2026-07-17 15:32:30 CST
- 背景: 继续简化二次优化代码，业务文件里不再定义 `local vr_srcs = constants.vr_ptid_map` 这类本地别名。
- 改动:
  1. 移除 `clarity.lua`、`format.lua`、`select_rate.lua`、`vr_select_rate.lua`、`audio/vip.lua` 中指向 `constants.vr_ptid_map` 的本地 VR 别名。
  2. 使用处直接引用 `constants.vr_ptid_map[...]`。
- 验证:
  1. `luac -p` 检查 `constants.lua` 及上述 5 个业务文件通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/video/vr_select_rate_spec.lua`，结果 `4 successes / 0 failures / 0 errors`。

## 四次优化

- 修改时间: 2026-07-17 15:51:14 CST
- 背景: `p911/rules/filter/vr.lua` 中前 4 组规则使用相同 src 白名单，但该白名单与 `constants.vr_ptids` 不完全一致，不能直接复用全局 VR ptid 集合。
- 改动:
  1. 在 `vr.lua` 内抽取 `vr_rule_src_white_list`。
  2. 前 4 组规则复用 `vr_rule_src_white_list`。
  3. 保留最后一组 `09023871010000000000` 奇遇专属规则不变。
- 验证:
  1. `luac -p vis-rule-engine/src/main/lua/p911/rules/filter/vr.lua` 通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/filter/vr_spec.lua`，结果 `3 successes / 0 failures / 0 errors`。

## 五次优化

- 修改时间: 2026-07-17 16:58:27 CST
- 背景: 明确 `17153381010000000000` 是 Apple Vision，`dash_ctl.lua` 的 `vr_ptid_new` 不包含 Apple Vision；`vr.lua` 前 4 组规则白名单等价于 `vr_ptid_new + ar_ptids`。
- 改动:
  1. 在 `constants.lua` 中新增 `vr_ptid_new`、`vr_ptid_apple_vision`。
  2. `vr_ptids` 改为由 `vr_ptid_new + vr_ptid_apple_vision` 组合生成，保持原通用 VR 集合语义。
  3. 新增 `vr_rule_ptids = vr_ptid_new + ar_ptids`，供 `vr.lua` 前 4 组规则直接引用。
  4. 新增 `vr_ptid_new_map`，供 `dash_ctl.lua` 的新 VR 音视频试看时长策略直接引用。
  5. `dash_ctl.lua` 同时改为直接引用 `constants.ar_ptid_map`，移除本地 AR map。
- 验证:
  1. `luac -p` 检查 `constants.lua`、`dash_ctl.lua`、`vr.lua` 通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/filter/vr_spec.lua`，结果 `3 successes / 0 failures / 0 errors`。

## 六次优化

- 修改时间: 2026-07-17 17:16:18 CST
- 背景: `format.lua` 的 `vr_src_all` 等价于 `constants.vr_ptids + 09023501010000000000 + 08021031010000000000`，可安全抽到 constants。
- 改动:
  1. 在 `constants.lua` 中新增 `vr_old_whole_ptids`。
  2. 新增 `vr_all_ptids = vr_ptids + vr_old_whole_ptids` 和 `vr_all_ptid_map`。
  3. `format.lua` 规则 17 改为直接引用 `constants.vr_all_ptid_map`。
  4. `format.lua` 本地 AR map 与 `constants.ar_ptid_map` 完全一致，已移除并直接引用 `constants.ar_ptid_map`。
- 验证:
  1. `luac -p` 检查 `constants.lua`、`format.lua` 通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/filter/vr_spec.lua`，结果 `3 successes / 0 failures / 0 errors`。

## 七次优化

- 修改时间: 2026-07-17 17:24:59 CST
- 背景: `subtitle/pre_filter.lua` 的 VR 集合等价于 `vr_ptids + vr_old_whole_ptids + subtitle_vr_extra_ptids`，本地 AR map 与 `constants.ar_ptid_map` 完全一致。
- 改动:
  1. 在 `constants.lua` 中新增 `subtitle_vr_extra_ptids`。
  2. 新增 `subtitle_vr_ptids = vr_ptids + vr_old_whole_ptids + subtitle_vr_extra_ptids` 和 `subtitle_vr_ptid_map`。
  3. `subtitle/pre_filter.lua` 移除本地 `vr_srcs` 和 `ar_srcs`，直接引用 `constants.subtitle_vr_ptid_map` 与 `constants.ar_ptid_map`。
- 验证:
  1. `luac -p` 检查 `constants.lua`、`subtitle/pre_filter.lua` 通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/subtitle/pre_filter_spec.lua`，结果 `7 successes / 0 failures / 0 errors`。

## 八次优化

- 修改时间: 2026-07-17 17:47:35 CST
- 背景: `watermark.lua` 中 VR/AR 纯净码流白名单与通用 VR/AR 集合基本一致，但奇遇 `09023871010000000000` 不应纳入 watermark 规则 4。
- 改动:
  1. 在 `constants.lua` 中新增 `vr_ptid_qiyu` 常量，避免业务代码继续写裸 ptid。
  2. `watermark.lua` 在 `unset_lgt_srcs` 定义后基于 `constants.vr_ptids` 追加 VR 端，追加时排除 `constants.vr_ptid_qiyu`，保持奇遇原有行为不变。
  3. `watermark.lua` 基于 `constants.ar_ptids` 追加 AR 端。
  4. `watermark.lua` 规则 4 仍统一通过 `unset_lgt_srcs[request.src]` 判断。
  5. `constants.lua` 给已知 VR ptid 补充注释：奇遇、Apple Vision；新加 `08023381010000000000` 注明 `VIDEODEV-5869 pico，对标 08020661010000000000`。
- 验证:
  1. `luac -p` 检查 `constants.lua`、`watermark.lua` 通过。
  2. 执行 `LUA_PATH='vis-rule-engine/src/main/lua/?.lua;vis-rule-engine/src/main/lua/?/init.lua;vis-rule-engine/src/main/lua/spec/?.lua;;' busted vis-rule-engine/src/main/lua/spec/p911/rules/video/watermark_spec.lua`，结果 `29 successes / 0 failures / 0 errors`。

## Codex Session

当前环境未暴露 `CODEX_SESSION_ID`，无法读取具体 session id。

## 九次修改

- 修改时间: 2026-07-28 CST
- 背景: 测试发现 `ft7_audio_try_time` 未开启时，新 pico src 会进入 `trail_config` 试看时长配置；因缺少新 src 配置，会回退到 `pf` 兜底配置，可能与对标 PTID 不一致。
- 改动:
  1. 在 `p911/vip/dash_ctl.lua` 的 `trail_config` 中新增 `08023381010000000000`。
  2. 配置与对标 PTID `08020661010000000000` 保持一致：`hX1080P`、`hXX1080P48`、`hX4K` 试看 360 秒，`h6K`、`hX6K`、`h8K`、`hX8K` 试看 60 秒。
- Codex Session: 当前环境未暴露 `CODEX_SESSION_ID`，无法读取具体 session id。
