#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

function detect_os() {
    uname -s
}

function detect_host() {
    if [ "$(detect_os)" = "Darwin" ] && command -v scutil >/dev/null 2>&1; then
        scutil --get LocalHostName 2>/dev/null || hostname -s
    else
        hostname -s
    fi
}

OS_NAME="$(detect_os)"
HOST_NAME="$(detect_host)"

function sedi() {
    if [ "$OS_NAME" = "Darwin" ]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

function detect_openresty_prefix() {
    if [ -n "$OPENRESTY_PREFIX" ]; then
        echo "$OPENRESTY_PREFIX"
        return
    fi

    if [ "$OS_NAME" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
        brew --prefix openresty 2>/dev/null && return
    fi

    if command -v openresty >/dev/null 2>&1; then
        local bin
        bin="$(realpath "$(command -v openresty)")"
        case "$bin" in
            */openresty/nginx/sbin/openresty|*/openresty/nginx/sbin/nginx)
                dirname "$(dirname "$(dirname "$bin")")"
                return
                ;;
            */openresty/bin/openresty|*/bin/openresty)
                dirname "$(dirname "$bin")"
                return
                ;;
        esac
    fi

    for prefix in /usr/local/openresty /opt/openresty /usr/local; do
        if [ -d "$prefix/lualib" ]; then
            echo "$prefix"
            return
        fi
    done

    echo "Error: cannot find OpenResty prefix" >&2
    exit 1
}

function detect_libcrypto() {
    if [ -n "$OPENSSL_LIBCRYPTO" ] && [ -f "$OPENSSL_LIBCRYPTO" ]; then
        echo "$OPENSSL_LIBCRYPTO"
        return
    fi

    if [ "$OS_NAME" = "Darwin" ]; then
        for lib in \
            /opt/homebrew/opt/openresty-openssl3/lib/libcrypto.3.dylib \
            /usr/local/opt/openresty-openssl3/lib/libcrypto.3.dylib \
            /opt/homebrew/opt/openssl@3/lib/libcrypto.3.dylib \
            /usr/local/opt/openssl@3/lib/libcrypto.3.dylib; do
            if [ -f "$lib" ]; then
                echo "$lib"
                return
            fi
        done
    else
        for lib in \
            /usr/local/openresty/openssl3/lib/libcrypto.so.3 \
            /usr/local/openresty/openssl/lib/libcrypto.so \
            /usr/lib/x86_64-linux-gnu/libcrypto.so.3 \
            /usr/lib64/libcrypto.so.3 \
            /usr/lib/aarch64-linux-gnu/libcrypto.so.3; do
            if [ -f "$lib" ]; then
                echo "$lib"
                return
            fi
        done
    fi

    return 1
}

function checkout_remote_branch() {
    local repo_dir="$1"
    local branch="$2"
    local remote="${3:-origin}"

    cd "$repo_dir"
    git fetch "$remote" "$branch"
    if git show-ref --verify --quiet "refs/remotes/$remote/$branch"; then
        git checkout -B "$branch" "$remote/$branch"
    else
        git checkout "$branch"
    fi
    git pull "$remote" "$branch"
}

# 默认分支
PLAY_NGINX_BRANCH="zyx"
LUNA_RULE_BRANCH="master"
RUN_PROFILE=""
LUNA_ENV_NAME="master"

# 解析参数
if [ $# -ge 1 ]; then
    PLAY_NGINX_BRANCH="$1"
fi
if [ $# -ge 2 ]; then
    LUNA_RULE_BRANCH="$2"
fi
if [ $# -ge 3 ]; then
    RUN_PROFILE="$3"
fi
if [ $# -ge 4 ]; then
    LUNA_ENV_NAME="$4"
fi

# 确定默认的 run_profile
if [ -z "$RUN_PROFILE" ]; then
    if [ "$PLAY_NGINX_BRANCH" = "xjp" ]; then
        RUN_PROFILE="xjp_hw-qpaas"
    else
        RUN_PROFILE="bddx-qpaas"
    fi
fi

case "$OS_NAME:$HOST_NAME" in
    Darwin:weichaofandeMacBook-Air)
        DEFAULT_SOURCE_DIR="/Users/weichaofan/lua/luna-rule-workspace"
        DEFAULT_PLAY_OPS_SOURCE="$HOME/python/play_ops"
        DEFAULT_PYTHON_BIN="$HOME/miniconda3/envs/py310/bin/python"
        ;;
    Darwin:*)
        DEFAULT_SOURCE_DIR="$HOME/lua/luna-rule-workspace"
        DEFAULT_PLAY_OPS_SOURCE="$HOME/python/play_ops"
        DEFAULT_PYTHON_BIN="$HOME/miniconda3/envs/py310/bin/python"
        ;;
    Linux:*)
        DEFAULT_SOURCE_DIR="$HOME/lua/luna-rule-workspace"
        DEFAULT_PLAY_OPS_SOURCE="$HOME/python/projects/play_ops"
        DEFAULT_PYTHON_BIN="$HOME/miniconda3/envs/py310/bin/python"
        ;;
    *)
        echo "Error: unsupported host: $OS_NAME:$HOST_NAME"
        exit 1
        ;;
esac

SOURCE_DIR="${SOURCE_DIR:-$DEFAULT_SOURCE_DIR}"
PLAY_OPS_SOURCE="${PLAY_OPS_SOURCE:-$DEFAULT_PLAY_OPS_SOURCE}"
PYTHON_BIN="${PYTHON_BIN:-$DEFAULT_PYTHON_BIN}"
OPENRESTY_PREFIX="$(detect_openresty_prefix)"
OPENSSL_LIBCRYPTO="$(detect_libcrypto || true)"
WORK_DIR="$SCRIPT_DIR/nginx-dev"
PLAY_NGINX_DIR="$WORK_DIR/play-nginx"
LUNA_RULE_DIR="$WORK_DIR/luna-rule"
PLAY_OPS_DIR="$WORK_DIR/play_ops"
LOGS_DIR="$PLAY_NGINX_DIR/logs"

echo "=========================================="
echo "OS:               $OS_NAME"
echo "Host:             $HOST_NAME"
echo "play-nginx branch: $PLAY_NGINX_BRANCH"
echo "luna-rule branch: $LUNA_RULE_BRANCH"
echo "run profile:      $RUN_PROFILE"
echo "luna env name:    $LUNA_ENV_NAME"
echo "Source:           $SOURCE_DIR"
echo "play_ops source:  $PLAY_OPS_SOURCE"
echo "Python:           $PYTHON_BIN"
echo "OpenResty prefix: $OPENRESTY_PREFIX"
echo "libcrypto:        ${OPENSSL_LIBCRYPTO:-not found}"
echo "Working dir:      $WORK_DIR"
echo "=========================================="

# 1. 清理并创建工作目录
echo "[1/14] Cleaning and creating working directory..."
if [ -d "$WORK_DIR" ]; then
    echo "Removing existing $WORK_DIR..."
    rm -rf "$WORK_DIR"
fi
mkdir -p "$WORK_DIR"

# 2. 复制仓库
echo "[2/14] Copying repository..."
cp -r "$SOURCE_DIR/." "$WORK_DIR/"

# 3. 切换 play-nginx 分支并 pull
echo "[3/14] Switching play-nginx to branch $PLAY_NGINX_BRANCH..."
checkout_remote_branch "$PLAY_NGINX_DIR" "$PLAY_NGINX_BRANCH"

# 4. 切换 luna-rule 分支并 pull
echo "[4/14] Switching luna-rule to branch $LUNA_RULE_BRANCH..."
checkout_remote_branch "$LUNA_RULE_DIR" "$LUNA_RULE_BRANCH"

# 5. 复制 vis-rule-engine/src/main/lua 到 conf/lua 目录
echo "[5/14] Copying lua code to conf/lua directory..."
VIS_LUA_SRC="$LUNA_RULE_DIR/vis-rule-engine/src/main/lua"
CONF_DIR="$PLAY_NGINX_DIR/conf"
LUA_DEST="$CONF_DIR/lua"
if [ ! -d "$VIS_LUA_SRC" ]; then
    echo "Error: $VIS_LUA_SRC not found"
    exit 1
fi
mkdir -p "$LUA_DEST"
cp -r "$VIS_LUA_SRC"/* "$LUA_DEST/"

# 创建 logs 目录
mkdir -p "$LOGS_DIR"

# 6. 修改配置文件
echo "[6/14] Modifying configuration files..."

# 遍历所有 .conf 文件，排除 lua 目录
find "$CONF_DIR" -name "*.conf" -not -path "$CONF_DIR/lua/*" | while read -r conf_file; do
    echo "Processing $conf_file..."

    # 使用临时文件
    temp_file="${conf_file}.tmp"
    cp "$conf_file" "$temp_file"

    # - 注释掉 load_module brotli 模块
    sedi '/ngx_http_brotli_filter_module.so/s/^/#/' "$temp_file"
    sedi '/ngx_http_brotli_static_module.so/s/^/#/' "$temp_file"

    # - 注释掉 user root root;
    sedi '/^[[:space:]]*user/s/^/#/' "$temp_file"

    # - 注释掉 use epoll;
    sedi '/^[[:space:]]*use[[:space:]]/s/^/#/' "$temp_file"

    sedi 's/^[[:space:]]*worker_processes[[:space:]].*/worker_processes 1;/' "$temp_file"

    # - 替换所有 logs/ 开头的相对路径到绝对路径
    sedi "s|logs/|$LOGS_DIR/|g" "$temp_file"

    # - 注释掉所有 brotli* 配置行
    sedi '/^[[:space:]]*brotli/s/^/#/' "$temp_file"

    # - 注释掉 ssl on; (旧语法，新版不支持)
    sedi 's/^.*ssl on;.*/#&/' "$temp_file"

    # - 注释掉 keyless: 开头的 ssl 证书配置(自定义模块)
    sedi 's/^.*keyless:.*/#&/' "$temp_file"

    # - 注释掉所有 ssl_certificate 和 ssl_certificate_key 配置
    sedi '/ssl_certificate/s/^/#/' "$temp_file"
    sedi '/ssl_certificate_key/s/^/#/' "$temp_file"

    # - 注释掉所有 listen 8443/443 和带 ssl 的 listen 行
    sedi '/listen\s*[48]443/s/^/#/' "$temp_file"
    sedi '/listen.*ssl/s/^/#/' "$temp_file"

    # - 注释掉所有 ssl_ 开头的配置
    sedi '/^\s*ssl_/s/^/#/' "$temp_file"

    # - 注释掉 proxy_cache_path 和 proxy_cache (本地没有这些目录)
    sedi '/proxy_cache_path/s/^/#/' "$temp_file"
    sedi '/proxy_cache/s/^/#/' "$temp_file"
    sedi '/proxy_temp_path/s/^/#/' "$temp_file"
    sedi '/unix:/s/^/#/' "$temp_file"

    # - 替换 listen 80 → 8080 (支持 ssl, http2, default_server 等变体)
    sedi 's/\(listen[[:space:]]*\)80\(.*\)/\18080\2/g' "$temp_file"

    # - 替换 listen 443 → 8443
    sedi 's/\(listen[[:space:]]*\)443\(.*\)/\18443\2/g' "$temp_file"

    # - 替换 pid 文件路径
    sedi "s|pid[[:space:]]\+logs/nginx.pid|pid $LOGS_DIR/nginx.pid|g" "$temp_file"

    # - 替换 error_log 路径
    sedi "s|error_log[[:space:]]\+logs/|error_log $LOGS_DIR/|g" "$temp_file"

    # - 替换 access_log 路径
    sedi "s|access_log[[:space:]]\+logs/|access_log $LOGS_DIR/|g" "$temp_file"

    # - 替换 /opt/soft/nginx/ 路径
    sedi "s|/opt/soft/nginx/|$PLAY_NGINX_DIR/|g" "$temp_file"

    mv "$temp_file" "$conf_file"
done

# 6b. 重命名 .upsync 文件为 .conf（先删除原 .conf）
echo "[6b/14] Renaming .upsync files to .conf..."
for upsync_file in "$CONF_DIR"/upstream.*.upsync; do
    if [ -f "$upsync_file" ]; then
        conf_file="${upsync_file%.upsync}.conf"
        if [ -f "$conf_file" ]; then
            rm "$conf_file"
            echo "Deleted existing: $(basename "$conf_file")"
        fi
        mv "$upsync_file" "$conf_file"
        echo "Renamed: $(basename "$upsync_file") -> $(basename "$conf_file")"
    fi
done

# 6c. 本地 DNS 不监听 127.0.0.1，修正 nginx resolver
echo "[6c/14] Patching nginx resolver..."
find "$CONF_DIR" -name "*.conf" -not -path "$CONF_DIR/lua/*" | while read -r conf_file; do
    sedi 's/resolver[[:space:]]\+127\.0\.0\.1\([[:space:];]\)/resolver 10.1.1.1\1/g' "$conf_file"
done

# 7. 修改lua文件中的路径
echo "[7/14] Modifying lua files..."

# 获取OpenResty的lualib路径
OPENRESTY_LUALIB="$OPENRESTY_PREFIX/lualib"
LUAROCKS_LUALIB="$HOME/.luarocks/lib/lua/5.1;/usr/local/lib/lua/5.1"
echo "Using OpenResty lualib: $OPENRESTY_LUALIB"
echo "Using LuaRocks lualib:  $LUAROCKS_LUALIB"

find "$LUA_DEST" -name "*.lua" | while read -r lua_file; do
    echo "Processing $lua_file..."

    temp_file="${lua_file}.tmp"
    cp "$lua_file" "$temp_file"

    # - 替换 /opt/soft/nginx/ 路径
    sedi "s|/opt/soft/nginx/|$PLAY_NGINX_DIR/|g" "$temp_file"

    # - 把 /opt/soft/rule-nginx/lualib/ 替换为 OpenResty 的 lualib 路径
    sedi "s|/opt/soft/rule-nginx/lualib/?.lua;|$OPENRESTY_LUALIB/?.lua;|g" "$temp_file"
    sedi "s|/opt/soft/rule-nginx/lualib/?.so|$OPENRESTY_LUALIB/?.so;$LUAROCKS_LUALIB/?.so;;|g" "$temp_file"

    mv "$temp_file" "$lua_file"
done

# 8. 特别处理 ipv6_utils.lua - 因为需要 libluna_ffi_core.so，本地没有这个库，mock掉
echo "[8/14] Patching ipv6_utils.lua..."
IPV6_UTILS="$LUA_DEST/utils/ipv6_utils.lua"
if [ -f "$IPV6_UTILS" ]; then
    cat > "$IPV6_UTILS" << 'EOF'
---
-- ipv6 on luna-ffi-core (MOCKED for local dev)
---
local _M = {}

function _M:load()
    -- No-op: mocked for local dev
end

function _M:find_ipv6_info(ipv6_str)
    return {
        isp_id = 0,
        continent_id = 0,
        country_id = 0,
        zone_id = 0,
        province_id = 0,
        city_id = 0,
        county_id = 0,
        town_id = 0,
        id = nil
    }
end

return _M
EOF
fi

# 9. mock meta_service.lua，本地不连接 cassandra
META_SERVICE="$LUA_DEST/utils/meta_service.lua"
echo "[9/14] Patching meta_service.lua..."
if [ -f "$META_SERVICE" ]; then
    cat > "$META_SERVICE" << 'EOF'
local _M = {}

function _M.get_by_vid(vid)
    return nil, "cassandra metadata service disabled for local dev"
end

function _M.get_by_proper_vid(vid, rid)
    return _M.get_by_vid(rid or vid)
end

function _M.execute(...)
    return nil, "cassandra metadata service disabled for local dev"
end

return _M
EOF
fi

OPENSSL_UTILS="$LUA_DEST/utils/openssl_utils.lua"
echo "[10/14] Patching openssl_utils.lua..."
if [ -f "$OPENSSL_UTILS" ]; then
    if [ -n "$OPENSSL_LIBCRYPTO" ]; then
        sedi "s|ffi.load('libcrypto')|ffi.load('$OPENSSL_LIBCRYPTO')|g" "$OPENSSL_UTILS"
    else
        echo "Warning: libcrypto not found; leaving ffi.load('libcrypto') unchanged"
    fi
fi

# 11. 创建空的IP数据文件
echo "[11/14] Creating empty IP data files..."
touch "$LUA_DEST/ip_zone_dtd.data"
touch "$LUA_DEST/ip_akamai_zone_dtd.data"

# 12. 写入 run_profile
echo "[12/14] Writing run profile..."
PROFILE_FILE="$LUA_DEST/profile"
echo "$RUN_PROFILE" > "$PROFILE_FILE"
echo "Profile written to $PROFILE_FILE"

# 13. 下载4s配置数据
echo "[13/14] Downloading 4s config data..."
if [ ! -d "$PLAY_OPS_SOURCE" ]; then
    echo "Error: $PLAY_OPS_SOURCE not found"
    exit 1
fi
if [ ! -x "$PYTHON_BIN" ]; then
    echo "Error: $PYTHON_BIN not found or not executable"
    exit 1
fi
cp -r "$PLAY_OPS_SOURCE" "$PLAY_OPS_DIR"
cd "$PLAY_OPS_DIR"
# play_ops is a disposable build copy. Clean it before checkout because the
# source repo may be on another branch with local edits.
git reset --hard
git clean -fd
git fetch origin dash_ops
git checkout -B dash_ops origin/dash_ops
git reset --hard origin/dash_ops
git clean -fd
cd "$PLAY_NGINX_DIR/html"
"$PYTHON_BIN" - << EOF
import sys
import types

fabric = types.ModuleType("fabric")
fabric_api = types.ModuleType("fabric.api")
fabric_api.env = types.SimpleNamespace(disable_known_hosts=False)
fabric_api.task = lambda func: func
fabric_api.run = lambda *args, **kwargs: None
fabric_api.put = lambda *args, **kwargs: None
fabric.api = fabric_api
sys.modules["fabric"] = fabric
sys.modules["fabric.api"] = fabric_api

sys.path.insert(0, "$PLAY_OPS_DIR/syn_4s_data")
from fabfile import download_4s_data, download_config_data

download_4s_data("1", "$LUNA_ENV_NAME")
download_config_data("1", "$LUNA_ENV_NAME")
EOF

# 14. 测试nginx配置
echo "[14/14] Testing nginx config..."
cd "$PLAY_NGINX_DIR"
openresty -p "$PWD" -c conf/nginx.conf -t

echo "Done!"
echo ""
echo "=========================================="
echo "Success!"
echo "Working directory: $WORK_DIR"
echo "Run profile:      $RUN_PROFILE"
echo ""
echo "To start openresty:"
echo "  cd $PLAY_NGINX_DIR"
echo "  openresty -p \$PWD -c conf/nginx.conf"
echo ""
echo "To stop:"
echo "  openresty -p \$PWD -c conf/nginx.conf -s stop"
echo "=========================================="
