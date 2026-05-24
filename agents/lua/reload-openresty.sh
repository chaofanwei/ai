#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAY_NGINX_DIR="${PLAY_NGINX_DIR:-$SCRIPT_DIR/nginx-dev/play-nginx}"
PID_FILE="$PLAY_NGINX_DIR/logs/nginx.pid"

if ! command -v openresty >/dev/null 2>&1; then
    echo "Error: openresty command not found"
    exit 1
fi

if [ ! -d "$PLAY_NGINX_DIR" ]; then
    echo "Error: $PLAY_NGINX_DIR not found!"
    exit 1
fi

if [ ! -s "$PID_FILE" ]; then
    echo "Error: openresty is not running or pid file is empty: $PID_FILE"
    echo "Please run start-openresty.sh first"
    exit 1
fi

cd "$PLAY_NGINX_DIR"
echo "Testing openresty config..."
openresty -p "$PWD" -c conf/nginx.conf -t

echo "Reloading openresty..."
openresty -p "$PWD" -c conf/nginx.conf -s reload

if [ $? -eq 0 ]; then
    echo "Openresty reloaded successfully"
else
    echo "Failed to reload openresty"
fi
