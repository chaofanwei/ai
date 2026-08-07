# VIDEODEV-5884 audioTrack接口支持跨域请求

## 背景

目前 `/audioTrack` 接口未设置跨域响应头，WebTV 无法通过浏览器跨域访问该接口，需要仿照 `/dash` 接口支持跨域请求。

需求链接：http://pms.qiyi.domain/browse/VIDEODEV-5884

## 实现分支

基于最新 `master`（`35df4282f`）新建分支：

`fan_5884_audiotrack_cors`

## 改动内容

修改 `vis-rule-engine/src/main/lua/p911/audio_track.lua`：

- 引入 `/dash` 已有的 `p911.rules.post.body_filter`。
- 在 `/audioTrack` 输出响应前调用 `body_filter:add_xhr_header(request)`。
- 复用 `/dash` 的现有跨域策略，不重复实现判断逻辑：
  - `ori=pcw/h5` 时支持跨域。
  - 从 HTTP Referer 提取来源并设置 `Access-Control-Allow-Origin`，无法提取时使用 `*`。
  - 设置 `Access-Control-Allow-Credentials: true`。
  - 设置 `Timing-Allow-Origin`。

## 影响范围

- 仅修改 `/audioTrack` 独立入口。
- 不改变音轨查询、过滤、选择及返回体逻辑。
- 不修改 `/dash` 的现有跨域行为。

## 验证

- `luac -p p911/audio_track.lua`：通过。
- `audio_track_service_spec.lua` 与 `body_filter_spec.lua`：16 successes，0 failures，0 errors。
- `git diff --check`：通过。

## Bug 修复：VP 请求缺少 request_utils 初始化

### 背景

`/audioTrack` 请求需要穿透到 VP 接口时，`fshark.get_from_vp` 会通过
`request_utils.get_qsm_host` 读取配置。由于 `/audioTrack` 是独立入口，没有经过
`p911.core.lua_process`，因此未执行 `request_utils.init(request)`，访问
`ngx.ctx.m_request` 时产生运行时错误：

`attempt to index field 'm_request' (a nil value)`

### 改动

- 在 `p911/audio_track.lua` 中引入 `p911.util.request_utils`。
- 完成 `config_file_data:set_config_data(request)` 后、调用
  `audio_track_service:process(request)` 前执行 `request_utils.init(request)`。
- 新增 `spec/p911/audio_track_spec.lua` 入口级回归测试，验证调用 service 前
  `ngx.ctx.m_request` 已初始化为当前请求。

### 验证

- `luac -p p911/audio_track.lua`：通过。
- `audio_track_spec.lua`、`audio_track_service_spec.lua` 与
  `body_filter_spec.lua`：17 successes，0 failures，0 errors。
- `git diff --check`：通过。

## 修改时间

- 初次实现：2026-07-24 13:45:37 CST
- Bug 修复：2026-07-31 14:19:08 CST

## Codex Session

- 初次实现：`019f929b-aecc-7fa1-82aa-349baf568ff3`
- Bug 修复：`019fb6cd-eba8-7221-a8f7-360a095f0a79`
