#!/usr/bin/env bash
set -euo pipefail

ADB="${ADB:-/Users/weichaofan/Library/Android/sdk/platform-tools/adb}"
TOUCH_DEV="${TOUCH_DEV:-/dev/input/event2}"

# Calibrated from:
#   com.android.systemui:id/lockPatternView bounds="[105,1040][975,1910]"
# Pattern: uppercase L from middle column down, then right: 2 -> 5 -> 8 -> 9.
POINTS=(
  "540 1185"
  "540 1475"
  "540 1765"
  "830 1765"
)

run_adb() {
  "$ADB" "$@"
}

touch_pattern() {
  local tracking_id="${1:-23456}"
  local first_x first_y x y
  local local_script remote_script

  read -r first_x first_y <<< "${POINTS[0]}"

  local_script="$(mktemp /tmp/unlock_pattern.XXXXXX.sh)"
  remote_script="/data/local/tmp/unlock_pattern.sh"

  {
    cat <<EOF
#!/system/bin/sh
sendevent $TOUCH_DEV 3 47 0
sendevent $TOUCH_DEV 3 57 $tracking_id
sendevent $TOUCH_DEV 3 53 $first_x
sendevent $TOUCH_DEV 3 54 $first_y
sendevent $TOUCH_DEV 3 48 8
sendevent $TOUCH_DEV 1 330 1
sendevent $TOUCH_DEV 0 0 0
sleep 0.10
EOF

    for point in "${POINTS[@]:1}"; do
      read -r x y <<< "$point"
      cat <<EOF
sendevent $TOUCH_DEV 3 53 $x
sendevent $TOUCH_DEV 3 54 $y
sendevent $TOUCH_DEV 0 0 0
sleep 0.10
EOF
    done

    cat <<EOF
sendevent $TOUCH_DEV 3 57 -1
sendevent $TOUCH_DEV 1 330 0
sendevent $TOUCH_DEV 0 0 0
EOF
  } > "$local_script"

  run_adb push "$local_script" "$remote_script" >/dev/null
  rm -f "$local_script"
  run_adb shell su -c "sh $remote_script"
}

echo "正在解锁手机..."

echo "  点亮并保持亮屏..."
run_adb shell su -c 'svc power stayon true'
run_adb shell input keyevent 224
sleep 0.2

echo "  进入图案解锁界面..."
run_adb shell input swipe 500 1800 500 300 300
sleep 0.6

echo "  执行 L 形图案 2-5-8-9..."
touch_pattern
sleep 0.5

if run_adb shell dumpsys window policy | grep -q 'showing=false'; then
  echo "解锁完成"
else
  echo "已发送解锁手势，但系统仍显示锁屏；请确认图案界面可见或 TOUCH_DEV 是否正确。" >&2
  exit 1
fi
