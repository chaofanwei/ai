# VIDEODEV-5896 屏蔽儿童频道分支互动视频的奇巴布片头

- PMS: VIDEODEV-5896
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5896
- 需求标题: 屏蔽儿童频道分支互动视频的奇巴布片头
- 开发分支: fan_5896_block_qibabu_parts
- Commit: 3c0020b3c
- 推送状态: 已推送至 origin/fan_5896_block_qibabu_parts
- PMS 完成备注: 已添加，comment_id 2905518
- PMS 月神分支补充备注: 已添加，comment_id 2905525
- 月神环境: 5896_hudong_ertong
- 修改时间: 2026-08-06 10:47:08 CST
- Codex session Id: 019fd4e5-24c0-7663-9797-9c12545caa85

## 背景

儿童频道互动视频切换分支时会重复播放奇巴布片头。需求要求对 PMS 指定的 33 个 `tvid` 强制关闭奇巴布前贴和后贴，并要求视频列表通过月神 `config_profile` 管理，不写死在 Lua 代码中。

## 实现过程与改动

1. 基于最新 `master` 创建开发分支 `fan_5896_block_qibabu_parts`。
2. 在月神开发环境 `5896_hudong_ertong` 新增 `config_profile` 配置：
   - 配置项: `no_qibabu_parts_tvids`
   - 描述: `VIDEODEV-5896 屏蔽奇巴布前后贴的视频列表`
   - 配置值: PMS 描述中的 33 个 `tvid`，使用逗号分隔。
   - 状态: 已保存到开发环境，未发布。
3. 修改 `p911/rules/video/back_part.lua`：
   - 通过 `request_utils.in_config(request.tvid, 'no_qibabu_parts_tvids')` 读取月神配置。
   - 命中配置的视频不执行奇巴布前后贴组装。
   - 未配置或未命中的视频保持原有逻辑。
   - 33 个视频 ID 未写入项目代码。
4. 修改 `spec/p911/rules/video/back_part_spec.lua`：
   - 覆盖配置命中时不添加奇巴布前后贴。
   - 覆盖配置未命中时正常添加奇巴布前后贴。
   - 覆盖配置缺失时保持原有行为。

## 验证

- `luac -p vis-rule-engine/src/main/lua/p911/rules/video/back_part.lua vis-rule-engine/src/main/lua/spec/p911/rules/video/back_part_spec.lua`
  - 结果: 通过。
- `/home/fan/shells/busted spec/p911/rules/video/back_part_spec.lua`
  - 结果: `7 successes / 0 failures / 0 errors / 0 pending`。
- 月神配置查询
  - 结果: `no_qibabu_parts_tvids` 新增成功，页面显示 33 个 `tvid`。

## 修改记录

### 2026-08-06 10:43:08 CST

- Codex session Id: 019fd4e5-24c0-7663-9797-9c12545caa85
- 完成月神配置、Lua 规则判断及定向单测。

### 2026-08-06 10:47:08 CST

- Codex session Id: 019fd4e5-24c0-7663-9797-9c12545caa85
- 提交并推送 commit `3c0020b3c` 至 `origin/fan_5896_block_qibabu_parts`。
- PMS 开发完成备注添加成功，接口返回 `code=A00000`，`comment_id=2905518`。
- 月神配置仍仅保存于开发环境，未执行发布。

### 2026-08-06 10:48:32 CST

- Codex session Id: 019fd4e5-24c0-7663-9797-9c12545caa85
- 补充 PMS 备注，明确月神环境分支 `5896_hudong_ertong`、配置项 `config_profile.no_qibabu_parts_tvids` 及未发布状态。
- 接口返回 `code=A00000`，`comment_id=2905525`。
