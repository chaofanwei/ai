# VIDEODEV-5897 点播-体育业务-将新爱鉴权的视频付费状态同步到bossStatus字段

- PMS: VIDEODEV-5897
- 需求链接: http://pms.qiyi.domain/browse/VIDEODEV-5897
- 需求标题: 点播-体育业务-将新爱鉴权的视频付费状态同步到bossStatus字段
- 开发分支: fan_5897_xinai_boss_status
- 最新提交: fcc57a1a1
- 推送状态: 已推送至 origin/fan_5897_xinai_boss_status
- PMS 完成备注: 已添加，业务修改 comment_id=2905955，QCD 修复 comment_id=2905963
- 修改时间: 2026-08-06 16:31:01 CST
- Codex session Id: 本轮会话未暴露

## 背景

体育小屏 app 命中 `sports_auth_src_white_list` 后，会调用新爱鉴权接口 `/xinai-video/auth/userAuth`。原逻辑虽然使用新爱返回的 `data.chargeStatus` 处理试看和播放权限，但最终会无条件将 `content.bossStatus` 设置为 `0`，没有向大播放模式同步视频是否付费。

非体育普通点播链路中，`bossStatus=0` 表示免费视频，`bossStatus=2` 表示付费视频。新爱接口的 `data.chargeStatus=2` 表示付费视频。

## 改动

1. `p911.vip.vip_right`
   - 在 `sports_auth_check_by_platformid` 中增加 `boss_status`，默认使用 `P.PROGRAM_BOSS_STATUS_FREE`。
   - 仅当请求 `src` 命中 `sports_auth_src_white_list`，且新爱鉴权成功返回 `data.chargeStatus=2` 时，将其设置为 `P.PROGRAM_BOSS_STATUS_PAID`。
   - 付费场景在同一白名单判断中将上述状态保存到 `request._sports_cvt_final_boss_status`；免费场景无需保存，处理中统一保持 `response.data.content.bossStatus=0`，避免跳过普通 BOSS 后因缺少 `boss_ts` 导致 MUS/DRM 码流地址封装失败。
   - 原 `/security/qp/authNew` 平台白名单鉴权、其他体育请求和非体育请求的处理保持不变。

2. `p911.rules.post.log`
   - 沿用项目历史上的 BOSS 降级恢复位置，在所有码流选择及地址封装完成后的 log 阶段，将 `request._sports_cvt_final_boss_status` 恢复到最终响应的 `content.bossStatus`。
   - 非新爱小屏请求没有该临时字段，后处理行为保持不变。

3. 单元测试
   - 覆盖新爱小屏付费视频同步 `bossStatus=2`。
   - 覆盖新爱小屏免费视频同步 `bossStatus=0`。
   - 覆盖旧平台白名单即使鉴权返回付费状态，仍保持原有 `bossStatus=0` 行为。
   - 覆盖 charge 阶段临时保持 `bossStatus=0`，且保存的最终状态不丢失。
   - 覆盖码流封装完成后恢复最终 `bossStatus`，以及普通请求不受影响。
   - 明确 `control.charge.status` 继续保持 `0`，不随新爱 `chargeStatus` 修改。

## 验证

- `luac -p` 检查本次涉及的 2 个生产 Lua 文件和 3 个 spec 文件。
  - 结果: 通过。
- `/home/fan/shells/busted spec/p911/vip/vip_right_spec.lua`
  - 结果: `7 successes / 0 failures / 0 errors / 0 pending`。
- `/home/fan/shells/busted spec/p911/rules/charge/charge_spec.lua`
  - 结果: `2 successes / 0 failures / 0 errors / 0 pending`。
- `/home/fan/shells/busted spec/p911/rules/post/log_spec.lua`
  - 结果: `3 successes / 0 failures / 0 errors / 0 pending`。

## 修改记录

### 2026-08-05 10:47:39 CST

- Codex session Id: 本轮会话未暴露
- 完成新爱小屏视频付费状态到 `bossStatus` 的同步，并补充隔离范围及付费/免费场景单测。

### 2026-08-06 16:06:29 CST

- Codex session Id: 本轮会话未暴露
- 复查发现新爱鉴权阶段写入的 `bossStatus=2` 会被后续 `charge.charge` 清零；若直接阻止清零，又会因新爱链路没有普通 BOSS 的 `boss_ts` 而影响 MUS/DRM 地址封装。
- 调整为鉴权阶段保存最终付费状态、处理中保持免费状态完成码流封装、沿用历史 BOSS 降级方案在 `post.log` 阶段恢复最终响应状态，并补充鉴权、中间清零和最终恢复三段回归测试。
- 提交 `1f3913d39` 已推送至 `origin/fan_5897_xinai_boss_status`；PMS 开发完成备注添加成功，`comment_id=2905955`。

### 2026-08-06 16:31:01 CST

- Codex session Id: 本轮会话未暴露
- QCD 全量测试发现 `charge_spec` teardown 将共享的 `package.preload['ngx.upstream']` 直接清空，导致后续 `inter_charge_spec` 加载 `dash_utils` 时报模块不存在。
- `charge_spec` 改为保存并恢复进入测试前的 preload；`inter_charge_spec` 显式保存、注册和恢复自身依赖的 `ngx.upstream` mock，消除测试顺序依赖。
- `charge_spec + inter_charge_spec` 组合测试结果：`6 successes / 0 failures / 0 errors`。
- 完整 `/home/fan/shells/busted` 结果：`880 successes / 0 failures / 0 errors / 0 pending`。
- QCD 修复提交 `fcc57a1a1` 已推送至 `origin/fan_5897_xinai_boss_status`；PMS 修复完成备注添加成功，`comment_id=2905963`。
