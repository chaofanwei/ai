# VIDEODEV-5849 支持多色彩范围合并生产

- PMS标题：支持多色彩范围合并生产
- PMS链接：http://pms.qiyi.domain/browse/VIDEODEV-5849
- 修改时间：2026-07-30
- Codex session Id：019fb23d-d59e-7233-a4ff-cec9e8b94eca

## 背景

生产侧将多个色彩范围的码流合并生产，通过基础码流附加 meta 文件的方式生成
EDR10、ADR 和 DV8.1 码流，以提升 P2P 分享比并降低带宽成本。

飞鲨 vp 接口为 meta 码流新增 `metaFile` 字段，并新增 `dr=9`（ADR）、
`dr=10`（DV8.1）。

## 改动

1. 将已有第 5 位 `ftx2_adr` 重命名为 `ftx2_adr_type`，继续控制原 ADR 类型字段。
2. 使用 `k_ftx2` 新 feature：
   - 第 7 位 `ftx2_adr`：是否支持 ADR。
   - 第 8 位 `ftx2_dv81`：是否支持 DV8.1。
   - 第 9 位 `ftx2_meta_rate`：是否支持 meta 码流。
3. 按色彩范围能力和 meta 码流能力过滤码流，DASH 直接下发飞鲨返回的
   `metaFile` 字段。
4. 调整色彩范围选择优先级：
   `DV5 > DV8.1 > HDR Vivid > EDR10 > EDR > ADR > SDR10 > SDR`。
5. 选中码流存在 `metaFile` 且进入普通开播加速时，对 `metaFile` 再调用一次相同
   的调度接口，返回结果放入与 `play` 平级的 `mf_play` 节点。
6. o1 开播场景允许非选中 meta 码流露出 `metaFile`，其他场景清理非选中码流的
   `metaFile`。
7. 本次不实现 `dr` 占比 Prometheus 指标，后续单独开发。
8. 通用过滤器新增 `@exists` 条件，META 码流过滤统一使用字段存在性判断。
9. 将三个新 feature 的过滤逻辑直接内联到 `pre_filter()`，并统一补充 `VIDEODEV-5849` 注释。

## 实现过程

1. 从最新 `origin/master` 创建分支 `fan_5849_multi_color_meta`。
2. 在 `p911/constants/P.lua` 增加 ADR、DV8.1 的 DR 常量。
3. 在 `p911/rules/filter/pre.lua`：
   - 将旧 `ftx2_adr` 使用点改为 `ftx2_adr_type`。
   - 将 `ftx2_adr`、`ftx2_dv81` 和 `ftx2_meta_rate` 拆成互相独立的过滤逻辑。
   - 保留 `metaFile` 作为 DASH 对外字段。
4. 在 `p911/select/video_selection.lua`、`video_selection_2.lua`、
   `video_selection_prio.lua` 和 `rules/video/group_filter.lua` 补齐新 DR 映射与优先级。
5. 在 `p911/dispatch/play_cdn.lua` 增加 meta URL 调度，在
   `p911/rules/video/play.lua` 的普通开播加速路径调用并生成 `mf_play`。
6. 在 `p911/util/response_utils.lua` 控制非选中码流的 `metaFile`：
   普通场景清理，o1 play 场景保留。
7. 增加过滤、优先级、调度返回和响应清理单元测试。
8. 在 `filter_utils` 增加 `@exists` 的 true/false 单元测试，并将 META 过滤改为复用该能力。

## 验证

1. 所有修改的 Lua 文件均通过 `luac -p` 语法检查。
2. META 过滤、DR 优先级、开播加速和响应清理定向测试通过：
   `76 successes / 0 failures / 0 errors`。
3. 合并选择、分组、o1/m3u8 和后处理相关回归后通过：
   `293 successes / 0 failures / 0 errors`。

## 2026-07-27 修改

保留原有 `ftx2_adr` 字段含义不变；本次新增 ADR 码流能力 feature 改名为
`ftx2_adr_rate`，并同步更新过滤逻辑和单元测试。`pre_spec.lua` 定向测试通过：
`46 successes / 0 failures / 0 errors`。

随后确认原有 `ftx2_adr` 字段不改名，已将旧字段引用从 `ftx2_adr_type` 恢复为
`ftx2_adr`；新增 ADR 码流能力仍使用 `ftx2_adr_rate`。
4. `git diff --check` 通过。
5. 未增加 DR Prometheus 指标，未提交，未 push。

## 2026-07-30 修改

1. 使用飞鲨测试接口 `tvId=9000001066430300` 获取 `metaFile`，并将调度请求
   定向到测试环境 `10.128.217.50` 验证。
2. 实测确认 `metaFile` 不需要增加 MP4 QDV3 防盗链签名即可正常调度。
3. 实测确认调度请求需要增加 `rj=1` 才会返回可由 `cjson.decode()` 直接解析的
   JSON；未增加时返回 `var videoUrl=...` 包装格式。
4. 在 `p911/dispatch/play_cdn.lua` 的 metaFile 调度请求中补充 `rj=1`，保留
   `pv=0.1`，调度结果仍写入 `mf_play`。
5. 补充单元测试，校验 metaFile 调度 URL 包含 `pv=0.1&rj=1`。
6. `play_cdn_spec.lua` 和 `play_spec.lua` 定向测试通过：
   `27 successes / 0 failures / 0 errors`。
7. 过滤、选择优先级、响应清理、合并选择、分组、m3u8 和后处理相关回归通过：
   `269 successes / 0 failures / 0 errors`。
8. 修改文件通过 `luac -p` 语法检查，`git diff --check` 通过；未提交、未 push。
9. 将 metaFile 调度请求定向到 `10.128.217.50`，携带
   `mss=1&ssl=1&pv=0.1&rj=1` 实测：接口返回 200 和 3 个候选 CDN 节点，
   所有 URL 均为 HTTPS 且保留 `mss=1&ssl=1`，多机房和 HTTPS 调度生效。
10. 确认 `mf_play` 已明确表示 metaFile 调度结果，无需再按视频格式分类；
    删除中间的 `ts` 节点，200 和 302 调度结果均直接写入 `mf_play`。
11. 移除 `ts` 节点后，`play_cdn_spec.lua` 和 `play_spec.lua` 定向测试通过：
    `27 successes / 0 failures / 0 errors`；相关回归通过：
    `269 successes / 0 failures / 0 errors`。
