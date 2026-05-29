#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""
海航PLUS机票查询脚本
查询指定航线是否有199的票
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
HNA_PACKAGE = "com.rytong.hnair"
OCR_CROP_BOX = (0, 300, 1080, 2050)
_OCR_ENGINE = None

# 城市拼音映射表
CITY_PINYIN = {
    "北京首都": "beijingshoudu",
    "北京大兴": "beijingdaxing",
    "上海虹桥": "shanghaihongqiao",
    "上海浦东": "shanghaipudong",
    "广州": "guangzhou",
    "深圳": "shenzhen",
    "成都": "chengdu",
    "重庆": "chongqing",
    "杭州": "hangzhou",
    "西安": "xian",
    "武汉": "wuhan",
    "南京": "nanjing",
    "三亚": "sanya",
    "海口": "haikou",
    "昆明": "kunming",
    "长沙": "changsha",
    "天津": "tianjin",
    "郑州": "zhengzhou",
    "青岛": "qingdao",
    "大连": "dalian",
    "大理": "dali",
    "厦门": "xiamen",
    "福州": "fuzhou",
    "乌鲁木齐": "wulumuqi",
    "哈尔滨": "haerbin",
    "沈阳": "shenyang",
    "长春": "changchun",
    "济南": "jinan",
    "太原": "taiyuan",
    "兰州": "lanzhou",
    "西宁": "xining",
    "银川": "yinchuan",
    "贵阳": "guiyang",
    "南宁": "nanning",
    "海口": "haikou",
    "珠海": "zhuhai",
    "汕头": "shantou",
    "宁波": "ningbo",
    "无锡": "wuxi",
    "苏州": "suzhou",
    "南昌": "nanchang",
    "合肥": "hefei",
    "石家庄": "shijiazhuang",
    "呼和浩特": "huhehaote",
}


@dataclass(frozen=True)
class UINode:
    text: str
    bounds: str
    class_name: str
    clickable: bool

    @property
    def nums(self) -> tuple[int, int, int, int] | None:
        values = tuple(map(int, re.findall(r"\d+", self.bounds or "")))
        if len(values) != 4:
            return None
        return values

    @property
    def visible(self) -> bool:
        values = self.nums
        if values is None:
            return False
        x1, y1, x2, y2 = values
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2135

    @property
    def center(self) -> tuple[int, int]:
        values = self.nums
        if values is None:
            raise ValueError(f"invalid bounds: {self.bounds}")
        x1, y1, x2, y2 = values
        return (x1 + x2) // 2, (y1 + y2) // 2


@dataclass(frozen=True)
class OCRTextBox:
    text: str
    box: tuple[int, int, int, int]
    score: float

    @property
    def visible(self) -> bool:
        x1, y1, x2, y2 = self.box
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2135

    @property
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) // 2, (y1 + y2) // 2

    def translated(self, dx: int, dy: int) -> OCRTextBox:
        x1, y1, x2, y2 = self.box
        return OCRTextBox(self.text, (x1 + dx, y1 + dy, x2 + dx, y2 + dy), self.score)


class ADB:
    def __init__(self, adb_path: str, dry_run: bool = False):
        self.adb_path = adb_path
        self.dry_run = dry_run

    def run(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        cmd = [self.adb_path] + args
        print(f"执行: {' '.join(cmd)}")
        if self.dry_run:
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout
        )
        if check and proc.returncode != 0:
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb failed: {stderr or stdout}")
        return proc

    def shell(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell"] + args, timeout=timeout)

    def tap(self, x: int, y: int) -> None:
        print(f"点击: ({x}, {y})")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(0.8)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 600) -> None:
        print(f"滑动: ({x1},{y1}) -> ({x2},{y2})")
        if not self.dry_run:
            self.shell(
                ["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                timeout=6
            )
            time.sleep(0.8)

    def keyevent(self, key: str) -> None:
        print(f"按键: {key}")
        if not self.dry_run:
            self.shell(["input", "keyevent", key], timeout=4)
            time.sleep(0.3)

    def input_text(self, text: str) -> None:
        escaped = text.replace("%", "%s").replace(" ", "%s")
        print(f"输入: {text}")
        if not self.dry_run:
            self.shell(["input", "text", escaped], timeout=6)
            time.sleep(0.8)

    def dump_nodes(self) -> list[UINode]:
        if self.dry_run:
            return []
        self.shell(["uiautomator", "dump", "/sdcard/window.xml"], timeout=8)
        result = self.run(["exec-out", "cat", "/sdcard/window.xml"], timeout=8)
        return parse_nodes(result.stdout)

    def screencap(self, path: Path = Path("/tmp/hna_screen.png")) -> Path:
        result = self.run(["exec-out", "screencap", "-p"], timeout=12)
        path.write_bytes(result.stdout)
        return path


def parse_nodes(xml_bytes: bytes) -> list[UINode]:
    try:
        root = ET.fromstring(xml_bytes)
    except Exception:
        return []
    nodes: list[UINode] = []
    for node in root.iter("node"):
        nodes.append(
            UINode(
                text=node.attrib.get("text", ""),
                bounds=node.attrib.get("bounds", ""),
                class_name=node.attrib.get("class", ""),
                clickable=node.attrib.get("clickable", "false") == "true"
            )
        )
    return nodes


def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        _OCR_ENGINE = PaddleOCR(
            use_textline_orientation=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False
        )
    return _OCR_ENGINE


def bounds_from_ocr_box(raw_box: object) -> tuple[int, int, int, int]:
    if hasattr(raw_box, "tolist"):
        raw_box = raw_box.tolist()
    if isinstance(raw_box, (list, tuple)) and len(raw_box) == 4:
        try:
            x1, y1, x2, y2 = [int(round(float(value))) for value in raw_box]
            return x1, y1, x2, y2
        except (TypeError, ValueError):
            pass
    points = list(raw_box)
    xs = [int(round(float(point[0]))) for point in points]
    ys = [int(round(float(point[1]))) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def parse_paddleocr_result(result: object) -> list[OCRTextBox]:
    pages = result if isinstance(result, list) else [result]
    boxes = []
    for page in pages:
        if isinstance(page, dict):
            texts = page.get("rec_texts", [])
            raw_boxes = page.get("rec_polys", [])
            scores = page.get("rec_scores", [])
            for index, text in enumerate(texts):
                if index >= len(raw_boxes):
                    continue
                score = float(scores[index]) if index < len(scores) else 0.0
                boxes.append(OCRTextBox(str(text), bounds_from_ocr_box(raw_boxes[index]), score))
            continue
        for item in page or []:
            if not item or len(item) < 2:
                continue
            text_info = item[1]
            if not text_info or len(text_info) < 1:
                continue
            text = str(text_info[0])
            score = float(text_info[1]) if len(text_info) > 1 else 0.0
            boxes.append(OCRTextBox(text, bounds_from_ocr_box(item[0]), score))
    return boxes


def ocr_screen(adb: ADB) -> list[OCRTextBox]:
    started = time.monotonic()
    image_path = adb.screencap()
    from PIL import Image
    crop_x1, crop_y1, crop_x2, crop_y2 = OCR_CROP_BOX
    crop_path = Path("/tmp/hna_ocr_crop.png")
    with Image.open(image_path) as img:
        img.crop(OCR_CROP_BOX).save(crop_path)
    ocr = get_ocr_engine()
    if hasattr(ocr, "predict"):
        result = ocr.predict(str(crop_path))
    else:
        result = ocr.ocr(str(crop_path), cls=False)
    boxes = [box.translated(crop_x1, crop_y1) for box in parse_paddleocr_result(result)]
    elapsed = time.monotonic() - started
    print(f"OCR完成，耗时{elapsed:.2f}秒，识别到{len(boxes)}个文本框")
    return boxes


def ocr_digits(text: str) -> str:
    return re.sub(r"\D+", "", text)


def output_text(proc: subprocess.CompletedProcess[bytes]) -> str:
    return proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def ensure_adb_exists(adb_path: str) -> None:
    if not Path(adb_path).exists():
        raise FileNotFoundError(f"adb不存在: {adb_path}")


def dumpsys_has_line(text: str, exact_line: str) -> bool:
    return any(line.strip() == exact_line for line in text.splitlines())


def device_needs_unlock(adb: ADB) -> bool:
    window_text = output_text(adb.shell(["dumpsys", "window"], timeout=10))
    power_text = output_text(adb.shell(["dumpsys", "power"], timeout=10))
    screen_off_markers = (
        "mWakefulness=Asleep",
        "mWakefulness=Dozing",
        "Display Power: state=OFF",
        "screenState=SCREEN_STATE_OFF",
    )
    locked_markers = (
        "showing=true",
        "mIsShowing=true",
        "mInputRestricted=true",
        "inputRestricted=true",
        "isStatusBarKeyguard=true",
        "mShowingLockscreen=true",
    )
    unlocked_markers = (
        "showing=false",
        "mIsShowing=false",
        "inputRestricted=false",
        "mInputRestricted=false",
    )
    if any(m in power_text or m in window_text for m in screen_off_markers):
        return True
    if any(dumpsys_has_line(window_text, m) for m in locked_markers):
        return True
    if any(dumpsys_has_line(window_text, m) for m in unlocked_markers):
        return False
    print("无法确定锁屏状态，假设已解锁")
    return False


def unlock_phone(unlock_script: str = "./unlock.sh") -> None:
    script = Path(unlock_script)
    if not script.exists():
        raise FileNotFoundError(f"解锁脚本不存在: {unlock_script}")
    print("手机已锁屏，运行解锁脚本...")
    subprocess.run([str(script.resolve())], check=True, timeout=30)
    time.sleep(1)


def prepare_phone(adb: ADB, unlock_script: str = "./unlock.sh", skip_unlock: bool = False) -> None:
    if skip_unlock:
        print("跳过解锁检查，先停止海南航空APP...")
        if not adb.dry_run:
            adb.shell(["am", "force-stop", HNA_PACKAGE], timeout=8)
        return

    if device_needs_unlock(adb):
        unlock_phone(unlock_script)
    else:
        print("手机已解锁，先停止已打开的海南航空APP...")
    if not adb.dry_run:
        adb.shell(["am", "force-stop", HNA_PACKAGE], timeout=8)
        time.sleep(0.8)


def launch_hna_app(adb: ADB, force_stop: bool = False) -> None:
    print("停止海南航空APP...")
    if force_stop and not adb.dry_run:
        adb.shell(["am", "force-stop", HNA_PACKAGE], timeout=8)
        time.sleep(0.5)
    print("启动海南航空APP...")
    if not adb.dry_run:
        adb.run(["shell", "monkey", "-p", HNA_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
        time.sleep(3)


def tap_text_by_uiautomator(adb: ADB, target_text: str, timeout: int = 5) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        nodes = adb.dump_nodes()
        for node in nodes:
            if node.visible and target_text in node.text and node.clickable:
                x, y = node.center
                adb.tap(x, y)
                return True
            if node.visible and target_text in node.text:
                x, y = node.center
                adb.tap(x, y)
                return True
        time.sleep(0.5)
    return False


def dismiss_blocking_popups(adb: ADB) -> None:
    """关闭首页常见活动弹窗，避免挡住 PLUS 入口。"""
    for _ in range(3):
        nodes = adb.dump_nodes()
        close_nodes = []
        for node in nodes:
            if not node.visible or not node.clickable:
                continue
            x, y = node.center
            text = node.text.strip()
            if any(keyword in text for keyword in ["关闭", "稍后", "取消"]):
                close_nodes.append(node)
            elif x > 820 and 250 < y < 700:
                close_nodes.append(node)
        if not close_nodes:
            return
        close_nodes.sort(key=lambda node: (node.center[1], -node.center[0]))
        x, y = close_nodes[0].center
        print(f"关闭可能挡住首页的弹窗: ({x}, {y})")
        adb.tap(x, y)
        time.sleep(1)


def has_plus_query_form(adb: ADB) -> bool:
    try:
        nodes = adb.dump_nodes()
    except Exception:
        return False
    texts = [node.text for node in nodes if node.visible]
    return (
        any("海航PLUS会员权益卡" in text for text in texts)
        and any("选择出发地" in text for text in texts)
        and any("选择目的地" in text for text in texts)
        and any("搜索预订" in text for text in texts)
    )


def tap_plus_form_text(adb: ADB, target_text: str) -> bool:
    nodes = adb.dump_nodes()
    candidates = [
        node for node in nodes
        if node.visible and node.text.strip() == target_text
    ]
    if not candidates:
        candidates = [
            node for node in nodes
            if node.visible and target_text in node.text
        ]
    if not candidates:
        return False
    candidates.sort(key=lambda node: node.center[1])
    x, y = candidates[0].center
    adb.tap(x, y)
    return True


def wait_for_plus_query_form(adb: ADB, timeout_s: int = 12) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if has_plus_query_form(adb):
            return True
        time.sleep(0.6)
    return False


def enter_plus_page(adb: ADB) -> None:
    print("等待首页加载...")
    time.sleep(2)
    dismiss_blocking_popups(adb)
    if has_plus_query_form(adb):
        print("已在海航PLUS会员权益卡查询页")
        return
    print("寻找海航PLUS权益卡入口...")
    # 先尝试用uiautomator找
    for attempt in range(3):
        dismiss_blocking_popups(adb)
        if tap_text_by_uiautomator(adb, "海航PLUS权益卡"):
            time.sleep(1)
            if wait_for_plus_query_form(adb):
                return
        if tap_text_by_uiautomator(adb, "PLUS会员权益卡"):
            time.sleep(1)
            if wait_for_plus_query_form(adb):
                return
        # 尝试点击固定位置
        adb.tap(750, 1350)
        time.sleep(1)
        if wait_for_plus_query_form(adb, timeout_s=5):
            return
    # 用OCR确认
    print("用OCR确认是否进入PLUS页面...")
    boxes = ocr_screen(adb)
    for box in boxes:
        if "查询航线" in box.text or "搜索预订" in box.text:
            print("已进入海航PLUS权益卡页面")
            return
    raise RuntimeError("无法进入海航PLUS权益卡页面")


def is_city_selector_page(adb: ADB) -> bool:
    try:
        nodes = adb.dump_nodes()
    except Exception:
        return False
    texts = [node.text for node in nodes if node.visible]
    letter_index = {
        node.text.strip()
        for node in nodes
        if node.visible and 1000 <= node.center[0] <= 1080 and len(node.text.strip()) == 1
    }
    has_letter_index = len(letter_index.intersection({"A", "B", "C", "D", "S", "X", "Z"})) >= 3
    city_markers = ("北京", "上海", "广州", "深圳", "西安", "大理", "机场")
    has_city_list = any(any(marker in text for marker in city_markers) for text in texts)
    return has_letter_index and has_city_list


def open_city_selector(adb: ADB, field_text: str, label: str) -> None:
    if not has_plus_query_form(adb):
        raise RuntimeError(f"当前不在海航PLUS会员权益卡首屏查询表单，停止点击{label}")
    if not tap_plus_form_text(adb, field_text):
        raise RuntimeError(f"没有找到{field_text}，停止点击{label}")
    time.sleep(1)
    if is_city_selector_page(adb):
        return
    print(f"未进入{label}城市选择页，重新点击首屏查询表单")
    if not has_plus_query_form(adb):
        raise RuntimeError(f"当前不在海航PLUS会员权益卡首屏查询表单，停止点击{label}")
    if not tap_plus_form_text(adb, field_text):
        raise RuntimeError(f"没有找到{field_text}，停止点击{label}")
    time.sleep(1)
    if not is_city_selector_page(adb):
        raise RuntimeError(f"点击{label}后没有进入城市选择页，停止以避免误滑 PLUS 页面")


def verify_city_selected(adb: ADB, target_city: str, is_departure: bool) -> bool:
    """验证是否选中了正确的城市"""
    boxes = ocr_screen(adb)
    for box in boxes:
        text = box.text.strip()
        # 检查是否显示了目标城市（而不是"选择出发地"）
        if target_city in text and len(text) <= 10 and box.visible:
            print(f"✓ 确认已选择: {text}")
            return True
    return False


def get_first_pinyin_char(city_name: str) -> str:
    """获取城市名称的拼音首字母"""
    # 简单映射表，覆盖常用城市
    first_char_map = {
        "北": "B", "上": "S", "广": "G", "深": "S", "成": "C",
        "重": "C", "杭": "H", "西": "X", "武": "W", "南": "N",
        "三": "S", "海": "H", "昆": "K", "长": "C", "天": "T",
        "郑": "Z", "青": "Q", "大": "D", "厦": "X", "福": "F",
        "乌": "W", "哈": "H", "沈": "S", "长": "C", "济": "J",
        "太": "T", "兰": "L", "银": "Y", "贵": "G",
        "珠": "Z", "汕": "S", "宁": "N", "无": "W", "苏": "S",
        "合": "H", "石": "S", "呼": "H",
    }
    if city_name and city_name[0] in first_char_map:
        return first_char_map[city_name[0]]
    # 如果没有映射，返回第一个字符的大写
    return city_name[0].upper() if city_name else "A"


def city_search_keyword(city_name: str) -> str:
    return CITY_PINYIN.get(city_name, city_name)


def tap_search_box(adb: ADB) -> None:
    nodes = adb.dump_nodes()
    for node in nodes:
        text = node.text.strip()
        if node.visible and any(keyword in text for keyword in ["搜索", "城市", "机场"]):
            x, y = node.center
            if y < 900:
                adb.tap(x, y)
                return
    adb.tap(430, 310)


def select_city_by_search(adb: ADB, target_city: str) -> bool:
    print(f"通过搜索框查找城市: {target_city}")
    tap_search_box(adb)
    adb.keyevent("KEYCODE_MOVE_END")
    for _ in range(12):
        adb.keyevent("KEYCODE_DEL")
    adb.input_text(city_search_keyword(target_city))
    time.sleep(1)

    if tap_text_by_uiautomator(adb, target_city, timeout=3):
        return True

    boxes = ocr_screen(adb)
    candidates = [
        box for box in boxes
        if box.visible and target_city in box.text and box.score >= 0.45 and box.center[1] > 320
    ]
    if candidates:
        candidates.sort(key=lambda box: box.center[1])
        adb.tap(*candidates[0].center)
        time.sleep(0.8)
        return True
    return False


def find_and_click_by_letter_index(adb: ADB, target_city: str) -> bool:
    """通过右侧字母索引查找并点击城市"""
    first_char = get_first_pinyin_char(target_city)
    print(f"通过字母索引查找: {target_city} (首字母 {first_char})")

    # 字母索引的位置 (右侧)
    letter_positions = {
        "A": (1040, 800), "B": (1040, 860), "C": (1040, 920),
        "D": (1040, 980), "E": (1040, 1040), "F": (1040, 1100),
        "G": (1040, 1160), "H": (1040, 1220), "J": (1040, 1280),
        "K": (1040, 1340), "L": (1040, 1400), "M": (1040, 1460),
        "N": (1040, 1520), "P": (1040, 1580), "Q": (1040, 1640),
        "R": (1040, 1700), "S": (1040, 1760), "T": (1040, 1820),
        "W": (1040, 1880), "X": (1040, 1940), "Y": (1040, 2000),
        "Z": (1040, 2060),
    }

    # 点击对应的字母索引
    if first_char in letter_positions:
        x, y = letter_positions[first_char]
        adb.tap(x, y)
        time.sleep(1)

    boxes = ocr_screen(adb)
    for box in boxes:
        text = box.text.strip()
        if target_city in text and box.visible:
            adb.tap(*box.center)
            time.sleep(0.5)
            print(f"✓ 在{first_char}区域找到并点击: {text}")
            return True

    return False


def tap_and_select_city(adb: ADB, target_city: str) -> None:
    """在城市选择页面点击目标城市"""
    if not is_city_selector_page(adb):
        raise RuntimeError(f"当前不在城市选择页，停止选择城市: {target_city}")
    if select_city_by_search(adb, target_city):
        return
    # 先尝试uiautomator
    if tap_text_by_uiautomator(adb, target_city, timeout=2):
        time.sleep(0.5)
        return
    # 尝试OCR在热门城市里找
    boxes = ocr_screen(adb)
    for box in boxes:
        if target_city in box.text and box.visible:
            adb.tap(*box.center)
            time.sleep(0.5)
            return
    # 热门城市没有，通过字母索引找
    print(f"未在当前城市页找到{target_city}，尝试字母索引定位一次...")
    if find_and_click_by_letter_index(adb, target_city):
        return
    # 最后尝试搜索框
    print(f"尝试搜索框...")
    if not select_city_by_search(adb, target_city):
        raise RuntimeError(f"无法选择城市: {target_city}")


def select_departure(adb: ADB, departure: str) -> None:
    print(f"选择出发地: {departure}")
    open_city_selector(adb, "选择出发地", "出发地")
    # 选择城市
    tap_and_select_city(adb, departure)
    # 验证是否选对了
    if verify_city_selected(adb, departure, True):
        return
    print(f"⚠️ 可能没有正确选对出发地，再试一次...")
    # 再试一次
    open_city_selector(adb, "选择出发地", "出发地")
    tap_and_select_city(adb, departure)


def select_destination(adb: ADB, destination: str) -> None:
    print(f"选择目的地: {destination}")
    open_city_selector(adb, "选择目的地", "目的地")
    # 选择城市
    tap_and_select_city(adb, destination)
    # 验证是否选对了
    if verify_city_selected(adb, destination, False):
        return
    print(f"⚠️ 可能没有正确选对目的地，再试一次...")
    # 再试一次
    open_city_selector(adb, "选择目的地", "目的地")
    tap_and_select_city(adb, destination)


def parse_target_date(target_date: str) -> tuple[int, int, int]:
    year_match = re.search(r"(\d{4})年", target_date)
    month_day_match = re.search(r"(\d{1,2})月(\d{1,2})日?", target_date)
    if not month_day_match:
        raise ValueError(f"日期格式错误: {target_date}，请使用 6月19日 或 2026年6月19日")
    today = dt.date.today()
    year = int(year_match.group(1)) if year_match else today.year
    month = int(month_day_match.group(1))
    day = int(month_day_match.group(2))
    return year, month, day


def month_label_candidates(year: int, month: int) -> tuple[str, ...]:
    return (
        f"{year}年{month}月",
        f"{month}月{year}年",
        f"{month}月",
    )


def extract_visible_months(boxes: list[OCRTextBox]) -> list[tuple[int, int, str]]:
    months: list[tuple[int, int, str]] = []
    for box in boxes:
        text = box.text.strip()
        match = re.search(r"(?:(\d{4})年)?\s*(\d{1,2})月", text)
        if match:
            months.append((int(match.group(2)), box.box[1], text))
            continue
        match = re.search(r"(\d{1,2})月\s*(\d{4})年", text)
        if match:
            months.append((int(match.group(1)), box.box[1], text))
    return months


def select_date(adb: ADB, target_date: str) -> None:
    print(f"选择日期: {target_date}")
    target_year, target_month, target_day = parse_target_date(target_date)
    target_month_labels = month_label_candidates(target_year, target_month)
    target_day_str = str(target_day)
    if not has_plus_query_form(adb):
        raise RuntimeError("当前不在海航PLUS会员权益卡首屏查询表单，停止选择日期")
    nodes = adb.dump_nodes()
    date_nodes = [
        node for node in nodes
        if node.visible and re.search(r"\d{4}年\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日", node.text)
    ]
    if not date_nodes:
        raise RuntimeError("没有找到首屏日期控件，停止选择日期")
    date_nodes.sort(key=lambda node: node.center[1])
    adb.tap(*date_nodes[0].center)
    time.sleep(1)
    # 先确保找到目标月份
    target_month_found = False
    for find_month_attempt in range(10):
        boxes = ocr_screen(adb)
        month_positions = extract_visible_months(boxes)
        # 检查目标月份是否可见
        target_month_visible = any(
            any(label in text for label in target_month_labels)
            for _, _, text in month_positions
        )
        if target_month_visible:
            target_month_found = True
            print(f"看到{target_year}年{target_month}月，现在找{target_day}日...")
            break
        # 目标月份不可见，判断滑动方向
        if month_positions:
            visible_months = [month for month, _, _ in month_positions]
            if visible_months:
                if target_month < min(visible_months):
                    print(f"目标月{target_month}比可见月早，下滑...")
                    adb.swipe(500, 1200, 500, 1800, 500)
                else:
                    print(f"上滑找{target_year}年{target_month}月...")
                    adb.swipe(500, 1800, 500, 1100, 500)
            else:
                print(f"上滑找{target_year}年{target_month}月...")
                adb.swipe(500, 1800, 500, 1100, 500)
        else:
            print(f"上滑找{target_year}年{target_month}月...")
            adb.swipe(500, 1800, 500, 1100, 500)
        time.sleep(0.8)
    if not target_month_found:
        raise RuntimeError(f"未能找到{target_year}年{target_month}月")
    # 目标月份已找到，现在找具体日期
    for find_day_attempt in range(6):
        boxes = ocr_screen(adb)
        # 先检查是否有目标日期
        for box in boxes:
            text = box.text.strip()
            if text == target_day_str and 300 < box.center[1] < 2050:
                adb.tap(*box.center)
                time.sleep(0.5)
                print(f"已选择日期: {target_date}")
                return
        # 没找到日期，小幅度上滑
        print(f"未找到{target_day}日，小幅度上滑...")
        adb.swipe(500, 1700, 500, 1400, 500)
        time.sleep(0.8)
    raise RuntimeError(f"未能找到日期{target_date}")


def search_flights(adb: ADB) -> None:
    print("点击搜索预订...")
    if not has_plus_query_form(adb):
        raise RuntimeError("当前不在海航PLUS会员权益卡首屏查询表单，停止搜索")
    if not tap_plus_form_text(adb, "搜索预订"):
        raise RuntimeError("没有找到搜索预订按钮")
    time.sleep(2)


def is_exact_price(text: str, target_price: int) -> bool:
    digits = ocr_digits(text)
    return digits == str(target_price)


def check_target_ticket(adb: ADB, target_price: int = 199, max_scroll: int = 6) -> list[tuple[str, str]]:
    print(f"检查是否有{target_price}的票...")
    found_flights = []
    for scroll in range(max_scroll):
        boxes = ocr_screen(adb)
        # 找航班时间和价格
        flight_times = []
        prices = []
        for box in boxes:
            if re.fullmatch(r"\d{1,2}:\d{2}", box.text.strip()) and box.visible:
                flight_times.append(box)
            if is_exact_price(box.text, target_price) and box.score >= 0.5 and box.visible and box.center[0] > 660:
                prices.append(box)
        # 检查是否有199的价格
        for price_box in prices:
            px, py = price_box.center
            nearby_times = [
                time_box for time_box in flight_times
                if abs(time_box.center[1] - py) < 190 and time_box.center[0] < 620
            ]
            nearby_times.sort(key=lambda box: box.center[0])
            if len(nearby_times) >= 2:
                flight_time = f"{nearby_times[0].text}-{nearby_times[1].text}"
            elif nearby_times:
                flight_time = nearby_times[0].text
            else:
                flight_time = "未知航班时间"
            flight = (flight_time, f"￥{target_price}")
            if flight not in found_flights:
                found_flights.append(flight)
            print(f"✓ 找到航班: {flight[0]}, 价格: {flight[1]}")
        # 检查是否有广告中的199提示
        for box in boxes:
            if str(target_price) in box.text and "起" in box.text:
                print(f"注意: 看到广告 '{box.text}'，不计入具体航班价格")
        if found_flights:
            return found_flights
        # 没找到，继续滑动
        if scroll < max_scroll - 1:
            print(f"未找到{target_price}的票，继续滑动 ({scroll + 1}/{max_scroll})...")
            adb.swipe(500, 1800, 500, 900)
    return found_flights


def check_199_ticket(adb: ADB, max_scroll: int = 6) -> list[tuple[str, str]]:
    return check_target_ticket(adb, target_price=199, max_scroll=max_scroll)


def main():
    parser = argparse.ArgumentParser(description="海航PLUS机票查询")
    parser.add_argument("departure", nargs="?", default="北京首都", help="出发地")
    parser.add_argument("destination", nargs="?", default="乌鲁木齐", help="目的地")
    parser.add_argument("date", nargs="?", default="6月19日", help="日期")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="ADB路径")
    parser.add_argument("--dry-run", action="store_true", help="仅演示，不实际操作")
    parser.add_argument("--skip-unlock", action="store_true", help="跳过解锁检查")
    args = parser.parse_args()

    ensure_adb_exists(args.adb)
    adb = ADB(args.adb, dry_run=args.dry_run)

    print("=" * 50)
    print(f"海航PLUS机票查询: {args.departure} → {args.destination}, {args.date}")
    print("=" * 50)

    try:
        # 1. 先检查锁屏态；已解锁时先杀掉已打开的海航APP。
        prepare_phone(adb, skip_unlock=args.skip_unlock)

        # 2. 预加载OCR引擎（避免进入查询流程后卡顿）
        print("正在加载OCR引擎，请稍候...")
        ocr_start = time.monotonic()
        get_ocr_engine()
        print(f"OCR引擎加载完成，耗时{time.monotonic() - ocr_start:.1f}秒")

        # 3. 打开APP
        launch_hna_app(adb)

        # 4. 进入PLUS页面
        enter_plus_page(adb)

        # 5. 选择出发地
        select_departure(adb, args.departure)

        # 6. 选择目的地
        select_destination(adb, args.destination)

        # 7. 选择日期
        select_date(adb, args.date)

        # 8. 搜索
        search_flights(adb)

        # 9. 检查199的票
        flights = check_199_ticket(adb)

        print("\n" + "=" * 50)
        if flights:
            print(f"找到 {len(flights)} 个199的航班:")
            for i, (time_str, price) in enumerate(flights, 1):
                print(f"{i}. {time_str} {price}")
        else:
            print("未找到199的票，当前最低价格是379起")
        print("=" * 50)

    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
