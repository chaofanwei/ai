# 月神运维记录

## 2026-10-21 / 默认权限增加「功能申请」/configApply

- 需求：所有登录用户默认可访问 `/configApply`（Privilege 组 **55**，页面「功能申请」），无需单独申请。
- 实现（方案 A，源码）：`Constants.DEFAULT_PRIVILEGE_GROUP_3=55`，统一列表 `DEFAULT_PRIVILEGE_GROUPS`（20/21/55）；登录菜单、`UserService` API 缓存、权限回填与申请/管理员改权时的剔除逻辑均使用该列表。
- 分支：`luna-platform` → **`default-privilege-config-apply`**，commit `9cbd98205`（已 push origin）。
- 上线后：用户需**重新登录**刷新 `menuItems`；库表 `Privilege` 中组 55 记录保持不变，无需改库。
- 备注：线上组 55 菜单 `httpUrl` 仍为 `/luna/config/listAll`，实际接口为 `/luna/configure/*`；Session 接口校验目前有兼容放行，若以后收紧拦截可单独 UPDATE `httpUrl`。

## 2026-10-20 / 中断 PTID 工单释放验重（239040 / 239041）

- 现象：云工单 239040、239041（申请人 `mengya`，芒果小程序 adr/iOS）中断后重新申请仍提示 PTID 已存在。
- 原因：`sailor_moon_ptid_apply_info` 两行仍为 `status=1`（审批中），`ptid` 占号；未入 `sailor_moon_ptid_all` / src-key。
- 处理：用户确认后，将 id **1459**（`02028911010000000000`）、**1460**（`02038911010000000000`）的 `ptid` 改为 **`{原ptid}.bak`**，并刷新 `update_time`；事务影响 2 行。
- 备份：`temp/backup_ptid_239040_239041_20261020.tsv`；脚本：`temp/update_ptid_bak_239040_239041_20261020.sql`；回滚：`temp/rollback_ptid_bak_239040_239041_20261020.sql`（未执行）。
- 验重逻辑：`uniquePtid` 仅当 `sailor_moon_ptid_apply_info` 中同 ptid 为中断/驳回/删除或 `sailor_moon_ptid_all` 无记录时可通过；改后缀等价于释放原 20 位 ptid。

## 2026-10-16 / 测试库 cloud_octopus 初始化 vip_or_tvod_videos

- 用户确认后，经跳板机 `ssh -p 443 root@10.63.5.53` 在 **`cloud_octopus`**（`bj.cloudoctopus.w.qiyi.db:1935`）执行，语义同 `vip_or_tvod_videos_20261014.sql`。
- 分配 **`task_model_id=63`**（测试原最大 62 为 `o1_configs`）。从测试 `ip_experience_card_white_list`（task_model_id=60，`group_id=NULL`）继承 `is_auto/is_approval/is_send_message/template_code/push_*`；`is_approval=0`。
- 结果：`task_config_key=vip_or_tvod_videos`，`task_model_url=/etcd/vip_or_tvod_videos`，`group_id=NULL`，`task_conf_min_size=2`，`task_conf_max_size=1048576`，`update_time=2026-10-16 14:57:12`；INSERT 影响 1 行。
- 容量：`sailor_moon_config_center.config_value` 仍为 **TEXT**；`sailor_moon_data_change_record` 的 `old_content/new_content` 为 **LONGTEXT**（与线上一致，大名单需注意 TEXT 上限）。
- 脚本：`temp/execute_vip_or_tvod_videos_test_20261016.sql`；回滚：`temp/rollback_vip_or_tvod_videos_test_20261016.sql`（未执行）。
- 任务配置内存缓存约 10 分钟；若 Open API 仍报「未获取到任务发布配置」/A00005，需等待刷新或重启测试实例。未预插 `sailor_moon_config_center` 行；发布端登记、Token 授权仍按 `docs/vip_or_tvod_videos.md` 另行完成。

## 2026-10-14 / 初始化 vip_or_tvod_videos etcd 任务配置

- 用户确认后，经跳板机 `ssh -p 443 root@10.63.5.53` 执行 `videocloud_luna` 库脚本（同 `vip_or_tvod_videos_20261014.sql` 语义）。
- 分配 ID：`task_model_id=62`（线上最大 61 为 `o1_configs`）。INSERT 时脚本要求 `@tvod_group_id>0` 曾暂用 `group_id=11`；用户确认后与 IP 体验卡对齐，已 `UPDATE` 为 **`group_id=NULL`**（影响 1 行，与 task_model_id=59 一致）。
- 从 `ip_experience_card_white_list`（task_model_id=59，线上 `group_id` 为 NULL）继承 `is_auto/is_approval/is_send_message/template_code/push_*`；INSERT 影响 1 行。
- 结果：`vip_or_tvod_videos`，**`task_model_url=/etcd/vip_or_tvod_videos`**（与 IP 体验卡 `/etcd/{config_key}` 形式一致；曾短暂为 `/Config_center_manage`），`is_online=1`，`task_conf_min_size=2`，`task_conf_max_size=1048576`，**`group_id=NULL`**；`update_time` 已刷为操作时刻。
- 容量核对：`sailor_moon_config_center.config_value` 为 **TEXT**（约 64KB）；变更记录表 `old_content/new_content` 为 LONGTEXT。文档预期单配置 JSON 约 175KB，若接近上限需另行安排 `config_value` 扩容。
- 执行文件：`temp/execute_vip_or_tvod_videos_20261014.sql`；`group_id` 修正：`temp/update_vip_or_tvod_group_null_20261014.sql`；url/时间：`temp/update_vip_or_tvod_url_time_20261014.sql`；回滚：`temp/rollback_vip_or_tvod_videos_20261014.sql`（未执行）。
- 操作前 `git pull --ff-only`：Already up to date。脚本未含 Token 授权、发布端登记，需按 `docs/vip_or_tvod_videos.md` 后续步骤完成。

## 2026-10-13 / 撤销 tianjun 超级管理员权限

- 用户另行确认撤销超级管理员计划后，将 UserPrivilege 记录 1802（user_id=338，privilege_group=1，work_order_id=238297）的 status 从 2 改为 -1，update_time 为 `2026-10-13 13:47:14`。
- 事务精确影响 1 行，超级管理员有效授权剩余 0；新连接复查其余记录未变，先前撤销的组 24 仍为 -1。
- 备份：`temp/backup_tianjun_1802_20261013.tsv`；回滚：`temp/rollback_tianjun_1802_20261013.sql`（未执行）。沿用本次会话 git pull --ff-only 的最新结果，未修改源码。
- 数据库撤权已完成，未清理现有登录会话；菜单需要退出后重新登录刷新。前述接口兼容放行及工单再次回调的限制仍适用。

## 2026-10-13 / 撤销 tianjun 防盗链页面直接授权

- 用户确认计划后直接改表：用户 `tianjun`（ID 338），权限组 24，对应「防盗链库配置 / PTID_防盗链配置」，工单 238297，UserPrivilege 记录 1800。
- 按 `PrivilegeService.editUserPrivilege` 的软删除语义，将 status 从 2 改为 -1，update_time 为 `2026-10-13 13:45:09`。事务影响 1 行；新连接复查组 24 有效直接授权为 0，其余记录不变。
- 备份：`temp/backup_tianjun_1800_20261013.tsv`；回滚：`temp/rollback_tianjun_1800_20261013.sql`（未执行）。操作前 git pull --ff-only 已确认最新，未修改源码。
- 此次仅撤销目标直接授权。用户仍有组 1 超级管理员授权（记录 1802，工单同为 238297，status=2），按源码仍可访问这两个页面，需另行确认更大撤权范围。
- 源码中菜单缓存在登录会话；SecurityInterceptor 对会话用户的接口权限未命中仍兼容放行，因此不能把直接授权撤销等同于接口访问已被阻断。未代替用户登录验证。
- 工单回调会按 work_order_id 更新全部关联记录状态（不排除软删除），若工单发生再次回调，需要复核撤权记录。

## 2026-10-13 / 删除废弃推荐短剧业务配置

- 用户确认删除 16 个 PTID 字面量前缀下全部 src 映射（包含版本后缀），表 `videocloud_luna.sailor_moon_src_key_online`。
- 前缀：`02023405040000000000`、`02023425040000000000`、`02023415040000000000`、`02025605040000000000`、`02023435040000000000`、`02023445040000000000`、`02023455040000000000`、`02023465040000000000`、`02023495040000000000`、`02023485040000000000`、`02023475040000000000`、`02023605040000000000`、`02023635040000000000`、`02023895040000000000`、`02023905040000000000`、`02023915040000000000`。
- 共 33 条；测试业务 `02025605040000000000` 3 条，其余各 2 条；业务名称与最晚更新时间（北京时间，按秒）均与用户清单一致。
- 回滚文件：`temp/rollback_20261013_drama.sql`；校验 33 条 INSERT、ID 不重复、16 组数量一致，无 DROP、CREATE、TRUNCATE、DELETE、UPDATE。
- SHA-256：`0ca023e4c6134c91d95eb49487b847499d933ed3521f9cf4482507d40c767aee`。
- 事务锁定 33 条，逐组数量和记录 ID/updatets 校验后删除 33 条，提交前后剩余 0；独立新连接复查 16 个前缀均为 0。
- 沿用本次会话 `git pull --ff-only` 结果（Already up to date），未修改源码。

## 2026-10-13 / 删除商城及爱金果微信小程序废弃配置

- 用户确认按六个 PTID 字面量前缀删除全部配置，包含版本后缀；表 `videocloud_luna.sailor_moon_src_key_online`。
- 数量：`02022131010000000000` 1 条、`02032131010000000000` 1 条、`02027091010000000000` 3 条、`02037091010000000000` 1 条、`02028061010000000000` 1 条、`02038061010000000000` 1 条，总共 8 条。
- 最晚更新时间（北京时间，按秒）与用户清单一致；App 外 Android 前缀包含两条旧名称“商城 Android Phone H5”的 TMTS 记录，同范围删除。
- 回滚文件：`temp/rollback_20261013_six_prefixes.sql`；校验为 8 条 INSERT，各组数量一致，无 DROP、CREATE、TRUNCATE、DELETE、UPDATE。
- SHA-256：`33c2cbb78492f10974989588bf957b34c19157f61433fa96332fffd0de563acf`。
- 事务锁定 8 条，逐组校验数量后删除 8 条，提交前后剩余 0；新连接逐组复查六个前缀均为 0。
- 沿用本次会话 `git pull --ff-only` 结果（Already up to date），未修改源码。

## 2026-10-13 / 删除 OSX 操作系统标志码错误的 PTID

- 用户确认删除 `01030031010000000000` 前缀下全部 src 映射（含版本后缀）。表：`videocloud_luna.sailor_moon_src_key_online`。
- 最终条件：`BINARY LEFT(src, CHAR_LENGTH('01030031010000000000')) = '01030031010000000000'`。
- 查询命中 2 条：ID 13（TMTS）、159（VPS），名称均为 `QiYi OSX Mac H5 （操作系统标志码错误）`；没有版本后缀记录。
- 回滚文件：`temp/rollback_20261013_osx.sql`；校验为 2 条 INSERT，无 DROP、CREATE、TRUNCATE、DELETE、UPDATE。
- SHA-256：`91a267b76617c542bbe21162e12aaa93a66ac6c00bb9984374d780699b6335cc`。
- 事务锁定 2 条、删除 2 条，提交前后剩余 0；新连接复查前缀下总数为 0。
- 沿用本次会话 `git pull --ff-only` 结果（Already up to date），未修改源码。

## 2026-10-13 / 删除双下划线错误 src

- 用户确认按 `delete_useless_src_key` 流程删除；表 `videocloud_luna.sailor_moon_src_key_online`，条件 `BINARY src = '05025033421000000000__v1qh'`。
- 查询命中 1 条：ID 4126，DASH，QiYi Android TV 易视腾湖南移动IPTV。
- 回滚文件：`temp/rollback_20261013_double_underscore.sql`，校验为 1 条 INSERT，无 DROP、CREATE、TRUNCATE、DELETE、UPDATE。
- SHA-256：`1c147b2d9a1dbe5260d3c94dbcc8d0f4fd76289c711aebbd36e9327a032019b3`。
- 事务锁定 1 条、删除 1 条，提交前后剩余 0；新连接复查错误 src 为 0，正常单下划线 `05025033421000000000_v1qh`（ID 4129）仍在。
- 首次尝试因旧版 MySQL 不支持 SELECT 常量直接接 WHERE，在 DELETE 前中止；改用 `SELECT 1 FROM DUAL WHERE ...` 后成功。
- 操作前 `git pull --ff-only`：Already up to date；未修改源码。

## 2026-09-29 / 1080P 免费节目延期

- 用户确认直接改表：`sailor_moon_config_task` 的任务 `273`，节目 `2119021357785123`，工单 `236094`，配置 `1080p_free_tvids`。
- 将 `end_time` 从 `2026-09-30 00:00:00` 改为 `2026-10-02 00:00:00`；事务内限定任务身份、原结束时间及状态 2，影响 1 行，新连接复查一致；配置中仍包含该节目。
- 修改前备份：`temp/backup_task_273_20260929.txt`；回滚 SQL：`temp/rollback_task_273_20260929.sql`（未执行）。
- 已告知用户：当前源码 `ConfigInfoJob` 到期清理仅周一至周四 10:15 执行，故本次预计 10 月 5 日 10:15 执行移除，实际以任务和发布成功为准。
- 操作前 `git pull --ff-only`：Already up to date；未修改源码。

## 2026-08-19 / src-key 映射下线

- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除条件及数量：
  - `src LIKE '02033161010011%'`：106 条
  - `src LIKE '02117011010011%'`：106 条
  - `src LIKE '11025134350000000000%'`：2 条
  - `src LIKE '11025134710000000000%'`：2 条
- 删除总数：216 条
- 回滚文件：`temp/rollback_20260819_src_prefixes.sql`
- 回滚文件大小：68,638 字节
- 回滚文件 SHA-256：`f5d50fc4c6b4ac55121a3d0263ebbe525c1262eb4187a95a3fadf686107f01f0`
- 事务结果：锁定 216 条，删除 216 条，提交前剩余 0 条。
- 独立复查：四个前缀均为 0 条。
- 代码状态：操作前执行 `git pull --ff-only`，结果为 Already up to date；未修改月神源码。
- 临时文件：跳板机 `/tmp` 中的备份已删除，本地回滚文件保留。

## 2026-08-25 / src-key 映射下线

- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除条件及数量：
  - `src LIKE '04023161010011%'`：136 条
  - `src LIKE '04004011010011%'`：68 条
  - `src LIKE '04025042931000000000%'`：3 条
  - `src LIKE '04025032051000000000%'`：8 条
- 删除总数：215 条
- 回滚文件：`temp/rollback_20260825_delete_useless_src_key.sql`
- 回滚文件大小：71,404 字节
- 回滚文件 SHA-256：`00508e06c895c302ced4e7d722790eb7347e60a9bf9cea68dc57f8de467343ff`
- 备份校验：215 条 `INSERT`，四组数量与删除前线上查询一致，未包含 `DROP`、`CREATE`、`TRUNCATE`、`DELETE` 或 `UPDATE`。
- 事务结果：锁定 215 条，删除 215 条，提交前剩余 0 条。
- 独立复查：四个前缀及总数均为 0 条。
- 代码状态：操作前执行 `git pull --ff-only`，结果为 Already up to date；未修改月神源码。

## 2026-09-15 / 删除以下划线结尾的错误 src 配置

- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除条件：`RIGHT(src, 1) = '_'`（匹配字面量下划线，避免 SQL `LIKE` 中 `_` 通配符的歧义）
- 删除前结果：共 20 条、20 个不同 `src`，用户提供的 20 个 PTID 各 1 条；未发现清单之外的其他下划线结尾配置。
- 回滚文件：`temp/rollback_20260915_trailing_underscore_src.sql`
- 回滚文件大小：6,554 字节
- 回滚文件 SHA-256：`0afc3f4dc62742e40504611aec8feda6a984a1c41bea82b10949fc0ac59aa82b`
- 备份校验：20 条 `INSERT`，20 个目标各 1 条，未包含 `DROP`、`CREATE`、`TRUNCATE`、`DELETE` 或 `UPDATE`。
- 事务结果：锁定 20 条，删除 20 条，提交前剩余 0 条，提交后同连接检查剩余 0 条。
- 独立复查：使用新数据库连接查询，所有以下划线结尾的 `src` 总数为 0；用户提供的 20 个 PTID 均为 0。
- 代码状态：操作前执行 `git pull --ff-only`，结果为 Already up to date；未修改月神源码。

## 2026-09-15 / 删除 PTID 与名称写反的 src 配置

- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除条件：`src` 精确等于 `QiYi Android TV 甘小果` 或 `QiYi Android TV 南传-广东移动IPTV`。
- 删除前结果：共 2 条，每个错误 `src` 各 1 条；对应 `name` 分别为正确 PTID `05025022931000000000_v1pi`、`05025133761000000000_v1r4`，确认属于 PTID 与名称写反。
- 回滚文件：`temp/rollback_20260915_swapped_ptid_name.sql`
- 回滚文件大小：2,060 字节
- 回滚文件 SHA-256：`9125ea6c1d30bd81b7140b1ad06118a79d2438116c74949ddcfcebb645aee58d`
- 备份校验：2 条 `INSERT`，两条目标记录及其正确 PTID 均完整，未包含 `DROP`、`CREATE`、`TRUNCATE`、`DELETE` 或 `UPDATE`。
- 事务结果：锁定 2 条，删除 2 条，提交前剩余 0 条，提交后同连接检查剩余 0 条。
- 独立复查：使用新数据库连接查询，两个错误 `src` 均为 0。
- 代码状态：本次操作沿用本次会话开始时的 `git pull --ff-only` 结果（Already up to date）；未修改月神源码。

## 2026-09-15 / 删除历史废弃 APP 的 src 配置

- 表：`videocloud_luna.sailor_moon_src_key_online`
- 删除范围：用户指定的 19 个 PTID 字面量前缀下的全部 `src`；使用 `LEFT(src, CHAR_LENGTH(prefix)) = prefix` 语义匹配，`2_22_225` 和 `2_22_226` 中的下划线按普通字符处理。
- 删除前结果：共 34 条、34 个不同记录，不同前缀间无重复命中。
- 各前缀数量：`02033001010000000000` 6 条，`d6bde8e122994226990c974238397364` 3 条，`2_22_226` 2 条，`2_22_225` 2 条，`02022261010000000000` 3 条，`02032261010000000000` 3 条，`02023851010000000000` 2 条，`02023881010000000000` 2 条，其余 11 个前缀各 1 条。
- APP 名称核对：主体名称与需求一致；同一废弃 PTID 下存在历史名称变体，包括“啪啪奇 IOS Phone”“吃鲸 IOS Phone”“爱奇艺app-好片快看”，按用户确认的 PTID 前缀范围一并删除。
- 回滚文件：`temp/rollback_20260915_deprecated_app_prefixes.sql`
- 回滚文件大小：11,800 字节
- 回滚文件 SHA-256：`e60d384a865bec573e36cd27042a18e63825f2fef5f51768164be696a2cecbe7`
- 备份校验：34 条 `INSERT`，19 个前缀的记录数逐项与线上删除前查询一致，未包含 `DROP`、`CREATE`、`TRUNCATE`、`DELETE` 或 `UPDATE`。
- 事务结果：锁定 34 条，删除 34 条，提交前剩余 0 条，提交后同连接检查剩余 0 条。
- 独立复查：使用新数据库连接逐项查询，19 个 PTID 前缀均为 0，总数为 0。
- 代码状态：本次操作沿用本次会话开始时的 `git pull --ff-only` 结果（Already up to date）；未修改月神源码。

## 2026-09-17 / 用户权限树「码流选择策略」勾选显示与生效

- 现象：给用户（如 `jinyan`）勾选「页面（读权限）：码流选择策略管理 / 码流选择策略2.1管理」保存后，在「点击查看」里该节点常显示未勾选，误以为未生效。
- 线上核实（`UserPrivilege`）：`jinyan` 已有 `privilege_group=33`、`status=2`（审批完成），`update_time=2026-09-17 10:14:01`；另有历史组 `22`（PTID 相关）。
- 组 33 在 `Privilege` 表中对应多条**页面**（`type=1`）：点播模块下「码流选择策略管理」「码流选择策略2.1管理」等（`parentId=14`），直播模块下「预推节目列表」（`parentId=16`）。读权限按 **privilege_group 整组** 生效，不能只开其中一个页面。
- 根因（前端展示）：`User.vue` 权限树 `node-key="value"` 使用 `privilegeGroup`；同一 group（如 33）在不同模块下会出现**多个树节点、相同 value**。Element UI `el-tree` 对重复 key 回填不稳定，常见表现是「预推节目列表」显示已勾选而「码流选择策略」显示未勾选，但库中组 33 已存在。
- 使用侧：被授权用户需**重新登录**（或刷新会话，`/api/tologin` 重载 `menuItems`）后，导航才会出现 `/Video_selection_plan`、`/Video_selection_plan_pro`。
- 长期修复需研发：拆分线上重复的 `privilegeGroup`（至少将组 33 在点播/直播下的页面拆组），或改为唯一 `node-key`；属源码/数据问题，运维不改 `luna-platform` 代码。

## 2026-09-17 / 改权限后仍提示无权限（会话未刷新）

- 现象：库表 `UserPrivilege` 已有新 `privilege_group`（如 jinyan 的组 33），但用户仍进入 `/guide`「没有当前页面的权限」。
- 根因：`/api/tologin`（`IndexController.currentUserName`）**只返回 HttpSession 里已有的 `loginUser`**，不会按库表重建菜单；`CASAUthenticationFilter` 也仅在 `session.loginUser == null` 时调用 `loadCurrentUser`。
- 结果：管理员在用户**已登录期间**改权限，目标用户若不重新走 CAS 登录，前端 `menuItems`/动态路由仍是旧数据；localStorage 里的 `menuItems` 也会一起旧。
- 处理：让用户 **右上角退出登录 → 重新 CAS 登录**；仍不行则清 `luna.qiyi.domain` 站点数据后重登；码流页可直接试 `http://luna.qiyi.domain/Video_selection_plan`（需重登后路由才注入）。
- 研发建议：`/api/tologin` 每次从 DB 重建 `CurrentUser` 写回 session，或在改权限后主动失效相关 session。

## 2026-09-17 / 右上角「环境/分支」链接无权限

- 入口：`Home.vue` 右上角环境名链到 **`/environmentManage`**（环境管理页），与码流页 **`/Video_selection_plan`** 不是同一权限。
- 线上 `Privilege`：`/environmentManage` 为 **privilegeGroup=48**（`环境管理`，parentId=7 系统管理）；同组还有 **`/dataReport`（数据报表）**。
- 仅开码流组 **33** 不够；需给用户勾选并保存 **组 48** 后 **重新登录**，才能进环境管理页切换分支。
