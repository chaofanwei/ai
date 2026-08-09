#!/usr/bin/env python3
"""从梁蓝欣聊天图片页保存各月 2026 工资条到本地按月文件夹。"""

import hashlib
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent / "梁蓝欣_工资条"
WEIXIN_WORK = "/sdcard/DCIM/WeixinWork"
SAVE_BTN = (690, 1842)

# (文件夹名, 从顶部向下滚动次数, 候选点击坐标)
MONTHS = [
    ("2026-07", 0, [(675, 709), (137, 1200), (406, 1200)]),
    ("2026-06", 1, [(944, 709), (137, 978)]),
    ("2026-05", 2, [(406, 978), (675, 978), (406, 709)]),
    ("2026-04", 4, [(137, 978), (137, 709)]),
    ("2026-03", 5, [(406, 1247), (406, 978)]),
    ("2026-02", 8, [(137, 440), (406, 440)]),
    ("2026-01", 9, [(137, 440), (406, 440), (675, 440)]),
]


def adb(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *a], capture_output=True, text=True)


def tap(x: int, y: int, d: float = 0.8) -> None:
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(d)


def back() -> None:
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(0.6)


def focus() -> str:
    return adb("shell", "dumpsys window | grep mCurrentFocus").stdout or ""


def scroll_to_top() -> None:
    for _ in range(14):
        adb("shell", "input", "swipe", "540", "400", "540", "1800", "400")
        time.sleep(0.35)


def scroll_down(n: int) -> None:
    for _ in range(n):
        adb("shell", "input", "swipe", "540", "1800", "540", "400", "400")
        time.sleep(0.65)


def list_remote() -> set[str]:
    r = adb(
        "shell",
        f"find {WEIXIN_WORK} -type f \\( -iname '*.jpg' -o -iname '*.png' \\) 2>/dev/null",
    )
    return {x.strip() for x in r.stdout.splitlines() if x.strip()}


def pull_new(before: set[str], dest_dir: Path) -> Path | None:
    after = list_remote()
    new = sorted(after - before)
    if not new:
        return None
    remote = new[-1]
    dest_dir.mkdir(parents=True, exist_ok=True)
    name = Path(remote).name
    local = dest_dir / f"工资条_{name}"
    if adb("pull", remote, str(local)).returncode == 0 and local.exists():
        return local
    return None


def try_save(x: int, y: int, dest_dir: Path) -> Path | None:
    before = list_remote()
    tap(x, y, 1.0)
    if "MediaPreviewerActivity" not in focus():
        return None
    for _ in range(8):
        time.sleep(0.6)
        if "MediaPreviewerActivity" in focus():
            break
    tap(*SAVE_BTN, 1.2)
    back()
    return pull_new(before, dest_dir)


def main() -> int:
    if "\tdevice" not in adb("devices").stdout:
        print("未连接设备")
        return 1

    if "ImageVideoSearchActivity" not in focus():
        adb("shell", "am", "start", "-n", "com.tencent.wework/.launch.LaunchSplashActivity")
        time.sleep(2)
        tap(540, 836, 1.5)
        tap(1014, 146, 1.0)
        tap(415, 823, 1.2)

    scroll_to_top()
    saved: list[str] = []

    for folder, scrolls, points in MONTHS:
        scroll_to_top()
        scroll_down(scrolls)
        dest = BASE / folder
        ok = None
        for x, y in points:
            ok = try_save(x, y, dest)
            if ok:
                break
        if ok:
            print(f"✓ {folder} -> {ok.name}")
            saved.append(folder)
        else:
            print(f"✗ {folder} 未能保存，请手动检查")

    print(f"\n完成 {len(saved)}/7: {saved}")
    return 0 if len(saved) == 7 else 1


if __name__ == "__main__":
    sys.exit(main())
