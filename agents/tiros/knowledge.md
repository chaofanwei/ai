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
- 例（2026-08-11 主站 bid=600）：tvid=8745713428414000；线上选中 `ff=dash` 同 vid 有 `play.av1`，预发选中 `ff=ts`（不同 vid），对齐后同 vid 预发 `_selected=false` 无 `play`；retryNum=10 稳定差异。

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

## DashStable 金丝雀业务对比（2026-10-12）

- envId=16 的业务告警存于 `business_result`，查询字段为 `envId` + `ruleName`，正文为 `proResponse` / `preResponse`。不要套用技术对比的集合、字段名。
- 本次实时配置：env1=`10.128.117.17`，env2=`10.72.12.116`，两侧响应 `data.ctl.from=stable`。`DashStable与Dash同码流返回不一致` 是 `StableVideoCompareService` 的固定文案，不能凭名称推断两个服务的实际部署类型。
- 该规则按 `bid+vid` 对齐，调用自己的字段 equality；不调用 `JsonCompareUtil`，不读取环境的 `ignore` / `uri_fields_rule`。选中流的排除表含 m3u8/ml/mk/play/mp4Url/fs/drm，但不含 `url`、`muhp`。即使技术对比 URI 配置包含这两项，业务规则仍完整比较 query。
- reset=269（2026-10-10 16:54:20）后，本次查询共10条该告警，均 tag=0/retryNum=10：6条仅 `muhp` query 的 `bs` 不同（其中1条涉及两个vid）；3条仅 `url` query 的 `qd_time/vf` 不同；1条历史选流不同。前9条对应 URI 的 scheme/host/path 一致，未发现该规则覆盖范围内的其他差异。地址 query 差异不能直接等同于 VP 码流元数据差异，也未据此验证播放内容或可用性。
- 历史选流样本 tvid=`3612654168735700`：两边均有同样的12条流，env1选 `8cc7a70add61f5d5d82ef92fd1327664`（rp/slt/sut=1），env2选 `db6cbe0ace82f597ddb3e3c1ad1aafca`（rp/slt/sut=0），均 bid=600/ff=265ts。伴随 `_selected` 值差异及选中流 ps/unencryptedDuration/p2p/tag/scrsz 节点有无差异。2026-10-12重签复查，两侧各连续5次均选择后一个vid，该字段比较阶段已一致；历史触发选流分歧的服务内部原因未确认。
- 业务重试仅更新 retryNum/tag，不更新原响应或 reason；达到10次后停止。因此“retryNum=10、tag=0”只说明重试窗口内未判相等，不能单独证明当前仍有原来的差异，也不能证明10次均由同一字段触发。
- `reason` 中 `tvid=null` 是代码从 video 子对象取 tvid，而该层无此字段；排查应取记录顶层 tvid 或请求参数。
- 本次证据汇总：`temp/dashstable-analysis-20261012.md`；结构化脱敏差异：`temp/stable-summary.json`。
- 后续用户明确要求排除 `muhp` / `url`：已在本地新分支 `fix/dashstable-ignore-url-muhp` 修改 `StableVideoCompareService.compare`，无论码流是否选中均排除这两个完整字段（包括其有无差异），其它规则保持原逻辑。Maven离线编译通过；以实际编译后的 `check4KStreamConsistency` 回归上述10条原始记录，9条地址类通过该阶段，1条选流类仍报差异。本次仅本地修改，尚未提交、推送或部署；以上排查中的旧行为描述对应修改前/线上逻辑。
- 用户随后授权 commit & push：上述修改已提交为 `e7fd6be`，推送至 `origin/fix/dashstable-ignore-url-muhp`；提交仅包含比较器文件，原有其它未提交改动保留。尚未部署。
- 用户进一步纠正排除范围：`muhp` / `url` 应放入 `if (isSelected)`。最终以 `2969734` 为准，已推送同一分支，仅按现有逻辑中 dashRate 的 `_selected=true` 排除；未选中流继续比较这两个字段。重新编译通过，10条样本中6条选中流地址差异通过该阶段，3条未选中流muhp差异和1条选流差异仍检出。
- 手动接口返回值陷阱（后端源码确认）：`dial_by_content` / `dial_by_id` / `dial_by_case` 同步返回 `DashEnvOperation.compare` 的 `DialCompareResult`，不是异步 `StableVideoCompareService` 的业务结论。该 compare 仅对 envId=1/7/4 执行 code/st/JSON 比较；envId=16 正常取得并解析响应后走 else 直接 EQUAL。因此不能以手动接口的 EQUAL 验证金丝雀业务规则修复。`dial_by_content` 经 `dialByMessage` 将tag设为 `dial_by_message_id`，还会跳过业务队列；其他入口是否入队取决于tag，仍不会将业务结果同步返回。此次未成功抓到前端按钮请求，按钮具体接口以浏览器network为准。
- 后续已读取线上页面 `/static/js/dash/dial.js`：`open()` 在 `fromType==='2'`（产品）时调用 `dialAjax(null, message)`，技术模式传uuid；两者统一POST `/dash/dial/dial`，仅传envId及id/content，成功后直接 `handleDetail(res.data.data)`。该页面没有独立产品重比调用。后台 `doBusinessDiffTask` 每10秒取当前周期内tag=0且retryNum<10的记录重放入业务队列；满10次记录不再重试。页面“重置diff”是归档/开启新统计周期及下线规则，不是重新产品对比。
- 用户告知2969734上线后，2026-10-12 16:08左右重签重放原10条；两侧均A00000/st=101。同码流阶段7条通过，剩3条为未选中流muhp.bs（tvid=5259500653068900/2451118021649300/8367091146911600）。本机执行完整StableVideoCompareService.compare时，另外7条因getSelectedRate访问10.61.233.252/test返回403而落入“选中码流信息不一致”，不可将该阶段通过当完整产品通过，也不可把本机403未经核实推断为线上同因。线上15:59:29有tvid=2492397200同名告警，服务端具体原因未确认。原10条记录仍tag=0/retryNum=10，未修改。详见temp/dashstable-after-deploy-20261012.md。
- **10.61.233.252 403 与 tiros 拼 URL（2026-10-12，不改 qasign）**：qasign 仅放行 `/test/dash|/test/live|…`，`/test?url=` 为 403。`getSelectedRate` 应请求 **`/test/dash?{dash query}`**；`modifyUrl` 需支持 access 日志相对路径 `/dash?…`。已随 `fix/dashstable-ignore-url-muhp` 提交 `f81755b` 并上线；vf 签名 HTTP 200，但 `httpGet(finalUrl)` 仍对相对 `/dash?` 无 Host（`null/dash`）会失败，落入「选中码流信息不一致」（与「同码流」页不同 rule）。
- **envId=16「同码流」页（2026-10-12）**：`37e94bd` 未选中也排除 `muhp` 上线后，用当日重放响应+最新比较器复核 **同码流 10/10 通过**，无再触发 `DashStable与Dash同码流返回不一致`。Mongo 该 rule 仍 **10 条** `tag=0/retryNum=10`（最后 update **12:05**，重试耗尽不回写）；星图列表需重置/打标才清。完整 `compare` 仍可能落 **选中码流信息不一致**（`getSelectedRate` 相对 `/dash?` 无 Host 等），与本页 rule 无关。
- **envId=16「选中码流信息不一致」**：仅注释 `checkSelectedStreamConsistency` 内复现调用；`080c323` 的 Kakashi/env1/headers 复现已撤销（入口关闭无需注入）。`getSelectedRate` 等仍保留备查、当前不执行。
- **envId=20 Dash-VS-DashStable-国际站（2026-10-12）**：代码 `DialEnv.DASH_VS_DASHSTABLE_INTL`，链路与 12/16 相同（`stableVideoCompareService` + `nginx_cache_access` 独立游标）。库表 `tiros_dial_env_pair.id=20`：host 白/黑同 env7；env1=`10.194.160.226`（对齐 12 用预发 dash）、env2=`10.72.12.116`（同 12 dashstable）；**默认 status=2 未启用**。`DashEnvOperation` 对 stable 环境用 `isDashStableEnv` 判断 tvid 尾 17 不入队。
