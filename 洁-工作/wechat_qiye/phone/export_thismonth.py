#!/usr/bin/env python3
"""导出梁蓝欣「图片与视频」中 本周+这个月 的图片到 2026-07（截屏方式）。"""

from __future__ import annotations

import hashlib
import io
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent / "2026-07"
TEMP = Path("/tmp/wework_thismonth")
UI = TEMP / "ui.xml"


def adb(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *a], capture_output=True, text=True)


def focus() -> str:
    return adb("shell", "dumpsys window | grep mCurrentFocus").stdout


def tap(x: int, y: int, d: float = 0.9) -> None:
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(d)


def back(d: float = 0.65) -> None:
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(d)


def dump() -> ET.ElementTree | None:
    for _ in range(4):
        adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        if adb("pull", "/sdcard/ui.xml", str(UI)).returncode == 0 and UI.exists() and UI.stat().st_size > 200:
            try:
                return ET.parse(UI)
            except ET.ParseError:
                pass
        time.sleep(0.4)
    return None


def texts(tree: ET.ElementTree | None) -> list[str]:
    if not tree:
        return []
    return [n.attrib.get("text", "") for n in tree.getroot().iter("node") if n.attrib.get("text")]


def thumbs(tree: ET.ElementTree | None) -> list[tuple[int, int, int]]:
    pts = []
    if not tree:
        return pts
    for n in tree.getroot().iter("node"):
        if n.attrib.get("resource-id") != "com.tencent.wework:id/fzb":
            continue
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if y2 - y1 < 80:
            continue
        pts.append(((x1 + x2) // 2, (y1 + y2) // 2, y1))
    return pts


def header_y(tree: ET.ElementTree | None, name: str) -> int | None:
    if not tree:
        return None
    for n in tree.getroot().iter("node"):
        if n.attrib.get("text") == name:
            m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
            if m:
                return int(m.group(2))
    return None


def screencap() -> bytes:
    return subprocess.check_output(["adb", "exec-out", "screencap", "-p"])


def is_content_image(data: bytes) -> bool:
    """排除加载中黑屏 / 几乎空白。"""
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        # 裁掉状态栏和底部操作栏，只看中间内容区
        w, h = img.size
        crop = img.crop((40, 180, w - 40, int(h * 0.78)))
        # 抽样像素
        small = crop.resize((64, 64))
        pixels = list(small.getdata())
        avg = sum(sum(p) for p in pixels) / (len(pixels) * 3)
        # 方差：全黑/全白很低
        var = sum((sum(p) / 3 - avg) ** 2 for p in pixels) / len(pixels)
        return avg > 25 and var > 80
    except Exception:
        return False


def capture_open_image(idx: int) -> Path | None:
    if "MediaPreviewerActivity" not in focus():
        return None
    data = None
    for _ in range(15):
        data = screencap()
        if is_content_image(data):
            break
        time.sleep(0.7)
    else:
        return None

    # 内容哈希去重
    h = hashlib.md5(data).hexdigest()[:10]
    dest = OUT / f"这个月_{idx:03d}_{h}.png"
    # 若内容已存在则跳过
    for old in OUT.glob("这个月_*.png"):
        if h in old.name:
            return old
    dest.write_bytes(data)
    return dest


def back_to_gallery() -> None:
    for _ in range(3):
        if "ImageVideoSearchActivity" in focus():
            return
        back()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():
            old.unlink()

    if "ImageVideoSearchActivity" not in focus():
        raise SystemExit("请先打开梁蓝欣「图片与视频」页")

    print("滚到顶部...")
    for _ in range(10):
        adb("shell", "input", "swipe", "540", "400", "540", "1800", "400")
        time.sleep(0.28)

    saved: list[Path] = []
    seen_grid: set[str] = set()
    same = 0
    last_hash = ""
    stop = False
    idx = 0

    for page in range(1, 20):
        page_png = screencap()
        ph = hashlib.md5(page_png).hexdigest()
        if ph == last_hash:
            same += 1
            if same >= 2:
                break
        else:
            same = 0
        last_hash = ph

        tree = dump()
        labels = [t for t in texts(tree) if t in ("本周", "这个月") or "2026年" in t or "2025年" in t]
        print(f"第{page}屏: {labels}")

        next_y = None
        for label in texts(tree):
            if re.search(r"2026年\s*0?6\s*月", label) or re.search(r"2026年0?[1-5]月", label) or (
                label.startswith("2025年")
            ):
                next_y = header_y(tree, label)
                stop = True
                print(f"  停在更早月份: {label}")
                break

        pts = thumbs(tree)
        if next_y is not None:
            pts = [p for p in pts if p[2] < next_y - 10]
        pts = sorted(pts, key=lambda p: (p[2], p[0]))

        for x, y, y1 in pts:
            gkey = f"{x // 30}_{y1 // 50}"
            if gkey in seen_grid:
                continue
            seen_grid.add(gkey)

            tap(x, y, 1.0)
            idx += 1
            path = capture_open_image(idx)
            back_to_gallery()
            if path and path not in saved:
                # 新文件才算成功
                if path.stat().st_mtime >= time.time() - 30 or path not in saved:
                    if path not in saved:
                        saved.append(path)
                print(f"  ✓ ({x},{y}) -> {path.name} 累计{len(saved)}")
            else:
                print(f"  ✗ ({x},{y}) 未加载或打开失败")

        if stop:
            break
        adb("shell", "input", "swipe", "540", "1800", "540", "500", "450")
        time.sleep(1.0)

    print(f"\n完成：共 {len(saved)} 张 -> {OUT}")
    return 0 if saved else 1


if __name__ == "__main__":
    raise SystemExit(main())
