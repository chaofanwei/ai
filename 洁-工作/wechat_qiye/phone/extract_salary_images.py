#!/usr/bin/env python3
"""从企业微信梁蓝欣聊天的图片/视频页导出工资条图片。"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "梁蓝欣_工资条"
TEMP_DIR = Path("/tmp/wework_extract")
UI_XML = TEMP_DIR / "ui.xml"
WEIXIN_WORK_DIR = "/sdcard/DCIM/WeixinWork"

SALARY_KEYWORDS = [
    "工资条", "工资", "薪资", "薪金", "实发", "应发", "代扣",
    "基本工资", "绩效工资", "税前", "税后", "发薪", "薪酬",
]

COL_X = [137, 406, 675, 944]
ROW_CENTERS = [440, 709, 978, 1247, 1516, 1785]

SAVE_BTN = (690, 1842)
_ocr = None


def log(msg: str) -> None:
    print(msg, flush=True)


def adb(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", *args], capture_output=True, text=True)


def tap(x: int, y: int, delay: float = 0.8) -> None:
    adb("shell", "input", "tap", str(x), str(y))
    time.sleep(delay)


def back(delay: float = 0.6) -> None:
    adb("shell", "input", "keyevent", "KEYCODE_BACK")
    time.sleep(delay)


def swipe_up() -> None:
    adb("shell", "input", "swipe", "540", "1900", "540", "500", "450")
    time.sleep(1.0)


def dump_ui(retries: int = 4) -> ET.ElementTree | None:
    for _ in range(retries):
        adb("shell", "uiautomator", "dump", "/sdcard/wework_ui.xml")
        r = adb("pull", "/sdcard/wework_ui.xml", str(UI_XML))
        if r.returncode == 0 and UI_XML.exists() and UI_XML.stat().st_size > 200:
            try:
                return ET.parse(UI_XML)
            except ET.ParseError:
                pass
        time.sleep(0.6)
    return None


def thumbnail_centers(tree: ET.ElementTree) -> list[tuple[int, int]]:
    pts: list[tuple[int, int]] = []
    for node in tree.getroot().iter("node"):
        if node.attrib.get("resource-id") != "com.tencent.wework:id/fzb":
            continue
        m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
        if not m:
            continue
        x1, y1, x2, y2 = map(int, m.groups())
        if y2 - y1 < 80:
            continue
        pts.append(((x1 + x2) // 2, (y1 + y2) // 2))
    return pts


def list_weixin_work_files() -> set[str]:
    r = adb(
        "shell",
        f"find {WEIXIN_WORK_DIR} -type f \\( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \\) 2>/dev/null",
    )
    return {line.strip() for line in r.stdout.splitlines() if line.strip()}


def save_open_image() -> bool:
    tree = dump_ui()
    if tree:
        for node in tree.getroot().iter("node"):
            if node.attrib.get("text") == "保存图片":
                m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    tap((x1 + x2) // 2, (y1 + y2) // 2, 1.0)
                    return True
    tap(*SAVE_BTN, 1.0)
    return True


def pull_new_files(before: set[str], dest: Path) -> list[Path]:
    after = list_weixin_work_files()
    new_remote = sorted(after - before)
    dest.mkdir(parents=True, exist_ok=True)
    pulled: list[Path] = []
    for remote in new_remote:
        local = dest / Path(remote).name
        if local.exists():
            local = dest / f"{local.stem}_{hashlib.md5(remote.encode()).hexdigest()[:6]}{local.suffix}"
        if adb("pull", remote, str(local)).returncode == 0 and local.exists():
            pulled.append(local)
    return pulled


def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        log("加载 OCR 模型...")
        _ocr = PaddleOCR(lang="ch")
    return _ocr


def extract_text(path: Path) -> str:
    result = get_ocr().ocr(str(path))
    texts: list[str] = []
    if not result:
        return ""
    for block in result:
        if isinstance(block, dict):
            texts.extend(str(t) for t in (block.get("rec_texts") or []))
            continue
        if not block:
            continue
        for item in block:
            if isinstance(item, dict):
                texts.extend(str(t) for t in (item.get("rec_texts") or []))
            elif item and len(item) >= 2 and item[1]:
                texts.append(str(item[1][0]))
    return " ".join(texts)


def is_salary(path: Path) -> tuple[bool, str]:
    try:
        text = extract_text(path)
        return any(k in text for k in SALARY_KEYWORDS), text
    except Exception as e:
        log(f"  OCR 失败 {path.name}: {e}")
        return False, ""


def current_focus() -> str:
    r = adb("shell", "dumpsys window | grep mCurrentFocus")
    return r.stdout or ""


def ensure_gallery() -> None:
    for _ in range(6):
        focus = current_focus()
        if "ImageVideoSearchActivity" in focus:
            return
        if "MessageListActivity" in focus:
            tap(1014, 146, 1.0)
            tap(415, 823, 1.2)
            continue
        if "MediaPreviewerActivity" in focus or "BaseContentActivity" in focus:
            back()
            continue
        adb("shell", "am", "start", "-n", "com.tencent.wework/.launch.LaunchSplashActivity")
        time.sleep(2.5)
        if dump_ui():
            for node in ET.parse(UI_XML).getroot().iter("node"):
                if "梁蓝欣" in node.attrib.get("text", ""):
                    m = re.search(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", node.attrib.get("bounds", ""))
                    if m:
                        _, y1, _, y2 = map(int, m.groups())
                        tap(540, min(y2 + 60, 2000), 1.5)
                        break
            tap(1014, 146, 1.0)
            tap(415, 823, 1.2)
    raise SystemExit("无法进入「图片与视频」页面，请手动打开梁蓝欣聊天的图片页后重试。")


def fallback_points() -> list[tuple[int, int]]:
    return [(x, y) for y in ROW_CENTERS if y <= 2050 for x in COL_X]


def back_to_gallery() -> None:
    for _ in range(3):
        if "ImageVideoSearchActivity" in current_focus():
            return
        back()


def scroll_to_top() -> None:
    for _ in range(10):
        adb("shell", "input", "swipe", "540", "500", "540", "1900", "450")
        time.sleep(0.35)


def save_current_screen(counter: list[int]) -> int:
    back_to_gallery()
    tree = dump_ui()
    pts = thumbnail_centers(tree) if tree else []
    if not pts:
        pts = fallback_points()
    saved_here = 0
    for x, y in pts:
        tap(x, y, 1.0)
        if "MediaPreviewerActivity" not in current_focus():
            continue
        save_open_image()
        counter[0] += 1
        saved_here += 1
        log(f"  [{counter[0]}] 已保存 ({x},{y})")
        back_to_gallery()
    return saved_here


def export_all() -> int:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = TEMP_DIR / "pulled"
    raw_dir.mkdir(parents=True, exist_ok=True)

    adb("shell", "settings", "put", "global", "window_animation_scale", "0")
    adb("shell", "settings", "put", "global", "transition_animation_scale", "0")
    adb("shell", "settings", "put", "global", "animator_duration_scale", "0")

    ensure_gallery()
    scroll_to_top()

    before = list_weixin_work_files()
    counter = [0]
    same = 0
    last_hash = ""
    for page in range(1, 41):
        tree = dump_ui()
        title = ""
        if tree:
            title = next(
                (n.attrib.get("text", "") for n in tree.getroot().iter("node") if n.attrib.get("text") == "图片与视频"),
                "",
            )
        if not title and page == 1:
            ensure_gallery()
            scroll_to_top()

        screen = TEMP_DIR / "page.png"
        screen.write_bytes(subprocess.check_output(["adb", "exec-out", "screencap", "-p"]))
        page_hash = hashlib.md5(screen.read_bytes()).hexdigest()
        if page_hash == last_hash:
            same += 1
            if same >= 2:
                break
        else:
            same = 0
        last_hash = page_hash

        n = save_current_screen(counter)
        log(f"第 {page} 屏保存 {n} 张, 累计 {counter[0]} 张")
        swipe_up()

    pulled = pull_new_files(before, raw_dir)
    log(f"已拉取 {len(pulled)} 张到电脑，开始识别工资条...")

    saved = 0
    for img in pulled:
        ok, text = is_salary(img)
        if not ok:
            log(f"- 跳过 {img.name}")
            continue
        dest = OUTPUT_DIR / f"工资条_{saved + 1:02d}_{img.name}"
        dest.write_bytes(img.read_bytes())
        saved += 1
        log(f"✓ [{saved}] {dest.name} | {text[:60]}")

    return saved


def main() -> int:
    out = adb("devices")
    if "\tdevice" not in out.stdout:
        raise SystemExit("未检测到 ADB 设备")
    log(f"输出目录: {OUTPUT_DIR}")
    n = export_all()
    log(f"\n完成：共保存 {n} 张工资条图片")
    return 0


if __name__ == "__main__":
    sys.exit(main())
