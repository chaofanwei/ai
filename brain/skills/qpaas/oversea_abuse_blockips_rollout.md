# QPaas 海外黑产 IP 封禁临时变更流程

记录时间：2026-07-31

适用场景：临时更新 dash nginx Pod 上的 `/data/blockips` 与 `pre_check.lua`，reload nginx 后验证海外黑产 IP 封禁是否生效。

## 目标环境

QPaas 页面：

`vrs-dash-qpaas / UNIT2-INTER / dash-u2-inter`

跳板机：

```bash
ssh root@10.63.5.53 -p 443
```

Pod IP 列表：

```text
10.134.58.213
10.132.169.52
10.132.161.99
10.132.255.101
10.132.172.163
10.132.143.139
10.132.145.235
10.132.172.164
10.132.148.210
10.132.161.108
```

## 本地文件

```bash
BLOCKIPS="$HOME/Downloads/blockips"
PRE_CHECK="$HOME/lua/projects/luna-rule-2/luna-rule/vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua"
```

远端目标：

```bash
/data/blockips
/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua
```

nginx reload：

```bash
/opt/soft/nginx/sbin/nginx -s reload
```

## 浏览器获取 Pod IP

1. 启动 9222 浏览器：

```bash
~/shells/start-ai-chrome.sh
```

2. 打开 QPaas 工作负载页面后，用 Playwright MCP 或页面 DOM 文本提取 `Pod IP / 节点IP`。
3. 每行取 `/` 前面的 IP，例如：

```text
Pod IP / 节点IP：10.134.58.213 / 10.132.233.17
```

取 `10.134.58.213`。

## 上传 blockips

先传到跳板机：

```bash
scp -P 443 "$HOME/Downloads/blockips" root@10.63.5.53:/tmp/blockips
```

再从跳板机分发到 Pod：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

ips=(
  10.134.58.213
  10.132.169.52
  10.132.161.99
  10.132.255.101
  10.132.172.163
  10.132.143.139
  10.132.145.235
  10.132.172.164
  10.132.148.210
  10.132.161.108
)

for ip in "${ips[@]}"; do
  echo "== ${ip} =="
  scp -o BatchMode=yes -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
    /tmp/blockips "root@${ip}:/data/blockips"
  ssh -n -o BatchMode=yes -o ConnectTimeout=10 \
    -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR \
    "root@${ip}" 'ls -l /data/blockips'
done
EOF
```

## 上传 pre_check.lua

先传到跳板机：

```bash
scp -P 443 "$HOME/lua/projects/luna-rule-2/luna-rule/vis-rule-engine/src/main/lua/p911/rules/pre/pre_check.lua" \
  root@10.63.5.53:/tmp/pre_check.lua
```

批量覆盖、备份、校验、reload：

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

src=/tmp/pre_check.lua
dest=/opt/soft/nginx/conf/lua/p911/rules/pre/pre_check.lua
dest_dir=/opt/soft/nginx/conf/lua/p911/rules/pre
expect_md5=$(md5sum "${src}" | awk '{print $1}')

ips=(
  10.134.58.213
  10.132.169.52
  10.132.161.99
  10.132.255.101
  10.132.172.163
  10.132.143.139
  10.132.145.235
  10.132.172.164
  10.132.148.210
  10.132.161.108
)

ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)
scp_opts=(-o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

for ip in "${ips[@]}"; do
  echo "== ${ip} =="
  ts=$(date +%Y%m%d%H%M%S)

  ssh "${ssh_opts[@]}" "root@${ip}" \
    "test -d '${dest_dir}' && cp -p '${dest}' '${dest}.bak.${ts}'"

  scp "${scp_opts[@]}" "${src}" "root@${ip}:${dest}"

  actual=$(ssh "${ssh_opts[@]}" "root@${ip}" \
    "md5sum '${dest}' | awk '{print \$1}'")

  if [ "${actual}" != "${expect_md5}" ]; then
    echo "FAILED md5 ${ip} actual=${actual} expect=${expect_md5}"
    continue
  fi

  ssh "${ssh_opts[@]}" "root@${ip}" \
    "/opt/soft/nginx/sbin/nginx -s reload >/tmp/pre_check_reload.log 2>&1"

  echo "OK ${ip} md5=${actual} backup=${dest}.bak.${ts}"
done
EOF
```

注意：跳板机脚本里的内层 `ssh` 必须加 `-n`，否则内层 `ssh` 会消费外层 heredoc 的 stdin，导致后续 `scp` 或校验命令不执行。

## 测试请求

测试 IP 使用 `blockips` 中命中的网段：

```text
14.191.68.1
```

测试路径：

```text
/dash?tvid=4953875465368300&bid=500&vid=&src=01080031010000000000&vt=0&rs=1&uid=&ori=pcw&ps=0&k_uid=883b18781a6a5485b1f91a2db28bc00f&pt=0&d=0&s=&lid=&cf=0&ct=0&authKey=26fb407c5629ff645156d93e5ce407d8&k_tag=1&dfp=a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873&locale=zh_cn&up=&qd_v=a1&tm=1785484576566&ppt=0&k_ft1=704237197590532&k_ft4=1170017878024196&k_ft5=17592337039361&k_ft7=26422940794880&k_ftx2=g&fr_300=120_120_120_120_120_120&fr_500=120_120_120_120_120_120&fr_600=120_120_120_120_120_120&fr_800=120_120_120_120_120_120&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873%22%2C%22b_ft1%22%3A28%7D&sr=1&ost=0&ut=0&vf=3a34f78f0f8e8640695ba1c95cfaa3f9
```

单机测试命令：

```bash
curl -sS -i --max-time 15 \
  --resolve 'cache.video.iqiyi.com:80:127.0.0.1' \
  -H 'X-Real-IP: 14.191.68.1' \
  -H 'X-Forwarded-For: 14.191.68.1' \
  'http://cache.video.iqiyi.com/dash?tvid=4953875465368300&bid=500&vid=&src=01080031010000000000&vt=0&rs=1&uid=&ori=pcw&ps=0&k_uid=883b18781a6a5485b1f91a2db28bc00f&pt=0&d=0&s=&lid=&cf=0&ct=0&authKey=26fb407c5629ff645156d93e5ce407d8&k_tag=1&dfp=a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873&locale=zh_cn&up=&qd_v=a1&tm=1785484576566&ppt=0&k_ft1=704237197590532&k_ft4=1170017878024196&k_ft5=17592337039361&k_ft7=26422940794880&k_ftx2=g&fr_300=120_120_120_120_120_120&fr_500=120_120_120_120_120_120&fr_600=120_120_120_120_120_120&fr_800=120_120_120_120_120_120&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873%22%2C%22b_ft1%22%3A28%7D&sr=1&ost=0&ut=0&vf=3a34f78f0f8e8640695ba1c95cfaa3f9'
```

预期返回：

```json
{"msg":"This ip is blocked.","code":"A00404"}
```

## 批量测试

```bash
ssh -p 443 root@10.63.5.53 'bash -s' <<'EOF'
set -u
unset LC_ALL LANG LANGUAGE

path='/dash?tvid=4953875465368300&bid=500&vid=&src=01080031010000000000&vt=0&rs=1&uid=&ori=pcw&ps=0&k_uid=883b18781a6a5485b1f91a2db28bc00f&pt=0&d=0&s=&lid=&cf=0&ct=0&authKey=26fb407c5629ff645156d93e5ce407d8&k_tag=1&dfp=a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873&locale=zh_cn&up=&qd_v=a1&tm=1785484576566&ppt=0&k_ft1=704237197590532&k_ft4=1170017878024196&k_ft5=17592337039361&k_ft7=26422940794880&k_ftx2=g&fr_300=120_120_120_120_120_120&fr_500=120_120_120_120_120_120&fr_600=120_120_120_120_120_120&fr_800=120_120_120_120_120_120&bop=%7B%22version%22%3A%2210.0%22%2C%22dfp%22%3A%22a12beefd473bb0112b425ac0b100701b8e1a5dd3c173ce42fca5f13344f46db873%22%2C%22b_ft1%22%3A28%7D&sr=1&ost=0&ut=0&vf=3a34f78f0f8e8640695ba1c95cfaa3f9'
ips=(10.134.58.213 10.132.169.52 10.132.161.99 10.132.255.101 10.132.172.163 10.132.143.139 10.132.145.235 10.132.172.164 10.132.148.210 10.132.161.108)
ssh_opts=(-n -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR)

fail=0
for ip in "${ips[@]}"; do
  resp=$(ssh "${ssh_opts[@]}" "root@${ip}" \
    "curl -sS --max-time 15 --resolve 'cache.video.iqiyi.com:80:127.0.0.1' -H 'X-Real-IP: 14.191.68.1' -H 'X-Forwarded-For: 14.191.68.1' 'http://cache.video.iqiyi.com${path}'")

  if [[ "${resp}" == *'"code":"A00404"'* && "${resp}" == *'This ip is blocked.'* ]]; then
    echo "OK ${ip} A00404"
  else
    code=$(printf '%s' "${resp}" | awk 'match($0, /"code":"[^"]+"/) {print substr($0, RSTART, RLENGTH); exit}')
    echo "FAILED ${ip} ${code}"
    fail=1
  fi
done
exit ${fail}
EOF
```

## 注意事项

- 只带 `X-Real-IP` 时曾返回 `A00000`；同时带 `X-Forwarded-For` 后返回 `A00404`。测试时两个头都带上。
- reload 后立刻测试可能仍命中旧 worker，短暂返回 `A00000`；等待几秒后重测即可。
- 跳板机 SSH 版本不支持 `StrictHostKeyChecking=accept-new`，用 `StrictHostKeyChecking=no`。
- 覆盖 `pre_check.lua` 前保留同目录备份：`pre_check.lua.bak.{YYYYMMDDHHMMSS}`。
- 本次最终验证 10 台均返回 `A00404`。
