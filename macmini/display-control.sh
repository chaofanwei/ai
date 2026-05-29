#!/bin/bash

case "$1" in
    off)
        echo "关闭显示器..."
        pmset displaysleepnow
        ;;
    on)
        echo "唤醒显示器并保持30分钟..."

        # 1. 先使用 caffeinate -u 模拟用户活动来唤醒显示器
        caffeinate -u -t 2

        # 2. 使用 caffeinate 保持显示器开启30分钟 (1800秒)
        # -d: 防止显示器休眠
        # -t: 持续时间（秒）
        caffeinate -d -t 1800 &
        echo "显示器将保持开启30分钟 (PID: $!)"
        ;;
    *)
        echo "用法: $0 {off|on}"
        echo "  off - 关闭显示器"
        echo "  on  - 唤醒显示器/解除屏幕保护"
        ;;
esac
