---
name: qpaas-template-update
description: 在爱奇艺 QPaas 批量更新应用模板（新建版本、加 fastjson safeMode、绑定环境配置、版本对比验收）。用于 QPaas、应用模版、环境信息配置、fastjson、k8s-conf-agent、版本对比、Playwright 9222 等场景。
---

# QPaas 应用模板批量更新

在 QPaas 为 `k8s-conf-agent` 增加 `-Dfastjson.parser.safeMode=true`，创建新应用模版版本，更新环境「应用模版版本」，**默认不部署**。

## 前置条件

| 项 | 值 |
|---|---|
| 浏览器 | `~/shells/start-ai-chrome.sh`，CDP `http://127.0.0.1:9222` |
| 自动化 | Playwright MCP 或 `puppeteer-core` 连接 9222 |
| 应用 URL | `http://paas.cloud.qiyi.domain/#/app/appDetail/{appId}/` |
| 模版列表 | `#/app/appDetail/{appId}/version?vTab=done&tab=version` |

启动浏览器：

```bash
curl -s http://127.0.0.1:9222/json/version || ~/shells/start-ai-chrome.sh
```

## 标准流程

```
盘点环境当前模版 → 去重建新模版 → 逐环境改配置 → 版本对比验收
（不部署，除非用户明确要求）
```

### 1. 盘点

逐 PROD 环境读取 **应用模版版本**（label 与 value 可能分行，取「应用模版版本：」下一行）。

去重：同一模版名只建 **1 个** 新版本，多环境共用。

### 2. 版本号命名（日期 `{YYYYMMDD}`）

| 规则 | 示例 |
|---|---|
| 模版名**含日期/年份** → **替换** | `AZ-20251022` → `AZ-20260722` |
| 模版名**含日期** → **替换** | `live-hk-20250327` → `live-hk-20260722` |
| 模版名**无日期** → **末尾追加** | `live-default-az` → `live-default-az20260722` |
| 带时间戳的旧版 | `INTER 2025-07-31 17:14:24` → `INTER20260722` |

### 3. 创建应用模版

路径：`版本 → 我的应用模版 → 创建应用模版`

1. 填写新版本号
2. yaml 选 **「导入已发布的版本」**
3. 下拉框选 **已发布模版版本名**（不是环境名）
4. **必须精确匹配**下拉项：`t === name || t.startsWith(name + '（')`
5. 在 `k8s-conf-agent` 的 `command` 中，于 `-Dspring.profiles.active=${PROFILE_AGENT}` 与 `-jar` 之间插入：

```yaml
            - "-Dfastjson.parser.safeMode=true"
```

6. 点 **「确定」** 发版

创建前检查新版本是否已存在；若错误版本已建且未部署，先解绑环境再删除错误模版。

### 4. 更新环境配置

路径：`运行环境 → {环境} → 编辑环境信息配置`

- 只改 **应用模版版本**，模版参数保持不变
- 下拉选模版时用 **精确匹配**（避免 `AZ-20260722` 误选 `AZ-20260722-prerelease-qlbservice`）
- 保存后预期：**配置变更成功**
- 部署详情「与环境配置不一致」属预期（未滚动升级）

### 5. 验收（权威方式）

路径：`版本 → 我的应用模版 → 版本对比`

1. 每次对比前 **关闭残留弹窗**，进入正确 `appId` 的模版页
2. 两个下拉框 **精确匹配** 旧模版名与新模版名
3. 点 **对比**

**符合预期**：总差异 **1 行**，内容为 `-Dfastjson.parser.safeMode=true`（UI 常显示 `+0 additions / -1 deletions`）。

不要用 yaml 弹窗或 `hasText` 子串匹配做结构验收（易误报/误选）。

## 自动化要点

| 项 | 建议 |
|---|---|
| 创建模版 | 每次 **1 个**，避免 MCP 超时 |
| 环境绑定 | 每批 **3～4 个** |
| 导入/绑定 | 禁止 `filter({ hasText })` 模糊匹配 |
| 版本对比 | 对比弹窗内用前两个 `input[type="text"]` 选版本 |
| 跨应用 | 切换 appId 后必须重新打开对比弹窗 |

## 常见踩坑

| 现象 | 原因 | 处理 |
|---|---|---|
| 新模版缺 Service/Skywalker/Consul | 导入时子串命中了 `xxx-grey-v3` 等同系列名 | 删除重建，精确选来源模版 |
| 版本对比 +45/-45 | 弹窗残留其他应用/模版的对比结果 | 关闭弹窗、确认 appId 后重比 |
| 环境显示新模版名但对比找不到 | 模版未成功发版或已被删 | 从正确来源重建并重新绑定 |
| 读模版版本为 N/A | 页面未加载完 | 等待 2～3s 后重读 |

## 完成清单输出

验收通过后输出表格：环境名、旧模版、新模版、版本对比结果（1 行 fastjson）。

## 附加资源

- 已处理应用与模版映射见 [reference.md](reference.md)
