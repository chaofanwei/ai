# VIDEODEV-5899 直播-体育业务-将新爱鉴权的视频付费状态同步到bossStatus字段

- PMS: http://pms.qiyi.domain/browse/VIDEODEV-5899
- 修改时间: 2026-08-06 17:51:22 CST
- Codex session id: 019fd63e-e31b-7631-a101-5b7e68165605
- 开发分支: `fan_5899_xinai_boss_status`

## 背景

体育小屏 `src` 白名单请求会调用新爱 `/xinai-video/auth/userAuth` 接口鉴权。现有直播逻辑只处理新爱返回的播放、试看权益，没有使用 `chargeStatus` 更新 `response.data.boss`，因此端上收到的付费状态仍是直播元数据或分端付费信息中的原值，可能与新爱判定不一致。

点播 VIDEODEV-5897 已约定新爱 `chargeStatus == 2` 表示付费，并在码流处理完成后将最终状态同步到 `bossStatus`。

## 改动

1. 在 `vis-rule-engine/src/main/lua/p918/rules/boss_proxy.lua` 中，仅对体育小屏 `src` 走新爱鉴权且鉴权成功、存在返回数据的请求，根据 `chargeStatus` 暂存最终付费状态：等于 `2` 时为付费 `2`，其他值为免费 `0`。
2. 在 `vis-rule-engine/src/main/lua/p918/rules/log_process.lua` 中，码流处理完成、响应 JSON 编码前将暂存状态同步到 `response.data.boss`，避免中途修改影响现有码流过滤和封装逻辑。
3. 普通体育 `pld` 请求继续调用 `/security/qp/authNew`，不使用其返回值覆盖 `response.data.boss`；新爱请求失败或没有返回数据时也保留原值。
4. 在 `vis-rule-engine/src/main/lua/spec/p918/rules/boss_proxy_rule_spec.lua` 中补充付费、免费和普通体育鉴权场景的定向测试。
5. 根据评审意见，将最终状态回写位置由 `post_process.lua` 调整为 `log_process.lua`，与点播在最终响应阶段恢复 `bossStatus` 的做法保持一致。

## 验证

- 已执行定向单测：`boss_proxy_rule_spec.lua`，结果 `4 successes / 0 failures / 0 errors`。
- 已执行体育小屏前置校验与鉴权规则组合回归：`pre_check_spec.lua`、`boss_proxy_rule_spec.lua`，结果 `17 successes / 0 failures / 0 errors`。
- 已执行 `git diff --check`，未发现空白错误。

## 提交与推送

- Commit: `7a5cb294f`
- 已推送远端分支：`origin/fan_5899_xinai_boss_status`
- 已添加 PMS 开发完成备注，接口返回 `code=A00000`，`comment_id=2906085`。
