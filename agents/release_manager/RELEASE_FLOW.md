# Release Apply Flow

本目录用于整理 VRS 每周上线申请，并在用户确认后通过 Playwright 自动填写 release-mgmt 表单。

## 固定流程

1. 读取 `AGENTS.md` 和 `demo.txt`。
2. 根据用户提供的上线内容生成申请文件，文件名形如 `v202605W1v1`。
3. 让用户确认文件内容、排序、Review、上线人、日期等都没有问题。
4. 用户确认后，再打开 release-mgmt 浏览器页面自动填表。
5. 自动填表只填写内容，不点击“提交”，提交前必须由用户人工检查。

## 文件整理规则

- 输出格式参考 `demo.txt`。
- 技术优化、业务需求通常合并到 `代码修改`；运维部署放到 `运维`。
- 每个部分内部按 `dash`、`live/直播`、其他排序。
- dash/live 服务上线人是刘贺，其他服务上线人是开发者本人。
- Review 规则以 `AGENTS.md` 为准。
- 日期按当前日期和后续工作日规则填写。

## 自动填表脚本

依赖：

```bash
npm install
```

执行：

```bash
node scripts/fill_release_apply.js v202605W1v1
```

如果已经通过 Playwright MCP 启动了带 `remote-debugging-port=9222` 的 Chrome，也可以使用 CDP 连接模式：

```bash
~/shells/start-ai-chrome.sh
npm run fill:cdp -- v202605W1v1
```

也可以通过环境变量指定其他 CDP 地址：

```bash
CDP_URL=http://127.0.0.1:9222 npm run fill:cdp -- v202605W1v1
```

脚本会打开：

```text
http://release-mgmt.qiyi.domain/release_manage/relApply/app/apply_add
```

如果跳到 SSO 登录页，需要用户在打开的 Chrome 里完成登录；脚本会等待登录后继续。

脚本会自动填写：

- `PMS ID`：从申请文件中提取所有 `VIDEODEV-*`
- `上线内容`：调用页面内置 `chooseJira()` 自动同步
- `上线备注`：写入申请文件全文
- `邮件主题`：`VRS上线申请(<文件名>)`
- 邮件主题右侧复选框：勾选

脚本不会点击“提交”。

## Playwright 实现要点

- 使用 `playwright-core` 和系统 Chrome：`/usr/bin/google-chrome`。
- 使用持久化 profile：`/tmp/release_mgmt_pw_profile`，便于保留 SSO 登录态。
- `scripts/fill_release_apply_cdp.js` 使用 `chromium.connectOverCDP()` 连接已启动的 Chrome，不负责启动或关闭浏览器。
- 可以通过环境变量覆盖：

```bash
CHROME_PATH=/usr/bin/google-chrome \
RELEASE_MGMT_PROFILE_DIR=/tmp/release_mgmt_pw_profile \
node scripts/fill_release_apply.js v202605W1v1
```

- PMS 弹窗实际页面是 `/release_manage/pop/jiralist`，但正式脚本不逐项点击弹窗，而是调用申请页内置函数：

```javascript
window.chooseJira({ issueIds, issueKeys });
```

这会写入 `#JiraKey`、`#summary`，并触发页面自己的工程信息、上线版本、测试报告、前置需求同步逻辑。

## 注意事项

- 自动填表前必须先生成并确认申请文件。
- 自动填表后必须人工检查浏览器页面。
- 若页面结构变化，优先检查 `chooseJira()`、`#description`、`#mailTitle`、`#ifMailTitle` 是否仍存在。
- 如果 Chrome 启动时报 sandbox/socket 权限错误，需要用授权方式在沙箱外执行 Node 脚本。
