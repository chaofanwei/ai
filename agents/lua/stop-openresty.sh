#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAY_NGINX_DIR="${PLAY_NGINX_DIR:-$SCRIPT_DIR/nginx-dev/play-nginx}"

if ! command -v openresty >/dev/null 2>&1; then
    echo "Error: openresty command not found"
    exit 1
fi

if [ ! -d "$PLAY_NGINX_DIR" ]; then
    echo "Error: $PLAY_NGINX_DIR not found!"
    exit 1
fi

cd "$PLAY_NGINX_DIR"
echo "Stopping openresty..."
openresty -p "$PWD" -c conf/nginx.conf -s stop

if [ $? -eq 0 ]; then
    echo "Openresty stopped successfully"
else
    echo "Failed to stop openresty"
fi
