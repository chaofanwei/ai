#!/bin/zsh
# 用 Whisky/Wine 启动 Windows 版 Foxmail 7.2（瓶子 foxmail72）
set -euo pipefail

BOTTLE_NAME="foxmail72"
BOTTLE="$HOME/Library/Containers/com.franke.Whisky/Bottles/3CA0120D-89C8-4821-92D5-9C2A598B6169"
WINE_BIN="$HOME/Library/Application Support/com.franke.Whisky/Libraries/Wine/bin"
FOXMAIL_DIR="/Volumes/Storage/foxmail/extracted/Foxmail 7.2"
FOXMAIL_EXE="$FOXMAIL_DIR/Foxmail.exe"
LOG_DIR="$HOME/Library/Logs/FoxmailWine"
LOG="$LOG_DIR/foxmail_$(date +%Y%m%d_%H%M%S).log"

mkdir -p "$LOG_DIR"

die() {
  echo "❌ $*" | tee -a "$LOG" >&2
  echo "日志: $LOG" >&2
  exit 1
}

echo "==== Foxmail Wine 启动 $(date) ====" | tee "$LOG"

# 1) 机械盘
[[ -d "/Volumes/Storage" ]] || die "机械盘 Storage 未挂载，请先接入/打开磁盘"
[[ -x "$FOXMAIL_EXE" ]] || die "找不到 Foxmail.exe: $FOXMAIL_EXE"

# 2) Wine 运行时
[[ -x "$WINE_BIN/wine64" ]] || die "找不到 wine64，请先在 Whisky 里装好 Wine 运行时: $WINE_BIN"
[[ -d "$BOTTLE" ]] || die "找不到瓶子目录: $BOTTLE"

# 3) 盘符映射（Whisky / wine 都会用到）
mkdir -p "$BOTTLE/dosdevices"
ln -sfn "$FOXMAIL_DIR" "$BOTTLE/dosdevices/f:"
ln -sfn "$FOXMAIL_DIR" "$BOTTLE/drive_f"

# 4) 环境（勿用带转义空格的 PATH）
export PATH="$WINE_BIN:$PATH"
export WINEPREFIX="$BOTTLE"
export WINEESYNC=1
export WINEMSYNC=1
export WINEFSYNC=0
export WINEDEBUG="-all"
export LANG="zh_CN.UTF-8"
export LC_ALL="zh_CN.UTF-8"
export CEF_DISABLE_SANDBOX=1
export STEAM_DISABLE_CEF_SANDBOX=1
# 修复 Wine 下 CEF 正文预览黑屏（禁用 Angle/GLES）
export WINEDLLOVERRIDES="libglesv2.dll=d;libEGL.dll=d${WINEDLLOVERRIDES:+;$WINEDLLOVERRIDES}"

# 5) 清理残留（避免多开导致秒退）
if pgrep -f 'Foxmail\.exe' >/dev/null 2>&1; then
  echo "检测到已有 Foxmail.exe，先结束旧进程…" | tee -a "$LOG"
  pkill -f 'Foxmail\.exe' 2>/dev/null || true
  sleep 1
fi
# 仅结束本瓶子的 wineserver（避免误杀其它 Wine）
if [[ -x "$WINE_BIN/wineserver" ]]; then
  "$WINE_BIN/wineserver" -k 2>/dev/null || true
  sleep 1
fi

# 禁用 Foxmail 自带 CEF 的 libGLESv2（黑屏常见修复，可还原 .bak_wine）
CEF_GLES="$FOXMAIL_DIR/7.2.25.542/cef4delphi/libGLESv2.dll"
if [[ -f "$CEF_GLES" && ! -f "${CEF_GLES}.bak_wine" ]]; then
  mv "$CEF_GLES" "${CEF_GLES}.bak_wine"
  echo "已禁用 CEF libGLESv2.dll（备份为 .bak_wine）" | tee -a "$LOG"
fi

echo "瓶子: $BOTTLE_NAME" | tee -a "$LOG"
echo "程序: $FOXMAIL_EXE" | tee -a "$LOG"
echo "Wine: $WINE_BIN/wine64" | tee -a "$LOG"
echo "WINEDLLOVERRIDES=$WINEDLLOVERRIDES" | tee -a "$LOG"
echo "日志: $LOG" | tee -a "$LOG"
echo "正在启动…" | tee -a "$LOG"

# 6) 启动（后台，输出进日志）
cd "$FOXMAIL_DIR"
nohup "$WINE_BIN/wine64" "F:\\Foxmail.exe" >>"$LOG" 2>&1 &
PID=$!
echo "wine 父进程 PID=$PID" | tee -a "$LOG"

# 7) 等窗口/进程出现
ok=0
for i in {1..25}; do
  sleep 1
  if pgrep -f 'Foxmail\.exe' >/dev/null 2>&1; then
    ok=1
    break
  fi
  if ! kill -0 "$PID" 2>/dev/null; then
    break
  fi
done

if [[ "$ok" -eq 1 ]]; then
  echo "✅ Foxmail 已启动。若看不见窗口：Dock 点一下，或三指上滑找桌面。" | tee -a "$LOG"
  echo "查看日志: tail -f \"$LOG\""
  exit 0
fi

echo "❌ 启动后未检测到 Foxmail.exe，可能已崩溃。" | tee -a "$LOG"
echo "---- 日志末尾 ----" | tee -a "$LOG"
tail -40 "$LOG" || true
open -R "$LOG" 2>/dev/null || true
exit 1
