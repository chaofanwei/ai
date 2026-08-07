# VIDEODEV-5870 Pad端支持爱奇艺音效

- PMS标题：Pad端支持爱奇艺音效
- PMS链接：http://pms.qiyi.domain/browse/VIDEODEV-5870
- 修改时间：2026-07-17 11:03:21 CST
- Codex session Id：019f6e00-52c9-7703-a93d-55c51f9706eb

## 背景

iPad 端 `src=03032001010000000000` 从 `17.7.5` 版本开始需要支持爱奇艺音效会员权益渲染，整体对标现有移动 phone 端：

- `request.src == "02032001010000000000"`
- `request.src == "02022001010000000000"`

差异点：iPad 本需求不支持试听。

## 改动

1. 在 `p911/rules/pre/property.lua` 的爱奇艺音效能力标记逻辑中，新增 iPad 端版本判断：
   - `request.src == P.PTID_IPAD_IQIYI`
   - `request.k_ver >= "17.7.5"`
2. 命中版本门槛后设置：
   - `request._mobile_iqiyi_audio_right = true`
   - `request._mobile_iqiyi_audio_trail = false`
3. 在 `p911/constants/P.lua` 新增 iPad src 常量 `P.PTID_IPAD_IQIYI = "03032001010000000000"`，业务判断处通过常量引用。
4. 在新增 iPad 判断处补充 `pms 5870` 注释。
5. 复用现有移动端爱奇艺音效权益渲染链路：
   - `vip/dash_ctl.lua` 根据 `_mobile_iqiyi_audio_right` 渲染 `ctl.aoe` 和音轨会员权益信息。
   - `select/audio_selection.lua` 根据 `_mobile_iqiyi_audio_trail=false` 避免起播选择试听音轨。

## 实现过程

1. 按需求从最新 `master` 创建分支 `fan_5870_pad_iqiyi_audio`。
2. 阅读现有 phone 端爱奇艺音效实现，确认能力标记在 `pre.property.lua`，权益渲染在 `vip/dash_ctl.lua`，不支持试听的选流保护在 `select/audio_selection.lua`。
3. 采用最小改动，只在能力标记处新增 iPad 版本门槛和试听关闭标记，不改后续通用处理逻辑。
4. 按二次要求将 iPad src 提取到 `P.lua` 常量，并在修改代码处补充 PMS 注释。

## 验证

1. `luac -p vis-rule-engine/src/main/lua/p911/rules/pre/property.lua` 通过。
2. `luac -p vis-rule-engine/src/main/lua/p911/constants/P.lua` 通过。
3. 已检查源仓库 diff，仅新增 iPad src 常量和 `k_ver >= 17.7.5` 的能力标记逻辑。
4. 未运行全量 Maven 测试：本次改动只涉及 Lua 能力标记，仓库未提供更精确的 `pre.property.lua` spec 入口。
