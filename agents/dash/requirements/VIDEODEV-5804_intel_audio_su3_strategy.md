# VIDEODEV-5804 海外站-多音轨合并：支持起播策略及未更新音轨信息

- PMS链接：http://pms.qiyi.domain/browse/VIDEODEV-5804
- 修改时间：2026-05-29 13:51:29 CST
- Codex session Id：019e723f-56ea-75a0-8738-3092c402c5d0
- 开发分支：fan_5804_intel_audio_su3_strategy

## 背景

海外站多音轨选择需要新增起播策略。请求参数 `su=3` 时，音轨选择顺序要求为：

1. 用户切换记录
2. 原声
3. APP语言（界面语言）
4. 月神配置

## 改动

- 修改 `vis-rule-engine/src/main/lua/p911/select/intel_audio_selection.lua`。
- 在国际站音轨选择 `select_audio_by_prio` 中新增 `su=3` 的明确分支。
- `su=3` 分支依次使用已有选择函数：
  - `select_audio_by_prio_lid`
  - `select_audio_by_prio_ori`
  - `select_audio_by_prio_applang`
  - `select_audio_by_prio_conf`
- 保持原有 `su` 空/0、`su=1`、`su=2` 及其他值逻辑不变。

## 验证

- 已执行 `luac -p vis-rule-engine/src/main/lua/p911/select/intel_audio_selection.lua`，语法检查通过。
- 已确认源码 diff 仅包含 `su=3` 分支新增逻辑。
