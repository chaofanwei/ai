---
name: iqiyi-skill-manager
description: 管理 iQIYI/iBrain Skill 市场中的 Agent Skill 全生命周期。用于查找、搜索、列表展示、安装、校验、打包、发布、上传或分享 Skill；触发场景包括：技能、找技能、find-skill、find-skills、有没有这个功能的 skill、install skill、publish skill、发布 skill、上传 skill、打包发布、分享内部 skill。
---

# iQIYI Skill Manager

使用本 Skill 处理 iQIYI/iBrain Skill 市场的完整流程：

- 查找、浏览并安装市场中的 Skill。
- 校验、打包并发布本地 Skill 目录或 zip 包。

## 公共规则

- Agent 名称：当前环境使用 `Codex`。其他环境按实际 Agent 使用 `Cursor`、`OpenClaw`、`ClaudeCode` 或对应名称。
- Registry endpoint base: `http://ai-registry-proxy.qsm.qiyi.middle/skills`。
- 从 `IBRAIN_PERSONAL_TOKEN` 和 `IBRAIN_PROJECT_TOKEN` 读取 token。不要输出 token 明文。
- 查询、搜索、列表展示和安装前的发现流程是只读操作；token 缺失时继续执行，但提醒用户可能只能访问公开 Skill。
- 发布是写操作；如果任一 token 缺失，停止发布，并提示用户到奇智平台右上角的「访问密钥」页面获取 token，然后配置：

```bash
export IBRAIN_PERSONAL_TOKEN="..."
export IBRAIN_PROJECT_TOKEN="..."
```

- curl、网络或 API 失败时，说明失败动作、非敏感错误/响应摘要，并建议重试。
- 不要删除源 Skill 目录。
- 校验失败时，不要静默修改用户文件。
- 除非用户明确要求，不要覆盖用户改动。

## 查找或安装 Skill

### 1. 选择查询模式

按用户意图只选择一种模式：

| 用户意图 | 查询参数 | 结果处理 |
| :--- | :--- | :--- |
| 精确查找，例如“有没有叫 xxx 的 skill” | `skillName=<name>` | 精确匹配 |
| 模糊查找，例如“有没有和 xxx 相关的 skill” | `search=<keyword>` | 最多展示接口返回的 5 条 |
| 浏览或列出全部，例如“有哪些 skill 可以用” | 不传查询参数 | 按 `scope` 分组 |

调用 list API；如果 token 存在则一并传入：

```bash
curl -s --max-time 10 --retry 2 --retry-delay 1 \
  "http://ai-registry-proxy.qsm.qiyi.middle/skills/list?skillName=<name>&personalToken=${IBRAIN_PERSONAL_TOKEN:-}&projectToken=${IBRAIN_PROJECT_TOKEN:-}"

curl -s --max-time 10 --retry 2 --retry-delay 1 \
  "http://ai-registry-proxy.qsm.qiyi.middle/skills/list?search=<keyword>&personalToken=${IBRAIN_PERSONAL_TOKEN:-}&projectToken=${IBRAIN_PROJECT_TOKEN:-}"

curl -s --max-time 10 --retry 2 --retry-delay 1 \
  "http://ai-registry-proxy.qsm.qiyi.middle/skills/list?personalToken=${IBRAIN_PERSONAL_TOKEN:-}&projectToken=${IBRAIN_PROJECT_TOKEN:-}"
```

预期响应结构：

```json
{
  "totalCount": 0,
  "pageItems": [
    {
      "name": "skill-name",
      "description": "description",
      "scope": "PUBLIC",
      "downloadCount": 0,
      "bizTags": "tag"
    }
  ]
}
```

`downloadCount` 缺失或为 null 时按 `0` 处理；`bizTags` 缺失或为 null 时按空值处理。

### 2. 展示结果

输出前必须按顺序执行以下门控：

1. 如果本次使用 `search` 做模糊搜索，保持接口返回顺序，不分组、不排序，输出所有返回项。表格列为 `Skill 名称`、`描述`、`业务标签`、`下载次数`，并说明模糊搜索最多返回 5 条。
2. 否则，如果用户明确要求“显示全部”“展示所有”“列出全部”“show all”或“list all”，按 `scope` 分组，每组内按 `downloadCount` 降序排列，并输出全部条目。
3. 否则，按 `scope` 分组，每组内按 `downloadCount` 降序排列，每组只输出前 20 条。第 21 条及之后不得出现在输出中。若某组超过 20 条，追加：`仅展示下载量 Top 20，该分类共 {total} 个 Skill。如需查看全部，请回复「显示全部」。`

`scope` 展示名：

- `PUBLIC`: 公开 Skill
- `APPROVE`: 审核可见 Skill
- `PRIVATE`: 私有 Skill

非模糊搜索的默认输出以这行开头：

```text
共找到 N 个 Skill（默认每分类仅展示下载量 Top 20）：
```

展示结果后，指出最匹配的 Skill 并询问是否安装：

```text
最符合你需求的是：**<skill-name>** (<scope label>) - <description>
需要我安装吗？
```

如果没有找到 Skill，告知用户未找到，并提供直接协助或建议换关键词重试。

### 3. 用户确认后安装

下载：

```bash
curl -s --max-time 30 --retry 2 --retry-delay 1 \
  -o "/tmp/<skill-name>.zip" \
  "http://ai-registry-proxy.qsm.qiyi.middle/skills/get?skillName=<skill-name>&agent=Codex&personalToken=${IBRAIN_PERSONAL_TOKEN:-}&projectToken=${IBRAIN_PROJECT_TOKEN:-}"
```

解压并安装：

```bash
mkdir -p "/tmp/<skill-name>_extract"
unzip -o "/tmp/<skill-name>.zip" -d "/tmp/<skill-name>_extract"
mkdir -p ~/.skills/<skill-name>
if [ -d "/tmp/<skill-name>_extract/<skill-name>" ]; then
  mv "/tmp/<skill-name>_extract/<skill-name>/"* ~/.skills/<skill-name>/
else
  mv "/tmp/<skill-name>_extract/"* ~/.skills/<skill-name>/
fi
rm -rf "/tmp/<skill-name>_extract" "/tmp/<skill-name>.zip"
```

校验并创建可用链接：

```bash
ls ~/.skills/<skill-name>/SKILL.md
mkdir -p ~/.agents/skills ~/.openclaw/workspace/skills
ln -sfn ~/.skills/<skill-name> ~/.agents/skills/<skill-name>
ln -sfn ~/.skills/<skill-name> ~/.openclaw/workspace/skills/<skill-name>
```

如果链接创建失败，不要让整个安装失败；说明链接失败，并保留已验证的 `~/.skills/<skill-name>/SKILL.md` 安装结果。

## 发布 Skill

### 1. 收集输入

只询问缺失的必填项：

- `skill_dir` 或 `zip_path`：优先使用包含 `SKILL.md` 的目录。
- `name`：使用 `SKILL.md` frontmatter 中的 `name`，不要使用 `displayName`。
- `displayDescription`：市场页面展示的简短介绍。
- 首次发布时，必须要求用户确认 `bizTags` 和 `authorityScope`。只有用户明确确认不指定时，才使用默认值。

首次发布且用户明确确认不指定时，使用这些默认值：

- `bizTags`: `测试,Skill`
- `authorityScope.type`: `public`
- `authorityScope.scope`: 空

支持的 `authorityScope` 形式：

- 公开：`type=public`，`scope=`
- 指定个人：`type=person`，`scope=wangbiwen,zhangsan`
- 指定组织：`type=org`，`scope=智能平台部-云服务部`

如果用户需要组合多种可见范围，说明当前表单发布接口优先使用单一 `authorityScope`；尝试数组形态 payload 前需先确认服务端支持。

### 2. 校验 Skill 目录

发布目录时，优先运行官方校验：

```bash
skills-ref validate "$SKILL_DIR"
```

如果官方工具不可用，执行轻量校验：

- `skill_dir` 存在，并且包含 `SKILL.md`。
- `SKILL.md` 以 YAML frontmatter 开头。
- Frontmatter 包含非空 `name` 和 `description`。
- `name` 等于目录 basename。
- `name` 符合 `^[a-z0-9]+(-[a-z0-9]+)*$`，且长度不超过 64。
- `description` 长度为 1-1024。
- Frontmatter 后存在非空 Markdown 正文。

任一规则失败都停止发布，说明失败规则，并询问是否先修复。

### 3. 按需打包

如果用户未提供 zip，则从 Skill 目录内部打包，确保 `SKILL.md` 位于 zip 根目录：

```bash
SKILL_NAME="$(basename "$SKILL_DIR")"
ZIP_PATH="/tmp/${SKILL_NAME}.zip"
rm -f "$ZIP_PATH"
(
  cd "$SKILL_DIR" &&
  zip -rq "$ZIP_PATH" .
)
test -s "$ZIP_PATH"
unzip -l "$ZIP_PATH" | grep -Eq '(^|[[:space:]])SKILL.md$'
```

如果 zip 中是 `parent/SKILL.md` 而不是根目录 `SKILL.md`，必须重新打包后再发布。

### 4. 判断是否首次发布

尽量判断同名 Skill 是否已存在：

```bash
curl -s --max-time 10 \
  "http://ai-registry-proxy.qsm.qiyi.middle/skills/list?skillName=${NAME}&personalToken=${IBRAIN_PERSONAL_TOKEN:-}&projectToken=${IBRAIN_PROJECT_TOKEN:-}"
```

- 如果存在同名 Skill，按更新发布处理。
- 如果不存在同名 Skill、API 失败或结果不明确，按首次发布处理。
- 首次发布时，说明 `bizTags` 和 `authorityScope` 会成为市场展示与可见范围的初始配置；如果用户未提供，必须询问。
- 更新发布时，如果用户未提供 `bizTags` 或 `authorityScope`，不要追问；省略这些字段，让服务端复用历史值。

### 5. 展示 dry-run 并等待确认

发布是状态变更。调用发布接口前，必须展示 dry-run 摘要并等待用户最终确认；即使用户一开始说“直接发布”，也要先确认。

```text
Skill: {name}
Zip: {zip_path}
Endpoint: http://ai-registry-proxy.qsm.qiyi.middle/skills/publish
displayDescription: {displayDescription}
bizTags: {bizTags or "未传，服务端复用历史值"}
authorityScope.type: {type or "未传，服务端复用历史值"}
authorityScope.scope: {scope or "未传，服务端复用历史值"}
agent: Codex
IBRAIN_PERSONAL_TOKEN: yes/no
IBRAIN_PROJECT_TOKEN: yes/no
X-API-KEY: yes/no
```

首次发布并使用用户确认后的默认值时，必须明确标注：

```text
bizTags: 测试,Skill（用户确认不指定，使用默认值）
authorityScope.type: public（用户确认不指定，使用默认值）
```

### 6. 发布

使用 multipart form data POST 到：

```text
http://ai-registry-proxy.qsm.qiyi.middle/skills/publish
```

必填字段：

- `file=@${ZIP_PATH}`
- `name=${NAME}`
- `displayDescription=${DISPLAY_DESCRIPTION}`
- `agent=Codex`
- `personalToken=${IBRAIN_PERSONAL_TOKEN}`
- `projectToken=${IBRAIN_PROJECT_TOKEN}`

条件字段：

- 首次发布：传入用户指定或用户明确确认后的默认 `bizTags`、`authorityScope.type`、`authorityScope.scope`。
- 更新发布：只有用户提供了新值时，才传入 `bizTags` 或 `authorityScope.*`。
- 如果需要 API key，增加 `-H "X-API-KEY: ${API_KEY}"`，但不要输出 key 明文。

示例：

```bash
FORM_ARGS=(
  -F "file=@${ZIP_PATH}"
  -F "name=${NAME}"
  -F "displayDescription=${DISPLAY_DESCRIPTION}"
  -F "agent=Codex"
  -F "personalToken=${IBRAIN_PERSONAL_TOKEN}"
  -F "projectToken=${IBRAIN_PROJECT_TOKEN}"
)

if [ -n "${BIZ_TAGS:-}" ]; then
  FORM_ARGS+=( -F "bizTags=${BIZ_TAGS}" )
fi

if [ -n "${AUTHORITY_SCOPE_TYPE:-}" ]; then
  FORM_ARGS+=( -F "authorityScope.type=${AUTHORITY_SCOPE_TYPE}" )
  FORM_ARGS+=( -F "authorityScope.scope=${AUTHORITY_SCOPE_SCOPE:-}" )
fi

curl -s --max-time 60 --retry 2 --retry-delay 1 \
  -X POST "http://ai-registry-proxy.qsm.qiyi.middle/skills/publish" \
  "${FORM_ARGS[@]}"
```

成功响应结构：

```json
{"code":0,"message":"success","data":"10000000022"}
```

当 `code == 0` 且 `data` 非空时，回复：

```text
发布成功：{name}
skill_id：{data}
详情页：http://ibrain.qiyi.domain/skill/console/{data}
```

失败时展示 `code`、`message` 和不含敏感信息的响应摘要。
