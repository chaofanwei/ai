#!/usr/bin/env python3
"""在梁蓝欣聊天图片中按月查找工资条（1-15日），从最新月份往前。"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "梁蓝欣_工资条"
TEMP = Path("/tmp/wework_salary_hunt")
UI = TEMP / "ui.xml"
SHOT = TEMP / "view.png"

SALARY_KW = ["工资条", "工资", "薪资", "薪金", "实发", "应发", "薪酬", "发薪"]
# 匹配 2026年7月 / 2026-07 / 2026/07/05 等
DATE_PATTERNS = [
    re.compile(r"2026[\s年\-/\.](0?[1-7])[\s月\-/\.](0?[1-9]|1[0-5])"),
    re.compile(r"(0?[1-7])[\s月\-/\.](0?[1-9]|1[0-5])[\s日号]?\s*2026"),
    re.compile(r"2026[\s年\-/\.](0?[1-7])[\s月]"),
]

_ocr = None


@dataclass
class Hit:
    year: int
    month: int
    day: int | None
    text: str
    source: str


def log(m: str) -> None:
    print(m, flush=True)


def adb(*a: str) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *a], capture_output=True, text=True)


def tap(x: int, y: int, d: float = 0.85) -> None:
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(d)


def back(d: float = 0.55) -> None:
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(d)


def focus() -> str:
    return adb("shell", "dumpsys window | grep mCurrentFocus").stdout or ""


def dump_ui() -> ET.ElementTree | None:
    for _ in range(4):
        adb("shell", "uiautomator", "dump", "/sdcard/wework_ui.xml")
        if adb("pull", "/sdcard/wework_ui.xml", str(UI)).returncode == 0 and UI.stat().st_size > 200:
            try:
                return ET.parse(UI)
            except ET.ParseError:
                pass
        time.sleep(0.5)
    return None


def ensure_gallery() -> None:
    if "ImageVideoSearchActivity" in focus():
        return
    adb("shell", "am", "start", "-n", "com.tencent.wework/.launch.LaunchSplashActivity")
    time.sleep(2.5)
    if dump_ui():
        for n in ET.parse(UI).getroot().iter("node"):
            if "梁蓝欣" in n.attrib.get("text", ""):
                m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                if m:
                    _, y1, _, y2 = map(int, m.groups())
                    tap(540, min(y2 + 60, 2000), 1.5)
                    break
    tap(1014, 146, 1.0)
    tap(415, 823, 1.2)


def scroll_to_bottom() -> None:
    """媒体页一般最新在底部，先滚到最新。"""
    last = ""
    for _ in range(25):
        h = hashlib.md5(subprocess.check_output(["adb", "exec-out", "screencap", "-p"])).hexdigest()
        if h == last:
            break
        last = h
        adb("shell", "input", "swipe", "540", "1900", "540", "500", "450")
        time.sleep(0.7)


def thumb_points(tree: ET.ElementTree | None) -> list[tuple[int, int]]:
    if not tree:
        return []
    pts = []
    for n in tree.getroot().iter("node"):
        if n.attrib.get("resource-id") != "com.tencent.wework:id/fzb":
            continue
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
        if m:
            x1, y1, x2, y2 = map(int, m.groups())
            if y2 - y1 >= 80:
                pts.append(((x1 + x2) // 2, (y1 + y2) // 2))
    return pts


def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        log("加载 OCR...")
        _ocr = PaddleOCR(lang="ch")
    return _ocr


def ocr_text(path: Path) -> str:
    result = get_ocr().ocr(str(path))
    texts: list[str] = []
    if not result:
        return ""
    for block in result:
        if isinstance(block, dict):
            texts.extend(str(t) for t in (block.get("rec_texts") or []))
        elif block:
            for item in block:
                if isinstance(item, dict):
                    texts.extend(str(t) for t in (item.get("rec_texts") or []))
                elif item and len(item) >= 2 and item[1]:
                    texts.append(str(item[1][0]))
    return " ".join(texts)


def parse_2026_date(text: str) -> tuple[int, int | None] | None:
    if "2026" not in text and not any(k in text for k in SALARY_KW):
        return None
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            g = m.groups()
            if len(g) == 2:
                month, day = int(g[0]), int(g[1])
                if 1 <= month <= 7 and 1 <= day <= 15:
                    return month, day
            elif len(g) == 1:
                month = int(g[0])
                if 1 <= month <= 7:
                    return month, None
    # 只有月份文字：7月份工资
    m = re.search(r"(0?[1-7])\s*月份?\s*.*(?:工资|薪资|薪金)", text)
    if m and "2026" in text:
        return int(m.group(1)), None
    m2 = re.search(r"2026\s*年\s*(0?[1-7])\s*月", text)
    if m2:
        return int(m2.group(1)), None
    return None


def is_salary(text: str) -> bool:
    return any(k in text for k in SALARY_KW)


def capture_view() -> Path:
    TEMP.mkdir(parents=True, exist_ok=True)
    SHOT.write_bytes(subprocess.check_output(["adb", "exec-out", "screencap", "-p"]))
    return SHOT


def save_image_to_album() -> None:
    tree = dump_ui()
    if tree:
        for n in tree.getroot().iter("node"):
            if n.attrib.get("text") == "保存图片":
                m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n.attrib.get("bounds", ""))
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    tap((x1 + x2) // 2, (y1 + y2) // 2, 1.0)
                    return
    tap(690, 1842, 1.0)


def hunt_2026(max_pages: int = 40) -> dict[int, Hit]:
    ensure_gallery()
    scroll_to_bottom()

    found: dict[int, Hit] = {}  # month -> hit
    seen_views: set[str] = set()
    same = 0
    last_hash = ""

    for page in range(1, max_pages + 1):
        h = hashlib.md5(subprocess.check_output(["adb", "exec-out", "screencap", "-p"])).hexdigest()
        if h == last_hash:
            same += 1
            if same >= 2:
                break
        else:
            same = 0
        last_hash = h

        tree = dump_ui()
        pts = thumb_points(tree)
        # 从右下到左上（较新的通常在下方）逆序点
        for x, y in reversed(pts):
            tap(x, y, 1.0)
            if "MediaPreviewerActivity" not in focus():
                continue
            img = capture_view()
            vh = hashlib.md5(img.read_bytes()).hexdigest()
            if vh in seen_views:
                back()
                continue
            seen_views.add(vh)

            text = ocr_text(img)
            if not is_salary(text):
                back()
                continue

            parsed = parse_2026_date(text)
            if not parsed:
                back()
                continue
            month, day = parsed
            if month in found:
                back()
                continue

            save_image_to_album()
            OUT.mkdir(parents=True, exist_ok=True)
            dest = OUT / f"2026-{month:02d}{f'-{day:02d}' if day else ''}_工资条.png"
            dest.write_bytes(img.read_bytes())
            found[month] = Hit(2026, month, day, text[:120], dest.name)
            log(f"✓ 找到 2026年{month}月" + (f"{day}日" if day else "") + f" -> {dest.name}")

            if len(found) >= 7:  # 1-7月齐
                back()
                return found
            back()

        # 向上滚看更早月份
        adb("shell", "input", "swipe", "540", "500", "540", "1900", "450")
        time.sleep(0.9)

    return found


def main() -> int:
    if "\tdevice" not in adb("devices").stdout:
        log("未连接 ADB 设备")
        return 1
    log("在梁蓝欣聊天图片中查找 2026 年 1-7 月工资条（每月1-15日）...")
    found = hunt_2026()
    log(f"\n2026 年共找到 {len(found)} 个月份的工资条: {sorted(found.keys())}")
    for m in sorted(found):
        h = found[m]
        log(f"  {m}月: {h.source} | {h.text[:60]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
