# VIDEODEV-5830 【直播】isLogin设置bug修复

## 基本信息

- PMS 标题：【直播】isLogin设置bug修复
- PMS 链接：http://pms.qiyi.domain/browse/VIDEODEV-5830
- 修改时间：2026-06-16 15:01:21 CST
- Codex session id：019ecf24-6b48-7992-8d56-852ff4371c07
- 开发分支：fan_5830_islogin_label_fix

## 背景

`post_process.lua` 的 `set_response_labels` 中 `is_login` 标签原来使用 `request.isLogin` 判断。该字段只在部分 URI 场景按 pck/cookie 计算，不适合作为直播 `/live` 链路的标签依据。

最终方案收敛为只修改 labels 赋值逻辑：如果 `v == 1` 或 `uid` 参数合法，则认为标签中的 `is_login` 为已登录。

## 改动

1. 在 `p918/rules/post_process.lua` 中新增局部 `is_login(request)`。
2. `set_response_labels` 中 `label_info['is_login']` 改为按 `is_login(request)` 输出 `1/0`，其中 `is_login` 逻辑为 `tonumber(request.v) == 1 or uid > 0`。
3. 已回滚前一次将 `is_login` 统一写入 request 的方案，避免影响 `rate_control`、`stream_filter` 等链路。

## 验证

- 已检查源码 diff：最终只修改 `p918/rules/post_process.lua`。
- 已执行 `luac -p p918/rules/post_process.lua` 检查。
