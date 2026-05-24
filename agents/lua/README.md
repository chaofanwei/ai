# 本地 OpenResty 开发环境

这套脚本用于在 macOS / Linux 上快速构建并启动本地 `play-nginx` + `luna-rule` OpenResty 环境。

## 前置目录

默认需要准备这些本地仓库：

```text
~/lua/luna-rule-workspace
~/python/play_ops
```

其中 `~/lua/luna-rule-workspace` 下应包含：

```text
play-nginx/
luna-rule/
```

`~/python/play_ops` 是 git 仓库，脚本会复制它并切到 `dash_ops` 分支。

## 多机器路径配置

脚本会自动识别系统和主机：

- macOS：使用 `scutil --get LocalHostName`
- Linux：使用 `hostname -s`

查看当前识别值：

```bash
uname -s
scutil --get LocalHostName 2>/dev/null || hostname -s
```

当前已内置：

```text
Darwin:weichaofandeMacBook-Air
```

其他 macOS 机器和 Linux 默认使用：

```text
SOURCE_DIR=$HOME/lua/luna-rule-workspace
PLAY_OPS_SOURCE=$HOME/python/play_ops
PYTHON_BIN=$HOME/miniconda3/envs/py310/bin/python
```

如果某台机器目录不同，可以临时用环境变量覆盖：

```bash
SOURCE_DIR=/path/to/luna-rule-workspace \
PLAY_OPS_SOURCE=/path/to/play_ops \
PYTHON_BIN=/path/to/py310/bin/python \
./build-nginx-dev.sh
```

也可以直接在 `build-nginx-dev.sh` 的 `case "$OS_NAME:$HOST_NAME"` 里增加该机器配置。

## 安装依赖

### macOS

```bash
brew install openresty luarocks zlib
```

安装 `lua-zlib` 时要指定 OpenResty 自带 LuaJIT：

```bash
OPENRESTY_VERSION="$(ls /opt/homebrew/Cellar/openresty | tail -1)"
luarocks --lua-version=5.1 \
  --lua-dir="/opt/homebrew/Cellar/openresty/$OPENRESTY_VERSION/luajit" \
  install lua-zlib \
  ZLIB_DIR="$(brew --prefix zlib)"
```

验证：

```bash
/opt/homebrew/Cellar/openresty/$OPENRESTY_VERSION/luajit/bin/luajit -e 'package.cpath = package.cpath .. ";" .. os.getenv("HOME") .. "/.luarocks/lib/lua/5.1/?.so"; local zlib = require "zlib"; print(zlib)'
```

### Linux

需要确保这些命令可用：

```bash
git
openresty
luarocks
```

安装 `lua-zlib` 时同样要按 OpenResty 的 LuaJIT / Lua 5.1 ABI 安装。OpenResty 如果安装在 `/usr/local/openresty`，可参考：

```bash
luarocks --lua-version=5.1 \
  --lua-dir=/usr/local/openresty/luajit \
  install lua-zlib
```

不同 Linux 发行版 OpenResty 路径可能不同，先用下面命令确认：

```bash
command -v openresty
```

### Python 环境

下载 4s 配置数据时默认使用：

```text
~/miniconda3/envs/py310/bin/python
```

确认环境和 `requests` 可用：

```bash
~/miniconda3/envs/py310/bin/python -c 'import requests; print(requests.__version__)'
```

如果缺少：

```bash
~/miniconda3/envs/py310/bin/pip install requests
```

## 构建

默认构建：

```bash
./build-nginx-dev.sh
```

参数：

```bash
./build-nginx-dev.sh <play-nginx分支> <luna-rule分支> <run_profile>
```

示例：

```bash
./build-nginx-dev.sh zyx master bddx-qpaas
./build-nginx-dev.sh xjp master xjp_hw-qpaas
```

默认值：

- `play-nginx` 分支：`zyx`
- `luna-rule` 分支：`master`
- `run_profile`：
  - `play-nginx=xjp` 时默认 `xjp_hw-qpaas`
  - 其他默认 `bddx-qpaas`

构建产物目录：

```text
./nginx-dev
```

构建脚本会自动：

- 复制 `luna-rule-workspace` 到 `./nginx-dev`
- checkout/pull `play-nginx` 和 `luna-rule` 分支
- 把 `luna-rule/vis-rule-engine/src/main/lua` 复制到 `play-nginx/conf/lua`
- 修改生产路径 `/opt/soft/nginx/` 为本地路径
- 修改 OpenResty lualib 路径
- 追加 LuaRocks `~/.luarocks/lib/lua/5.1/?.so`
- 设置 `worker_processes 1`
- 注释掉本地不兼容的 SSL、brotli、cache、unix socket 配置
- mock `ipv6_utils.lua`
- mock `meta_service.lua`，避免本地连接 Cassandra
- patch `openssl_utils.lua`，避免 macOS 加载 `/usr/lib/libcrypto.dylib` 崩溃
- 创建空 IP 数据文件
- 写入 `conf/lua/profile`
- 复制 `play_ops`，切到 `dash_ops`，下载 4s 数据到 `html/4s-data`
- 执行 `openresty -t` 检查配置

## 启动

```bash
./start-openresty.sh
```

启动脚本可以从任意目录执行。默认使用：

```text
./nginx-dev/play-nginx
```

也可以覆盖运行目录：

```bash
PLAY_NGINX_DIR=/path/to/nginx-dev/play-nginx ./start-openresty.sh
```

启动前会先执行：

```bash
pkill nginx || true
```

最后自动执行测试请求：

```bash
curl -H "Host: cache.video.iqiyi.com" "localhost:8080/dash?tvid=100"
```

正常能返回 JSON，例如：

```json
{"msg":"This sign is not correct.","data":{"p":{"mt":0},"ctl":{"num":5,"uip":""}},"code":"A00001"}
```

## 停止

```bash
./stop-openresty.sh
```

也可以覆盖运行目录：

```bash
PLAY_NGINX_DIR=/path/to/nginx-dev/play-nginx ./stop-openresty.sh
```

## 日志

主要日志目录：

```text
./nginx-dev/play-nginx/logs
```

常看文件：

```bash
tail -f ./nginx-dev/play-nginx/logs/error.log
tail -f ./nginx-dev/play-nginx/logs/block_access.log
```

## 常见问题

### module 'cjson' not found

OpenResty 自带 `cjson`，但业务 `init.lua` 会设置 `package.cpath`。构建脚本会自动把 OpenResty lualib 加进去。

### module 'zlib' not found

需要用 LuaRocks 给 OpenResty LuaJIT 安装 `lua-zlib`，并确保 `package.cpath` 包含：

```text
$HOME/.luarocks/lib/lua/5.1/?.so
```

构建脚本会自动追加这个路径。

### module 'resty.cassandra.cluster' not found

本地开发不需要 Cassandra。构建脚本会 mock：

```text
conf/lua/utils/meta_service.lua
```

### worker process exited on signal 6

如果 macOS crash report 里出现：

```text
Invalid dylib load. Clients should not load the unversioned libcrypto dylib
```

说明代码加载了系统的：

```text
/usr/lib/libcrypto.dylib
```

构建脚本会自动检测 Homebrew/OpenResty 的版本化 `libcrypto` 并 patch `openssl_utils.lua`。

### bind() failed: Address already in use

说明已有 nginx/openresty 占用端口。启动脚本已加：

```bash
pkill nginx || true
```

### TCP_FASTOPEN invalid argument

如果看到：

```text
setsockopt(TCP_FASTOPEN, 500) 0.0.0.0:8080 failed, ignored (22: Invalid argument)
```

这是 macOS 对该选项支持问题，OpenResty 会忽略，不影响本地调试。
