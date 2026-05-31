#!/usr/bin/env bash
# 依次为两个差客账号申请贵宾 VIP 卡退款：
#   当前账号退款 -> 切换账号 -> 另一账号退款 -> 切回原账号
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-/Users/weichaofan/miniconda3/envs/py3.11/bin/python}"

REFUND_PY="${SCRIPT_DIR}/chake_refund.py"
SWITCH_PY="${SCRIPT_DIR}/chake-switch-account.py"

EXECUTE=0
SKIP_UNLOCK=()
RELAUNCH=()

usage() {
  cat <<EOF
用法: $(basename "$0") --execute [选项]

依次为两个差客账号批量申请贵宾 VIP 卡退款（当前账号 -> 切换 -> 另一账号 -> 切回）。

选项:
  --execute            实际操作手机（未指定时仅 dry-run）
  --skip-unlock-check  跳过锁屏检测（传给退款与切换脚本）
  --relaunch           切换账号前强制重启差客 App（仅切换脚本）

示例:
  $(basename "$0") --execute
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --execute)
      EXECUTE=1
      ;;
    --skip-unlock-check)
      SKIP_UNLOCK+=(--skip-unlock-check)
      ;;
    --relaunch)
      RELAUNCH+=(--relaunch)
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

refund_args=("${SKIP_UNLOCK[@]}")
switch_args=("${SKIP_UNLOCK[@]}" "${RELAUNCH[@]}")

if [[ "$EXECUTE" -eq 1 ]]; then
  refund_args+=(--execute)
  switch_args+=(--execute)
fi

run_step() {
  local title="$1"
  shift
  echo ""
  echo "========== ${title} =========="
  "$@"
}

run_step "1/4 当前账号：申请退款" \
  "$PYTHON" "$REFUND_PY" "${refund_args[@]}"

run_step "2/4 切换到另一账号" \
  "$PYTHON" "$SWITCH_PY" "${switch_args[@]}"

run_step "3/4 另一账号：申请退款" \
  "$PYTHON" "$REFUND_PY" "${refund_args[@]}"

run_step "4/4 切回原账号" \
  "$PYTHON" "$SWITCH_PY" "${switch_args[@]}"

echo ""
if [[ "$EXECUTE" -eq 1 ]]; then
  echo "两个账号的退款流程已全部完成。"
else
  echo "dry-run 完成。加上 --execute 才会实际操作手机。"
fi
