# tiros 拨测对比知识点（自动沉淀）

> 经用户确认或反复验证的结论写这里。详细手册见 `./tiros/tiros-dial/Readme-diff-check.md`。

## 对比语义

- `simpleUnequalKey` 的 `[X]` = 按 vid 排序后的下标泛化，不是原始顺序。
- `ignore`：**两边节点都必须存在**才忽略内容；一侧缺失必报。
- 浅对比：两边都是对象时按 depth 比结构；一侧 null 仍不等。
- `vt=4`：代码层只比 code/st（部署后生效），避免选流噪声。

## 选流相关字段

- `_selected=true`：当前选中可直接播放的码流；两边 true 落在不同 vid → 一串连带差异。
- `ft`：几乎只在选中流；每边通常 1 条。
- `etid`：选中流常缺失；未选中流常有。
- `play`：多在选中流；也可能同 vid 一边有一边无（人工处理，勿代码吞）。
- 例（2026-08）：bid=800 时线上选 `ff=dash`、预发选 `ff=ts` → 报 `_selected`。
- 例（2026-08 主站）：`JSON.data.program.video[X].play` 当前样本是 `vt=` 空、`bid=860`；线上同 vid 选中 `ff=265ts` 且有 `play.ts`，预发同 vid 未选中且无 `play`，预发改选另一条 `ff=fmp4`，本质是选流不同导致的节点缺失。

## VP vs Dash

- VP `/cache` 可区分底数问题：预发 `10.72.11.143` + Host `fshark.video.qiyi.smart`；线上 `vp-bdxs.qsm.qiyi.middle` + 同名 Host。
- `content.croIds` 案例：线上 VP=`[154590]`、预发 VP 缺失 → dash 差异同源自 VP。

## 运维标记

- tag：0 未处理 / 1 重试后一致 / 2 符合预期 / 3 不符合预期
- UI 符合预期看 MySQL `tiros_meet_expectation`，不只 Mongo tag。
- 重试满 `retryNum=10` 仍 tag=0 → 稳定差异。

## 配置备忘（以库为准）

- 主站 id=1 / 国际站 id=7 ignore 曾补：`ms`、`play(\.\S+)?`、`nsdl\.timestamp`
- 裸 `play` 旧正则 `play.\S+` 匹配失败，已改为可选后缀。
