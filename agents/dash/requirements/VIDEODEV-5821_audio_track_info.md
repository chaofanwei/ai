# VIDEODEV-5821 多音轨需求-提前获取音轨信息

## 背景

国际站需要新增独立音轨查询接口 `/audioTrack`，用于在播放前提前获取可用音轨信息和默认选中音轨。该接口不走 `/dash` 播放主流程，不做鉴权、视频码流过滤、DRM、MUS、播放地址封装等逻辑。

需求链接：http://pms.qiyi.domain/browse/VIDEODEV-5821

## 实现分支

基于 `fan_5804_intel_audio_su3_strategy` 新建分支：

`fan_5821_audio_track_info`

## 改动内容

1. 在 `p911.select.intel_audio_selection` 中复用并暴露国际站音轨公共能力：
   - `find_location`
   - `get_location_prio`
   - `get_limit_audio`
   - `select_audio_by_prio`
   - `select_audio_track`

2. 新增 `vis-rule-engine/src/main/lua/p911/audio/audio_track_service.lua`：
   - 校验 `tvid/src`，`applang` 非必传，`su/lid` 缺省按 `0` 处理。
   - 校验 `src_inter`，非国际站返回 `A00001`。
   - 调用 `p911.http.fshark.fetch_video_data(request)` 获取 VP 元数据。
   - 解析并校验 VP 返回基础结构，`p` 允许为空。
   - `data.p.dal` 为空或 0 时，按 `/dash` 逻辑从 `program.video[1].lid` 兜底。
   - 只执行国际站音轨白名单过滤和 `su` 选择策略。
   - 使用 `subtitle_audio_trans` 生成音轨展示名，语言未命中时 fallback 到 `en_us`。
   - 返回精简音轨列表和 `audioInfo.dal`；没有选中音轨时不返回 `selected_lid`。
   - 没有可返回音轨时仍返回 `A00000`，`audio` 为空数组。

3. 新增 `vis-rule-engine/src/main/lua/p911/audio_track.lua`：
   - 作为 `/audioTrack` 独立 Lua 入口。
   - 复用 `core.rule_process:req_values()` 收参。
   - 复用 `values.config_file_data:set_config_data()` 注入月神配置。
   - 输出 JSON 响应。

4. `/audioTrack` 不接入防盗链验证，不修改 `vis-rule-engine/src/main/lua/config/intface_config.lua`。

5. 新增 `vis-rule-engine/src/main/lua/spec/p911/audio/audio_track_service_spec.lua`：
   - 覆盖成功响应、`su=3` 选择、翻译 fallback、`applang` 非必传、非法请求、飞鲨异常、过滤后无音轨、音轨节点缺失和 `dal` 兜底。

6. 新增 `/audioTrack` 专用 metrics：
   - `audio_track_requests_code_total`: 按 `code` 统计请求量和业务错误码。
   - `audio_track_requests_status_total`: 按 HTTP `status` 统计请求量。
   - `audio_track_request_duration_seconds`: 统计接口耗时。
   - `/audioTrack` 不设置也不统计 `st`。

## 错误码

- `A00000`: 成功。
- `A00001`: 参数非法或非国际站请求。
- `A00003`: VP/飞鲨数据获取或解析失败，或返回结构缺失。

## 修改时间

2026-06-01 13:11:57 CST

2026-06-03 14:38:22 CST

## 本次修改

- 将 `/audioTrack` 的 `applang` 参数改为非必传。
- 不主动给 `request.applang` 设置默认值；未传或未命中翻译配置时，沿用现有 `subtitle_audio_trans['en_us']` fallback。
- 补充 `applang` 缺省场景单测，验证接口返回 `A00000` 且音轨名称使用 `en_us` 翻译。

## Codex Session

`019e8106-5751-7a03-9960-886c94f27ae7`

`019e8c30-e3dd-7802-a8a9-933142c87316`
