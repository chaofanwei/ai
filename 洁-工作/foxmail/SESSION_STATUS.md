# Foxmail 会话续作状态（2026-08-08）

## 目标
从备份中取出邮件 **129547**（2025-08-27「员工手册」）里的截图附件：

- 主题：关于公司《员工手册》及《考勤管理制度》更新及生效的通知
- 发件：周海贵 / bjxingzheng@bidcenter.cn
- 附件：`Catch(08-27-10-27-42).jpg`（约 248–304KB）
- 原信路径：`Storage/huijie@bidcenter.cn/Mails/11/16/129547`（319995 字节，加密）

## 已确认
1. **列表/索引可读**：标题、时间、发件人、附件名都能从 Index / Decode 元数据拿到。
2. **Wine 正文预览不可用**：CEF 阅读窗格黑屏/空白；关 `libGLESv2` 后仍不行。启动脚本：`start_foxmail_wine.sh`。
3. **`FoxCryptoPP.dll` 的 `ipc_decrypt`**：
   - 真实调用是 **2 参数 cdecl：`(void* data, uint len)`，原地加解密**
   - 算法为 **AES-CFB-128**，自带固定密钥，roundtrip 正常
   - 该密钥 **不能** 解开 `Mails/` 下原信（网络包加密 ≠ 本地邮件存储加密）
4. **`Index.key`**（`07d04d22…1a12`）在 Index 头里也有；用它做 AES-CFB/CBC 多组 IV 推导，**仍解不开** 129547 原信。
5. Decode 元数据里附件在解密后偏移：`bodyPos=7739`，`secLen=311856`（Base64 JPEG）。

## 当前阻塞
本地原信加密密钥/派生方式未打通；Wine 下也无法稳定「另存附件」。

## 推荐下一步（按可行性）
1. **Mac 版 Foxmail**（已安装）用企业邮客户端授权码登录 `huijie@bidcenter.cn`，只收/搜这封，另存 `Catch(08-27-10-27-42).jpg`。
2. **Win7 远程**恢复 SSH 后，在已有 Foxmail 里打开同备份另存附件。
3. 继续逆向：在 Foxmail 选中该邮件时 hook 解密缓冲（勿对进程长期 lldb attach，会把进程卡在 `TX` 状态）。

## 相关文件
- 启动：`start_foxmail_wine.sh`
- 说明正文：`salary_export/bodies/main__129547.txt`
- 截图目录：`salary_export/handbook_20250827/`
- 工具：`tools/fox_ipc_decrypt.*`（旧 3 参尝试，已确认 ABI 不符）
