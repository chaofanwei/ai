# VIDEODEV-5780 TV 支持屏蔽 4K_sdr10_inter

## 基本信息

- PMS: VIDEODEV-5780
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5780
- 开发分支: fan_5780_block_4k_sdr10_inter
- 修改时间: 2026-05-07 20:29:20 CST
- 代码仓库: /home/fan/lua/projects/luna-rule-2/luna-rule

## 背景

TV 部分设备希望关闭 4K SDR 中码率露出。

已有 feature `ft5_tv_4k_inter_sdr` 关闭后，只会影响 4K SDR 8bit 中码率，也就是 `bid=800, br=200, dr=-1`。

但 4K SDR10bit 中码率没有被关闭，也就是 `bid=800, br=200, dr=7` 仍会露出。

## 期望

扩大 `ft5_tv_4k_inter_sdr` 的控制范围，使其在 TV 场景下同时控制：

- 4K SDR 8bit 中码率: `bid=800, br=200, dr=-1`
- 4K SDR10bit 中码率: `bid=800, br=200, dr=7`

## 改动

### 过滤逻辑

文件:

- `vis-rule-engine/src/main/lua/p911/rules/filter/pre.lua`

改动点:

- 在 `request._is_mainland_tv_or_tv_touping` 场景下，`request.ft5_tv_4k_inter_sdr ~= true` 时，过滤条件从单个 4K SDR 8bit 中码率扩大为两个条件：
  - `{ bid = P.VIDEO_BID_4K, br = P.VIDEO_BR_INTER, dr = P.VIDEO_DR_SDR }`
  - `{ bid = P.VIDEO_BID_4K, br = P.VIDEO_BR_INTER, dr = P.VIDEO_DR_SDR10 }`

### 单测

文件:

- `vis-rule-engine/src/main/lua/spec/p911/rules/filter/pre_spec.lua`

新增 TV 场景回归用例：

- `ft5_tv_4k_inter_sdr=false` 时，4K SDR 8bit inter 和 4K SDR10bit inter 都不露出。
- `ft5_tv_4k_inter_sdr=true` 时，4K SDR 8bit inter 和 4K SDR10bit inter 都保留露出。

## 验证

已执行：

- `luac -p vis-rule-engine/src/main/lua/p911/rules/filter/pre.lua`
- `luac -p vis-rule-engine/src/main/lua/spec/p911/rules/filter/pre_spec.lua`
- `git diff --check`

结果:

- Lua 语法检查通过。
- diff 空白检查通过。

未执行:

- `busted spec/p911/rules/filter/pre_spec.lua`

原因:

- 当前机器未安装 `busted`，命令返回 `busted: command not found`。

## 后续再次修改建议

如果后续需要继续扩大该 feature 的控制范围，优先在 `pre.lua` 的同一处 TV feature 过滤逻辑中追加明确的 `bid/br/dr` 条件，并同步补充 `pre_spec.lua` 中 TV 开关开启/关闭两类用例。

## 本需求的codex session

019e025a-815b-7a40-a28d-60a68b442721
