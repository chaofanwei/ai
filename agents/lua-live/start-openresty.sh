#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAY_NGINX_DIR="${PLAY_NGINX_DIR:-$SCRIPT_DIR/nginx-dev/play-nginx}"

if ! command -v openresty >/dev/null 2>&1; then
    echo "Error: openresty command not found"
    exit 1
fi

if [ ! -d "$PLAY_NGINX_DIR" ]; then
    echo "Error: $PLAY_NGINX_DIR not found!"
    echo "Please run build-nginx-dev.sh first"
    exit 1
fi

cd "$PLAY_NGINX_DIR"
echo "Stopping existing nginx processes..."
pkill nginx || true

echo "Starting openresty..."
openresty -p "$PWD" -c conf/nginx.conf

if [ $? -eq 0 ]; then
    echo "Openresty started successfully"
    echo "Listening on: http://localhost:8080"
else
    echo "Failed to start openresty"
fi

echo ""
echo "Testing with:"
echo 'curl -H "Host: cache.video.iqiyi.com" "localhost:8080/dash?tvid=100"'
curl -H "Host: cache.video.iqiyi.com" "localhost:8080/dash?tvid=100"
echo ""
