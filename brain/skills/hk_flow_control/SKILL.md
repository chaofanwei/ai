---
name: hk-flow-control
description: 管理香港黑产流量的 IP 清单封禁、登录凭证校验和发布流程。用于自动下载新的IP列表文件（如all_ips）、校验完整 IPv4 格式/数量/排序/重复项、对比新旧版本、用本地 LuaJIT 实测加载耗时及内存，维护目标 src 的 uid/authcookie/Passport 校验，以及上传服务器、reload OpenResty 和发布后验收；触发场景包括“下载最新 IP 文件”“又来了新的 IP 文件”“看下这个 IP 清单是否可以”“对比新旧 all_ips”“上传 IP 清单”“authcookie与uid校验”“Passport校验”“reload 检测”“香港流量封禁名单更新”。
---

# 香港黑产 IP 清单检查

按“下载 → 检查 → 发布与验收”三个阶段执行，并维护本文件中的更新记录。当前只有检查阶段已配置；下载和发布阶段仍是骨架，所有 `TODO` 补齐前不得执行对应阶段。除非用户明确要求，否则不要改项目代码、提交或推送。

## 项目上下文

- PMS：`VIDEODEV-5891 dash-海外黑产流量封禁`
- PMS 地址：`http://pms.qiyi.domain/browse/VIDEODEV-5891`
- 独立项目目录：`~/ai/brain/skills/hk_flow_control/luna-rule`
- 固定代码分支：`fan_5891_oversea_abuse_block`
- 当前实现提交：`ff6a25759`
- 源文件：`~/ai/brain/skills/hk_flow_control/luna-rule/vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua`
- 需求记录：`~/ai/agents/dash/requirements/VIDEODEV-5891_oversea_abuse_block.md`
- 服务端清单路径：`/data/all.ip.txt`
- 封禁条件：指定 `src=01080031010000000000`、`uid` 为空且 `request.ip` 精确命中清单；不匹配 `xff_ip`。

## 总体流程

| 阶段 | 当前状态 | 输入 | 产出/门禁 |
|---|---|---|---|
| 1. 自动下载 | `TODO：待配置` | 下载源、认证、日期/版本 | 本地候选文件；下载信息可追溯 |
| 2. 文件检查 | `可执行` | 候选文件、上一版基线 | 合法性、版本差异、LuaJIT 性能结论 |
| 3. 上传、reload 与验收 | `可执行` | 检查通过且获准发布的文件 | 覆盖 `/data/all.ip.txt`、reload、请求验收、必要时同步 `pre_check.lua` |

严格按顺序执行。阶段二未通过时不得进入阶段三；存在删除 IP 时，未经业务确认不得发布。涉及下载认证、上传服务器、替换线上文件、reload 或回滚时，遵守当前环境授权规则，不要猜测目标或命令。

## 阶段一：自动下载（待填写）

### 下载配置

- `TODO_DOWNLOAD_SOURCE`：下载地址、接口或获取方式。
- `TODO_AUTH`：认证方式和凭据来源；不要把密钥直接写入本文件。
- `TODO_LOCAL_DIR`：本地下载目录。
- `TODO_FILE_NAMING`：文件命名和日期/版本规则。
- `TODO_TIMEOUT_RETRY`：超时、重试次数和失败退出规则。
- `TODO_INTEGRITY`：期望的文件类型、大小范围、校验和或服务端元数据。

### 下载步骤骨架

1. 解析本次目标日期或版本，计算下载地址和本地目标路径。
2. 检查本地目标是否已存在，明确覆盖、复用或另存策略。
3. 下载到临时文件，禁止直接覆盖当前对比基线或线上同名文件。
4. 验证 HTTP/接口结果、文件非空、文件大小和可选校验和。
5. 原子重命名为候选文件，并记录来源、下载时间和版本信息。
6. 将候选文件交给阶段二；下载失败时停止，不得使用残缺文件继续。

在上述 `TODO` 未补齐前，如果用户要求自动下载，列出缺失配置并停止，不要自行推断。

## 已有更新记录

每次检查前完整读取 [ip_update_history.md](ip_update_history.md)，从中获取累计更新次数、历史数据和当前对比基线。新清单检查完成后只更新该历史文件，不要因更新记录修改本 `SKILL.md`。

## 已知实现约束

- 只使用独立源码 `~/ai/brain/skills/hk_flow_control/luna-rule`，不要使用或切换共享工作区 `~/lua/projects/luna-rule-2/luna-rule`。
- 每次检查前先确认代码分支为 `fan_5891_oversea_abuse_block`，并确认工作区干净；分支不符或存在未提交修改时先报告，不要擅自覆盖修改。
- 相关实现位于 `vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua`。
- `src=01080031010000000000` 的 uid/authcookie/Passport 校验、Nginx 限流冲突和代码单文件发布：执行前完整阅读 [references/authcookie_uid_control.md](references/authcookie_uid_control.md)。
- 服务端固定读取 `/data/all.ip.txt`。
- 清单必须是一行一个完整 IPv4，并按 IPv4 数值升序排列。
- 代码将 IPv4 转为 `uint32_t`，按每块 65,536 条存储并二分查找。
- 文件不存在、包含非法 IP 或数值降序时，当前 worker 记录错误并放行，且本 worker 不再重试。
- 清单按 worker 首次命中目标请求时懒加载；更新文件后需 reload/restart OpenResty worker。

## 阶段二：检查 IP 文件

### 1. 确认文件

展开用户给出的 `~` 路径，使用 `ls -lh`、`file`、`wc -l`、`sed` 和 `tail` 检查：

- 文件是否存在且可读；
- 文件大小和总行数；
- 头尾是否是一行一个 IPv4；
- 不要修改原文件。

路径不存在时，先用 `rg --files ~/ | rg '<文件名>'` 查找同名或近似文件；仍找不到再请用户确认。

### 2. 全量校验

使用 AWK 顺序扫描完整文件，不要只抽样。对每行完成以下检查：

1. 格式匹配四段十进制 IPv4；
2. 每段均在 `0..255`；
3. 将 IP 转为数值：`(((a * 256 + b) * 256 + c) * 256 + d)`；
4. 当前数值不得小于上一条，否则记为降序；
5. 当前数值等于上一条时记为重复。

至少输出：`lines`、`invalid`、`descending`、`duplicates`、`unique`。

只有 `invalid=0`、`descending=0`、`duplicates=0` 时，才判定格式兼容现有代码。

### 3. 对比上一版

优先与用户上一次确认的清单对比。没有明确上一版或上一版文件不存在时，只做当前文件检查，并明确说明未做版本差异对比。

两个文件都已按 IPv4 数值排序时，使用双文件顺序归并，统计：

- `common`：两版共同 IP；
- `added`：新版新增 IP；
- `removed`：新版删除 IP；
- 各输出最多5个新增和删除样例。

不要直接使用 `comm`，因为文件是 IPv4 数值顺序，不是普通字符串字典序。不要通过 `sort` 复制大型临时文件，也不要把数百万 IP 全部装入 AWK/Lua 哈希表。

校验关系：`common + added = 新版总数`，`common + removed = 旧版总数`。

当 `removed > 0` 时必须醒目标明“不是纯增量”，并建议用户确认业务是否允许解除这些旧 IP 的封禁。

### 4. LuaJIT 实际加载验证

使用项目实际 LuaJIT，按 `pre_check.lua` 的现有算法完整加载新文件：

- 解析每条 IPv4 为 `uint32_t`；
- 每块保存 65,536 条；
- 拒绝非法或降序数据；
- 二分查找首条、中间条、末条；
- 验证一个不存在 IP 和一个非法字符串不命中；
- 如果版本对比存在删除项，再验证一个已删除样例不命中。

用 `/usr/bin/time -f 'elapsed=%e max_rss_kb=%M'` 记录加载耗时与测试进程峰值 RSS。优先使用 `command -v luajit` 找到 LuaJIT；找不到时检查 OpenResty 自带 LuaJIT。遵守当前环境关于执行本地脚本和沙箱授权的规定。

内存指标分别报告：

- 常驻 IP 数组估算：`ceil(IP数量 / 65536) * 65536 * 4` 字节；
- 测试进程峰值 RSS：以 `/usr/bin/time` 实测为准。

不要把峰值 RSS 误写成 IP 数组的单独占用。总服务内存可粗略按“每 worker 常驻 IP 数组 × worker 数量”估算，OpenResty 自身内存另计。

### 5. 给出结论

结论先说明“可以直接使用”或“不可以直接使用”，然后简洁列出：

- 文件大小与 IP 数量；
- 合法性、排序、重复检查结果；
- 相对上一版的保留、新增、删除和净变化；
- LuaJIT 加载耗时、分块数、常驻数组大小和峰值 RSS；
- 是否需要业务确认删除项；
- 部署时需放置并命名为 `/data/all.ip.txt`。

格式、排序或实际加载任一失败时，不要建议部署，需准确指出失败原因。

### 6. 更新历史记录文件

新清单完成全量校验、版本对比和 LuaJIT 验证后，更新 `ip_update_history.md`：

1. 将累计更新次数加1；
2. 追加新版本的日期、实际路径、数量、大小、增删数、常驻数据、耗时和峰值 RSS；
3. 将“当前对比基线”改为本次新文件；
4. 保留已有历史行，不覆盖旧数据；
5. 只更新 `ip_update_history.md`，不要修改本 `SKILL.md`，也不要因此修改或提交项目源码。

## 阶段三：上传、reload 与验收

### 发布配置

- 跳板机：`ssh root@10.63.5.53 -p 443`。
- 目标 Pod：通过 Paas appunit details 接口获取 Ready 且容器全 ready 的 Pod IP，通常共 10 个。
- 远端临时文件：跳板机 `/tmp/all.ip.txt`。
- 远端最终文件：`/data/all.ip.txt`，代码固定读取此路径。
- 代码文件：`/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua`。
- 本地新版代码：`~/ai/brain/skills/hk_flow_control/luna-rule/vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua`。
- reload 命令：`/opt/soft/nginx/sbin/nginx -s reload`。
- 测试请求：使用 Nobug `http://nobug.qiyi.domain/` 的 Dash 请求分析页对固定测试 URL 重新签名。
- 测试请求头：同时带 `X-Real-IP: <命中IP>` 和 `X-Forwarded-For: <命中IP>`；只带 `X-Real-IP` 可能不会进入 `request.ip` 判断。
- 验收命中 IP：优先取本次清单第一条，例如 `awk 'NR==1 {print; exit}' <候选文件>`。

### 1. 重新获取目标 Pod IP

每次发布前都通过接口重新获取 Pod IP，不复用旧列表。接口会从 old/new replicasets 中筛选：

- `deletion_timestamp == null`；
- 所有 container `ready == true`；
- Pod `Ready` condition 为 `True`。

命令：

```bash
PAAS_TOKEN='9a6511b42e214ecabf92596bb8ba30ee'

curl -sS \
  'http://paas.cloud.qiyi.domain/api/v1/apps/4454/appunits/15594890/details' \
  -H "token: ${PAAS_TOKEN}" |
jq -r '
  .data.deployments[] |
  (
    (.old_replicasets[]?.pods[]?),
    (.new_replicasets?.pods[]?)
  ) |
  select(.deletion_timestamp == null) |
  select([.containers[]?.ready] | all) |
  select(any(.status.conditions[]?;
    .type == "Ready" and .status == "True"
  )) |
  .ip
' | sort -u
```

结果大于 3 个 Pod IP 即可继续；小于等于 3 个时停止并检查 appunit、接口 token、当前发布状态和筛选条件。

### 2. 上传清单文件

确认阶段二已经通过，记录本地候选文件的行数和 MD5：

```bash
wc -l "$CANDIDATE"
md5sum "$CANDIDATE"
```

大文件先 gzip 压缩再传输；IP 纯文本压缩率高，可减少本机到跳板机、跳板机到 Pod 的传输耗时。门禁使用**解压后的原始文件 MD5**，不是 `.gz` 文件 MD5。

```bash
orig_md5=$(md5sum "$CANDIDATE" | awk '{print $1}')
gzip -c "$CANDIDATE" > /tmp/all.ip.txt.gz
gzip -t /tmp/all.ip.txt.gz

rsync -av --inplace \
  -e "ssh -p 443 -o BatchMode=yes -o ConnectTimeout=10" \
  /tmp/all.ip.txt.gz root@10.63.5.53:/tmp/all.ip.txt.gz

ssh -p 443 root@10.63.5.53 \
  "gzip -t /tmp/all.ip.txt.gz && gzip -dc /tmp/all.ip.txt.gz | md5sum"
```

上面 `gzip -dc ... | md5sum` 的值必须等于 `orig_md5`。

从跳板机分发压缩包到 Pod，在 Pod 端解压为临时文件，校验解压后 MD5 后再替换 `/data/all.ip.txt`：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

src=/tmp/all.ip.txt.gz
dest=/data/all.ip.txt
tmp_dest=/data/all.ip.txt.tmp
expect_md5=<本地候选文件MD5>
ips=(<接口获取的10个Pod IP>)

ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
scp_opts=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

fail=0
for ip in "${ips[@]}"; do
  echo "== ${ip} =="
  ts=$(date +%Y%m%d%H%M%S)
  data_backup=${dest}.bak.${ts}
  ssh "${ssh_opts[@]}" "root@${ip}" "test ! -f '${dest}' || cp -p '${dest}' '${data_backup}'" || { echo "FAILED backup ${ip}"; fail=1; continue; }
  scp "${scp_opts[@]}" "${src}" "root@${ip}:/tmp/all.ip.txt.gz" || { echo "FAILED upload ${ip}"; fail=1; continue; }
  actual=$(ssh "${ssh_opts[@]}" "root@${ip}" "
    gzip -t /tmp/all.ip.txt.gz &&
    gzip -dc /tmp/all.ip.txt.gz > '${tmp_dest}' &&
    md5sum '${tmp_dest}' | awk '{print \\\$1}'
  ")
  if [ "${actual}" = "${expect_md5}" ]; then
    ssh "${ssh_opts[@]}" "root@${ip}" "mv '${tmp_dest}' '${dest}' && rm -f /tmp/all.ip.txt.gz"
    echo "OK ${ip} md5=${actual} backup=${data_backup}"
  else
    echo "FAILED md5 ${ip} actual=${actual}"
    fail=1
  fi
done
exit ${fail}
EOF
```

### 3. 新 Pod 必须确认代码版本

滚动后出现过新 Pod 只带旧版 `pre_check.lua` 的情况：`/data/all.ip.txt` 已上传成功，但请求仍返回 `A00000`。因此上传清单后至少抽查 1 台：

```bash
ssh -p 443 root@10.63.5.53 \
  'ssh root@<pod_ip> "md5sum /opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua /data/all.ip.txt"'
```

`pre_check.lua` 应为当前实现 MD5（截至记录时为 `9fddc537ccb9760c5a78314670cede42`）。如果目标 Pod 是旧版本，先分发新版代码：

```bash
scp -P 443 "$HOME/ai/brain/skills/hk_flow_control/luna-rule/vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua" \
  root@10.63.5.53:/tmp/pre_check.lua

ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

src=/tmp/pre_check.lua
dest=/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua
expect_md5=<本地pre_check.lua的MD5>
ips=(<接口获取的10个Pod IP>)

ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
scp_opts=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

fail=0
for ip in "${ips[@]}"; do
  ts=$(date +%Y%m%d%H%M%S)
  ssh "${ssh_opts[@]}" "root@${ip}" "cp -p '${dest}' '${dest}.bak.${ts}'" || { echo "FAILED backup ${ip}"; fail=1; continue; }
  scp "${scp_opts[@]}" "${src}" "root@${ip}:${dest}" || { echo "FAILED upload ${ip}"; fail=1; continue; }
  actual=$(ssh "${ssh_opts[@]}" "root@${ip}" "md5sum '${dest}' | awk '{print \$1}'")
  [ "${actual}" = "${expect_md5}" ] && echo "OK ${ip} md5=${actual} backup=${dest}.bak.${ts}" || { echo "FAILED md5 ${ip} actual=${actual}"; fail=1; }
done
exit ${fail}
EOF
```

### 4. 先灰度 1 台并自动回滚

不要一开始就 reload 全部 Pod。发布时先选接口返回列表的第 1 台作为 canary，只对这 1 台执行：

1. 备份 `/data/all.ip.txt` 为 `/data/all.ip.txt.bak.{ts}`；
2. 覆盖新 `/data/all.ip.txt`；
3. 如 `pre_check.lua` 不是当前实现，备份并覆盖新版代码；
4. reload；
5. 用 Nobug 新签名 URL 验收；
6. 检查错误日志是否有明显异常。

canary 通过后，才按同样步骤更新剩余 Pod。可以先把压缩包放到跳板机，但不要对全部 Pod 同时 reload。

canary 错误日志检查两个文件：`/opt/soft/nginx/logs/error.log` 和 `/opt/soft/nginx/logs/block_access.log`。检查命令：

```bash
ssh -p 443 root@10.63.5.53 \
  'ssh root@<canary_ip> "awk '\''/oversea abuse|invalid or unordered|failed to open|runtime error|not enough memory|lua entry thread aborted|stack traceback/ {print}'\'' /opt/soft/nginx/logs/error.log /opt/soft/nginx/logs/block_access.log"'
```

验收通过条件：

- curl 返回 `A00404 / This ip is blocked.`；
- `/opt/soft/nginx/logs/error.log` 和 `/opt/soft/nginx/logs/block_access.log` 没有明显新增的大量 Lua 运行错误、文件加载失败、乱序/非法 IP、内存错误或 worker 异常；
- nginx reload 命令退出码为 0。

如果 canary 不通过，立即回滚 canary 上一个版本的清单和代码，然后 reload：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

ip=<canary_ip>
data_backup=<canary上/data/all.ip.txt.bak.{ts}>
code_backup=<canary上pre_check.lua.bak.{ts}>
data_dest=/data/all.ip.txt
code_dest=/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua
ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

ssh "${ssh_opts[@]}" "root@${ip}" "
  test -f '${data_backup}' &&
  cp -p '${data_backup}' '${data_dest}' &&
  { test ! -f '${code_backup}' || cp -p '${code_backup}' '${code_dest}'; } &&
  /opt/soft/nginx/sbin/nginx -s reload
"
EOF
```

回滚完成后停止发布，不要继续更新剩余 Pod。输出失败原因、canary IP、已回滚的备份文件路径和 reload 结果。

### 5. reload

覆盖清单后必须 reload，因为代码按 worker 懒加载并缓存 `/data/all.ip.txt`。逐台执行：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

ips=(<接口获取的10个Pod IP>)
ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

fail=0
for ip in "${ips[@]}"; do
  if ssh "${ssh_opts[@]}" "root@${ip}" "/opt/soft/nginx/sbin/nginx -s reload >/tmp/pre_check_reload.log 2>&1"; then
    echo "OK ${ip} reload=ok"
  else
    echo "FAILED ${ip} reload"
    ssh "${ssh_opts[@]}" "root@${ip}" "awk '{print}' /tmp/pre_check_reload.log"
    fail=1
  fi
done
exit ${fail}
EOF
```

reload 后等待约 5 秒再测试，避免旧 worker 短暂处理请求。canary 阶段只对 canary 执行；canary 通过后再对剩余 Pod 执行。

### 6. Nobug 重新签名并验收

优先直接调用 Nobug 签名接口，避免依赖 9222 浏览器：

```http
POST http://nobug.qiyi.domain/api/url/sign
Content-Type: application/json;charset=UTF-8
Accept: application/json
```

请求体：

```json
{
  "url": "<不带host的/dash路径；更新tm；移除vf参数>",
  "src": "01080031010000000000",
  "v": "a1",
  "service": "dash"
}
```

响应示例：

```json
{"message":"SUCCESS","data":"baaa6c884c1e9a4aff68005b1fc3262d","code":"A00000"}
```

其中 `data` 就是新的 `vf`。将它追加回路径：`<path>&vf=<data>`，再加上 host 得到验收 URL。不要手动只改 `tm` 而复用旧 `vf`，否则会返回 `A00001`；过期 URL 会返回 `A00020`。

可用 Python 直接生成签名 URL：

```python
import json
import time
import urllib.parse
import urllib.request

raw_url = "http://cache.video.iqiyi.com/dash?..."
u = urllib.parse.urlsplit(raw_url)
params = urllib.parse.parse_qsl(u.query, keep_blank_values=True)
params = [(k, v) for k, v in params if k != "vf"]
params = [(k, str(int(time.time() * 1000)) if k == "tm" else v) for k, v in params]
path = u.path + "?" + urllib.parse.urlencode(params)

payload = {
    "url": path,
    "src": "01080031010000000000",
    "v": "a1",
    "service": "dash",
}
req = urllib.request.Request(
    "http://nobug.qiyi.domain/api/url/sign",
    data=json.dumps(payload).encode(),
    headers={"accept": "application/json", "content-type": "application/json;charset=UTF-8"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=10) as resp:
    vf = json.loads(resp.read().decode())["data"]

signed_url = urllib.parse.urlunsplit((u.scheme, u.netloc, u.path, urllib.parse.urlencode(params + [("vf", vf)]), ""))
print(signed_url)
```

浏览器兜底方式：进入 `http://nobug.qiyi.domain/` 的 Dash 请求分析页，将上一条测试 URL 填入“原始URL”，读取“已签名的URL”。页面会更新 `tm` 和 `vf`。

固定测试 URL 的业务参数保持不变，使用 Nobug 输出的最新签名 URL。基础 URL 如下，`tm` 和 `vf` 可以是旧值，必须通过 Nobug 重新签名后再用于验收：

```text
http://cache.video.iqiyi.com/dash?tvid=4953875465368300&bid=500&vid=&src=01080031010000000000&vt=0&rs=1&uid=&ori=pcw&ps=0&k_uid=883b18781a6a5485b1f91a2db28bc00f&pt=0&d=0&s=&lid=&cf=0&ct=0&authKey=26fb407c5629ff645156d93e5ce407d8&k_tag=1&dfp=a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873&locale=zh_cn&up=&qd_v=a1&tm=1785753449279&ppt=0&k_ft1=704237197590532&k_ft4=1170017878024196&k_ft5=17592337039361&k_ft7=26422940794880&k_ftx2=g&fr_300=120_120_120_120_120_120&fr_500=120_120_120_120_120_120&fr_600=120_120_120_120_120_120&fr_800=120_120_120_120_120_120&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873%22%2C%22b_ft1%22%3A28%7D&sr=1&ost=0&ut=0&vf=a8f7a22d6c57a8d69e78e14aeb7df011
```

测试时命中 IP 取本次清单第一条，并同时带两个请求头：

```bash
curl -sS --max-time 60 \
  --resolve 'cache.video.iqiyi.com:80:127.0.0.1' \
  -H "X-Real-IP: ${hit_ip}" \
  -H "X-Forwarded-For: ${hit_ip}" \
  "${signed_url}"
```

从跳板机批量验收：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

hit_ip=<本次清单第一条IP>
signed_url='<Nobug输出的已签名URL>'
ips=(<接口获取的10个Pod IP>)
ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

fail=0
for ip in "${ips[@]}"; do
  resp=$(ssh "${ssh_opts[@]}" "root@${ip}" \
    "curl -sS --max-time 60 --resolve 'cache.video.iqiyi.com:80:127.0.0.1' -H 'X-Real-IP: ${hit_ip}' -H 'X-Forwarded-For: ${hit_ip}' '${signed_url}'")

  if [[ "${resp}" == *'"code":"A00404"'* && "${resp}" == *'This ip is blocked.'* ]]; then
    echo "OK ${ip} A00404"
  else
    code=$(printf '%s' "${resp}" | awk 'match($0, /"code":"[^"]+"/) {print substr($0, RSTART, RLENGTH); exit}')
    msg=$(printf '%s' "${resp}" | awk 'match($0, /"msg":"[^"]+"/) {print substr($0, RSTART, RLENGTH); exit}')
    echo "FAILED ${ip} ${code} ${msg}"
    fail=1
  fi
done
exit ${fail}
EOF
```

验收通过标准：10 台全部输出 `OK <pod_ip> A00404`。常见失败含义：

- `A00020 / Time expired`：签名 URL 过期，回 Nobug 重新签名。
- `A00001 / This sign is not correct.`：手动改了 `tm` 或参数导致签名不匹配，回 Nobug 重新签名。
- `A00000`：通常是目标 Pod 的 `pre_check.lua` 仍为旧版本，或没有 reload 到新 worker；先查代码 MD5，再覆盖代码并 reload。

### 发布门禁

以下任一情况出现时不得继续或必须回滚：

- 文件检查失败，或 LuaJIT 无法完整加载；
- 存在删除 IP 但未取得业务确认；
- 本地与远端大小、行数或校验和不一致；
- reload 失败；
- reload 后出现加载失败、worker 异常、错误率或延迟明显上升；
- 10 台验收未全部返回 `A00404`。

### 输出格式

完成后简要输出：

- 本次接口获取的 10 个 Pod IP；
- 本地文件路径、行数、大小和 MD5；
- `/data/all.ip.txt` 远端校验是否全部一致；
- 是否同步过 `pre_check.lua` 及其 MD5；
- reload 结果；
- 测试 IP 和 10 台 `A00404` 验收结论。

## 按指定 src + 登录凭证条件叠加 Nginx 限流

在 IP 清单封禁之外，可对 `/dash` 再叠加 Nginx `limit_req`：指定 `src` 只有在请求同时携带非空 `uid` 和 authcookie 时才豁免；`uid` 为空、仅伪造非空 `uid`，或只有 authcookie 没有 `uid` 时均参与限流。其他 `src` 不受该 zone 影响。

Dash 的 authcookie 可能来自查询参数 `pck`、请求头 `pck`、Cookie `P00001` 或 Cookie `I00001`，条件必须覆盖这四个入口。这里判断的是凭证是否存在，不校验凭证真伪；如果黑产进一步同时伪造 `uid` 和任意非空 `pck`，需要把限流下沉到 authcookie 服务端校验之后，不能只靠 Nginx `map`。

### 原理

1. 分别用 `map` 判断 `uid` 是否非空、四种 authcookie 入口是否至少一个非空，再组合成完整登录参数形态。
2. 用最后一个 `map` 把“指定 `src` + 非完整登录参数形态”编码成限流 key：命中时赋非空值，未命中时 `default ""`。
3. `limit_req_zone` 使用该变量；**key 为空字符串时该 zone 不计次、不限流**。
4. 在 `location = /dash` 里叠加 `limit_req`；可与原有全局限流（如 `porsche_zone`）同时存在，需全部通过。
5. zone 使用共享内存，**限流速率是整机所有 worker 合计**，不是每 worker 各一份。

### 配置模板

配置文件：`play-nginx` 的 `conf/vh.cache.video.qiyi.com.conf`（`http` 上下文可写 `map` / `limit_req_zone`）。

本机参考路径：`~/lua/projects/play-nginx/conf/vh.cache.video.qiyi.com.conf`（绝对路径：`/home/fan/lua/projects/play-nginx/conf/vh.cache.video.qiyi.com.conf`）。

```nginx
# http 上下文：uid + authcookie 存在性、条件键和 zone
map $arg_uid $dash_uid_present {
    default 1;
    "" 0;
}

map "$arg_pck:$http_pck:$cookie_P00001:$cookie_I00001" $dash_authcookie_present {
    default 1;
    ":::" 0;
}

map "$dash_uid_present:$dash_authcookie_present" $dash_complete_login_shape {
    default 0;
    "1:1" 1;
}

map "$arg_src:$dash_complete_login_shape" $dash_src_incomplete_login_key {
    default "";
    "01080031010000000000:0" "1";
}
limit_req_zone $dash_src_incomplete_login_key zone=dash_src_incomplete_login_zone:1m rate=2r/s;

# location = /dash
limit_req_status 513;
limit_req zone=dash_src_incomplete_login_zone burst=2 nodelay;
limit_req zone=porsche_zone burst=100 nodelay;   # 原有全局限流可保留
```

### 调整说明

| 项 | 说明 |
|---|---|
| 匹配条件 | 改最后一个 `map` 左侧的 `"<src>:0"`；只有 uid 和 authcookie 均非空时才豁免 |
| QPS | 改 `rate=`，如 `2r/s` |
| 突发 | `burst`；要更严可直接省略 `burst`，其默认值为 0 |
| 超限状态码 | `limit_req_status`（当前 `/dash` 为 `513`） |
| 多条件 | 在最后一个 `map` 中继续追加 `"<src>:0" "1";` 等条目，共用同一 zone |

### 注意

- `map` / `limit_req_zone` 必须放在 `http` 块（或被 include 进 `http` 的文件顶部），不能只写在 `server`/`location` 里。
- 改完后需 `nginx -t` 再 `reload`。
- 这是 Nginx 层 QPS 限流，与 Lua `pre_check.lua` 的 IP 清单封禁相互独立，可叠加。

### 限流生效验证

#### 1. 配置与 reload 检查

在目标 Pod 上先确认规则只出现一次、配置语法正确，再 reload：

```bash
cfg=/opt/soft/nginx/conf/vh.cache.video.qiyi.com.conf

grep -nE 'dash_(uid_present|authcookie_present|complete_login_shape|src_incomplete_login|src_incomplete_login_zone)' "$cfg"
/opt/soft/nginx/sbin/nginx -t
/opt/soft/nginx/sbin/nginx -s reload
```

reload 后等待约 5 秒，避免旧 worker 短暂处理请求。多台发布时应记录并对比配置文件 MD5，保证所有 Pod 配置一致。

#### 2. 不要只看 HTTP 状态码

当前 Dash 服务会把 Nginx 内部的 `513` 包装成 HTTP `200` 业务响应。因此，`curl -w '%{http_code}'` 看到 `200` 不能判定未限流，必须检查响应体。实测命中限流时响应为：

```json
{"msg":["513"],"data":{"st":1513},"code":"A00003"}
```

验收时以响应体同时包含以下特征作为限流命中依据：

- `"code":"A00003"`
- `"st":1513`
- `"msg":["513"]`

#### 3. 使用并发请求验证匹配条件

不要只发顺序请求：如果请求间隔足以让漏桶恢复，连续顺序请求可能全部通过。应使用少量并发请求验证，例如在目标 Pod 内通过回环地址发 4 个并发请求：

```bash
tmp_dir=$(mktemp -d)

for n in 1 2 3 4; do
  curl -sS --max-time 15 \
    --resolve 'cache.video.iqiyi.com:80:127.0.0.1' \
    "http://cache.video.iqiyi.com/dash?src=01080031010000000000&uid=forged_uid&verify=${n}" \
    >"${tmp_dir}/${n}" &
done
wait

grep -l '"st":1513' "${tmp_dir}"/* | wc -l
rm -rf "$tmp_dir"
```

按模板的 `2r/s`、`burst=2` 配置，4 个真正同时到达的匹配请求通常至少 1 个应命中 `st=1513`；如果线上已有相同条件的流量占用该 zone，也可能更多或全部命中。

#### 4. 完整条件矩阵

每台 Pod 至少验证以下请求，避免条件写宽导致误伤：

| 场景 | 查询参数示例 | 预期 |
|---|---|---|
| 指定 src，`uid=` | `src=01080031010000000000&uid=` | 并发超额请求出现 `st=1513` |
| 指定 src，未传 uid | `src=01080031010000000000` | 并发超额请求出现 `st=1513` |
| 指定 src，伪造 uid、无 authcookie | `src=01080031010000000000&uid=forged_uid` | 并发超额请求出现 `st=1513` |
| 指定 src，uid 非空、查询参数 pck 非空 | `src=01080031010000000000&uid=logged_in&pck=<有效值>` | 不得因该 zone 出现 `st=1513` |
| 指定 src，uid 非空、pck 请求头非空 | 查询参数带非空 uid，请求头带 `pck: <有效值>` | 不得因该 zone 出现 `st=1513` |
| 指定 src，uid 非空、登录 Cookie 非空 | 查询参数带非空 uid，Cookie 带 `P00001` 或 `I00001` | 不得因该 zone 出现 `st=1513` |
| 指定 src，uid 为空、authcookie 非空 | `src=01080031010000000000&uid=&pck=<值>` | 并发超额请求出现 `st=1513` |
| 其他 src，uid 为空 | `src=other&uid=` | 不得因该 zone 出现 `st=1513` |

非匹配请求可以因缺少 Dash 必需参数返回其他业务错误码；只要没有该限流对应的 `st=1513`，即可证明没有被这个 zone 拒绝。

#### 5. 日志检查

验收后检查 Nginx 错误日志和业务阻断日志，确认没有 reload、Lua、内存或 worker 异常：

```bash
tail -n 1000 \
  /opt/soft/nginx/logs/error.log \
  /opt/soft/nginx/logs/block_access.log 2>/dev/null |
awk '/invalid or unordered|failed to open|runtime error|not enough memory|lua entry thread aborted|stack traceback/ {print}'
```

单机灰度通过后才扩到剩余 Pod；全量发布后逐台重复配置 MD5、`nginx -t`、匹配条件、非匹配条件和异常日志检查。
