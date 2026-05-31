#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""Query HNA PLUS member fares with ADB.

Example:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python hna_plus_query.py 北京大兴 海口 6月19日 --price 199 --execute
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
HNA_PACKAGE = "com.rytong.hnair"
SCREEN_W = 1080
SCREEN_H = 2340

CITY_LETTERS = {
    '安': 'A',
    '阿': 'A',
    '鞍': 'A',
    '亳': 'B',
    '保': 'B',
    '包': 'B',
    '北': 'B',
    '博': 'B',
    '巴': 'B',
    '毕': 'B',
    '白': 'B',
    '百': 'B',
    '蚌': 'B',
    '常': 'C',
    '成': 'C',
    '昌': 'C',
    '池': 'C',
    '沧': 'C',
    '赤': 'C',
    '郴': 'C',
    '重': 'C',
    '长': 'C',
    '东': 'D',
    '大': 'D',
    '敦': 'D',
    '稻': 'D',
    '达': 'D',
    '迪': 'D',
    '二': 'E',
    '恩': 'E',
    '鄂': 'E',
    '富': 'F',
    '福': 'F',
    '阜': 'F',
    '固': 'G',
    '广': 'G',
    '格': 'G',
    '桂': 'G',
    '贵': 'G',
    '赣': 'G',
    '合': 'H',
    '呼': 'H',
    '和': 'H',
    '哈': 'H',
    '怀': 'H',
    '惠': 'H',
    '杭': 'H',
    '汉': 'H',
    '河': 'H',
    '海': 'H',
    '淮': 'H',
    '菏': 'H',
    '衡': 'H',
    '邯': 'H',
    '霍': 'H',
    '黄': 'H',
    '九': 'J',
    '井': 'J',
    '佳': 'J',
    '加': 'J',
    '嘉': 'J',
    '揭': 'J',
    '景': 'J',
    '济': 'J',
    '荆': 'J',
    '金': 'J',
    '锦': 'J',
    '鸡': 'J',
    '克': 'K',
    '凯': 'K',
    '喀': 'K',
    '库': 'K',
    '昆': 'K',
    '临': 'L',
    '丽': 'L',
    '六': 'L',
    '兰': 'L',
    '吕': 'L',
    '拉': 'L',
    '林': 'L',
    '柳': 'L',
    '泸': 'L',
    '洛': 'L',
    '澜': 'L',
    '荔': 'L',
    '连': 'L',
    '阆': 'L',
    '陇': 'L',
    '梅': 'M',
    '满': 'M',
    '漠': 'M',
    '牡': 'M',
    '绵': 'M',
    '芒': 'M',
    '南': 'N',
    '宁': 'N',
    '攀': 'P',
    '普': 'P',
    '奇': 'Q',
    '庆': 'Q',
    '泉': 'Q',
    '琼': 'Q',
    '秦': 'Q',
    '青': 'Q',
    '黔': 'Q',
    '日': 'R',
    '若': 'R',
    '三': 'S',
    '上': 'S',
    '十': 'S',
    '松': 'S',
    '沈': 'S',
    '深': 'S',
    '石': 'S',
    '莎': 'S',
    '邵': 'S',
    '韶': 'S',
    '台': 'T',
    '吐': 'T',
    '唐': 'T',
    '图': 'T',
    '塔': 'T',
    '天': 'T',
    '太': 'T',
    '腾': 'T',
    '通': 'T',
    '铜': 'T',
    '万': 'W',
    '乌': 'W',
    '威': 'W',
    '文': 'W',
    '无': 'W',
    '梧': 'W',
    '武': 'W',
    '温': 'W',
    '潍': 'W',
    '芜': 'W',
    '信': 'X',
    '兴': 'X',
    '厦': 'X',
    '徐': 'X',
    '忻': 'X',
    '新': 'X',
    '湘': 'X',
    '襄': 'X',
    '西': 'X',
    '邢': 'X',
    '锡': 'X',
    '义': 'Y',
    '于': 'Y',
    '伊': 'Y',
    '宜': 'Y',
    '岳': 'Y',
    '延': 'Y',
    '扬': 'Y',
    '榆': 'Y',
    '永': 'Y',
    '烟': 'Y',
    '玉': 'Y',
    '盐': 'Y',
    '营': 'Y',
    '银': 'Y',
    '中': 'Z',
    '张': 'Z',
    '扎': 'Z',
    '昭': 'Z',
    '湛': 'Z',
    '珠': 'Z',
    '舟': 'Z',
    '遵': 'Z',
    '郑': 'Z',
}


@dataclass(frozen=True)
class UINode:
    text: str
    bounds: str
    clickable: bool

    @property
    def nums(self) -> tuple[int, int, int, int] | None:
        values = tuple(map(int, re.findall(r"\d+", self.bounds or "")))
        return values if len(values) == 4 else None

    @property
    def visible(self) -> bool:
        values = self.nums
        if values is None:
            return False
        x1, y1, x2, y2 = values
        return x2 > x1 and y2 > y1 and y2 > 75 and y1 < 2210

    @property
    def center(self) -> tuple[int, int]:
        values = self.nums
        if values is None:
            raise ValueError(f"invalid bounds: {self.bounds}")
        x1, y1, x2, y2 = values
        return (x1 + x2) // 2, (y1 + y2) // 2


class ADB:
    def __init__(self, adb_path: str, execute: bool) -> None:
        self.adb_path = adb_path
        self.execute = execute

    def run(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        cmd = [self.adb_path, *args]
        print("$", " ".join(cmd))
        if not self.execute and args[:1] == ["shell"] and args[1:2] == ["input"]:
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if check and proc.returncode != 0:
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb {' '.join(args)} failed: {stderr or stdout}")
        return proc

    def shell(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell", *args], timeout=timeout)

    def tap(self, x: int, y: int) -> None:
        print(f"tap {x} {y}")
        if self.execute:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(0.7)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 450) -> None:
        print(f"swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if self.execute:
            self.shell(
                ["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                timeout=6,
            )
            time.sleep(0.8)

    def keyevent(self, key: str) -> None:
        print(f"keyevent {key}")
        if self.execute:
            self.shell(["input", "keyevent", key], timeout=4)
            time.sleep(0.6)

    def dump_nodes(self) -> list[UINode]:
        proc = self.run(["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=8, check=False)
        if proc.returncode != 0 and b"UI hierchary dumped to:" not in proc.stdout + proc.stderr:
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb shell uiautomator dump /sdcard/window.xml failed: {stderr or stdout}")
        proc = self.run(["exec-out", "cat", "/sdcard/window.xml"], timeout=8)
        return parse_nodes(proc.stdout)


def parse_nodes(xml_bytes: bytes) -> list[UINode]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return []
    nodes: list[UINode] = []
    for node in root.iter("node"):
        nodes.append(
            UINode(
                text=node.attrib.get("text", ""),
                bounds=node.attrib.get("bounds", ""),
                clickable=node.attrib.get("clickable", "false") == "true",
            )
        )
    return nodes


def output_text(proc: subprocess.CompletedProcess[bytes]) -> str:
    return proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def dumpsys_has_line(text: str, exact_line: str) -> bool:
    return any(line.strip() == exact_line for line in text.splitlines())


def device_needs_unlock(adb: ADB) -> bool:
    window_text = output_text(adb.shell(["dumpsys", "window"], timeout=10))
    power_text = output_text(adb.shell(["dumpsys", "power"], timeout=10))
    if any(marker in power_text or marker in window_text for marker in (
        "mWakefulness=Asleep",
        "mWakefulness=Dozing",
        "Display Power: state=OFF",
        "screenState=SCREEN_STATE_OFF",
    )):
        return True
    if any(dumpsys_has_line(window_text, marker) for marker in (
        "showing=true",
        "mIsShowing=true",
        "mInputRestricted=true",
        "inputRestricted=true",
        "isStatusBarKeyguard=true",
        "mShowingLockscreen=true",
    )):
        return True
    return False


def prepare_phone(adb: ADB, unlock_script: str) -> bool:
    unlocked_before_prepare = not device_needs_unlock(adb)
    if not unlocked_before_prepare:
        print("screen locked/off; running unlock script")
        subprocess.run([str(Path(unlock_script).resolve())], check=True, timeout=40)
        time.sleep(1)
    else:
        print("screen unlocked")
    return unlocked_before_prepare


def force_stop_hna(adb: ADB) -> None:
    print("force-stop HNA app")
    adb.shell(["am", "force-stop", HNA_PACKAGE], timeout=8)
    time.sleep(0.8)


def parse_foreground_package(window_text: str) -> str | None:
    patterns = (
        r"mCurrentFocus=Window\{[^}]*\s([a-zA-Z0-9_.]+)/",
        r"mFocusedApp=ActivityRecord\{[^}]*\s([a-zA-Z0-9_.]+)/",
        r"topResumedActivity=ActivityRecord\{[^}]*\s([a-zA-Z0-9_.]+)/",
    )
    for pattern in patterns:
        match = re.search(pattern, window_text)
        if match:
            return match.group(1)
    if HNA_PACKAGE in window_text:
        return HNA_PACKAGE
    return None


def foreground_package(adb: ADB) -> str | None:
    window_text = output_text(adb.shell(["dumpsys", "window"], timeout=10))
    return parse_foreground_package(window_text)


def is_hna_foreground(adb: ADB) -> bool:
    package = foreground_package(adb)
    print(f"foreground package: {package or 'unknown'}")
    return package == HNA_PACKAGE


def launch_hna(adb: ADB) -> None:
    adb.run(["shell", "monkey", "-p", HNA_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
    time.sleep(3)


def visible_texts(nodes: list[UINode]) -> list[str]:
    return [node.text.strip() for node in nodes if node.visible and node.text.strip()]


def has_text(nodes: list[UINode], text: str) -> bool:
    return any(text in node.text for node in nodes if node.visible)


def is_plus_form(nodes: list[UINode]) -> bool:
    texts = visible_texts(nodes)
    return (
        any("海航PLUS会员权益卡" in t for t in texts)
        and any("搜索预订" in t for t in texts)
        and any(re.search(r"\d{4}年\d{1,2}月\d{1,2}日", t) for t in texts)
    )


def is_hna_home(nodes: list[UINode]) -> bool:
    return not is_plus_form(nodes) and (
        has_text(nodes, "海航PLUS权益卡")
        or has_text(nodes, "PLUS会员权益卡")
    )


def is_date_picker(nodes: list[UINode]) -> bool:
    texts = visible_texts(nodes)
    return not is_plus_form(nodes) and (
        any(text == "请选择日期" for text in texts)
        or (
            any(text == "取消" for text in texts)
            and any(text == "确定" for text in texts)
            and any(re.fullmatch(r"\d{4}", text) for text in texts)
            and any(text == "月" for text in texts)
        )
    )


def is_flight_results_page(nodes: list[UINode]) -> bool:
    return not is_plus_form(nodes) and (
        has_text(nodes, "起飞时间")
        or has_text(nodes, "到达时间")
        or has_text(nodes, "排序")
        or has_text(nodes, "筛选")
    )


def is_city_picker(nodes: list[UINode]) -> bool:
    texts = visible_texts(nodes)
    return any("请选择出发地" in t or "请选择到达地" in t for t in texts)


def is_recoverable_plus_child_page(nodes: list[UINode]) -> bool:
    return not is_plus_form(nodes) and (
        is_flight_results_page(nodes)
        or is_date_picker(nodes)
        or is_city_picker(nodes)
    )


def wait_for(adb: ADB, predicate, timeout_s: int, interval_s: float = 0.6) -> list[UINode]:
    deadline = time.time() + timeout_s
    last_nodes: list[UINode] = []
    while time.time() < deadline:
        last_nodes = adb.dump_nodes()
        if predicate(last_nodes):
            return last_nodes
        time.sleep(interval_s)
    return last_nodes


def tap_text(adb: ADB, text: str, nodes: list[UINode] | None = None) -> bool:
    nodes = nodes or adb.dump_nodes()
    matches = [node for node in nodes if node.visible and text in node.text]
    if not matches:
        return False
    matches.sort(key=lambda n: (n.center[1], n.center[0]))
    adb.tap(*matches[0].center)
    return True


def dismiss_home_popups(adb: ADB) -> None:
    for _ in range(4):
        nodes = adb.dump_nodes()
        close_nodes = [
            node for node in nodes
            if node.visible and node.clickable and node.center[0] > 820 and 250 < node.center[1] < 700
        ]
        if not close_nodes:
            return
        close_nodes.sort(key=lambda n: (n.center[1], -n.center[0]))
        adb.tap(*close_nodes[0].center)
        time.sleep(1)


def return_to_plus_or_home(adb: ADB, max_steps: int = 5) -> list[UINode]:
    nodes = adb.dump_nodes()
    for _ in range(max_steps):
        nodes = adb.dump_nodes()
        if is_plus_form(nodes) or is_hna_home(nodes):
            return nodes
        if is_recoverable_plus_child_page(nodes):
            print("detected HNA PLUS child page; backing toward PLUS form")
        elif tap_text(adb, "首页", nodes):
            print("tapped home tab")
            time.sleep(1)
            dismiss_home_popups(adb)
            nodes = adb.dump_nodes()
            if is_plus_form(nodes) or is_hna_home(nodes):
                return nodes
            continue
        adb.keyevent("BACK")
    return adb.dump_nodes()


def ensure_hna_plus_form(adb: ADB, unlocked_before_prepare: bool) -> None:
    if not unlocked_before_prepare:
        force_stop_hna(adb)
        launch_hna(adb)
        enter_plus_form(adb)
        return

    if not is_hna_foreground(adb):
        print("HNA app is not foreground; launching")
        launch_hna(adb)
        enter_plus_form(adb)
        return

    nodes = return_to_plus_or_home(adb)
    if is_plus_form(nodes):
        print("already on HNA PLUS query form")
        return
    if is_hna_home(nodes):
        print("already on HNA home; entering PLUS query form")
        enter_plus_form(adb)
        return

    print("current HNA page is not recognized; going through launcher entry")
    launch_hna(adb)
    nodes = return_to_plus_or_home(adb)
    if not is_plus_form(nodes):
        enter_plus_form(adb)


def enter_plus_form(adb: ADB) -> None:
    if device_needs_unlock(adb):
        raise RuntimeError("phone locked while entering HNA PLUS query form")
    deadline = time.time() + 12
    nodes: list[UINode] = []
    while time.time() < deadline:
        dismiss_home_popups(adb)
        nodes = adb.dump_nodes()
        if is_plus_form(nodes) or has_text(nodes, "海航PLUS权益卡"):
            break
        time.sleep(0.6)
    if is_plus_form(nodes):
        return
    if not tap_text(adb, "海航PLUS权益卡", nodes):
        # Home card observed on this device.
        adb.tap(743, 1410)
    deadline = time.time() + 12
    while time.time() < deadline:
        dismiss_home_popups(adb)
        nodes = adb.dump_nodes()
        if is_plus_form(nodes):
            break
        time.sleep(0.6)
    if not is_plus_form(nodes):
        raise RuntimeError("could not enter HNA PLUS query form")


def tap_form_field(adb: ADB, side: str) -> None:
    nodes = adb.dump_nodes()
    candidates: list[UINode] = []
    for node in nodes:
        if not node.visible or not node.clickable:
            continue
        x1, y1, x2, y2 = node.nums or (0, 0, 0, 0)
        if not (1250 <= y1 <= 1550):
            continue
        if side == "left" and x1 < 520 and x2 <= 560:
            candidates.append(node)
        elif side == "right" and x1 >= 520:
            candidates.append(node)
    if not candidates:
        raise RuntimeError(f"could not find {side} city field")
    candidates.sort(key=lambda n: ((0 if n.text.strip() else 1), n.center[1], n.center[0]))
    adb.tap(*candidates[0].center)


def normalize_city(text: str) -> str:
    return re.sub(r"\s+", "", text).replace("国际", "").replace("机场", "")


def city_matches(current: str | None, expected: str) -> bool:
    if not current:
        return False
    current_norm = normalize_city(current)
    expected_norm = normalize_city(expected)
    return bool(current_norm and expected_norm and (expected_norm in current_norm or current_norm in expected_norm))


def current_form_city(nodes: list[UINode], side: str) -> str | None:
    candidates: list[UINode] = []
    for node in nodes:
        if not node.visible or not node.text.strip():
            continue
        x1, y1, x2, y2 = node.nums or (0, 0, 0, 0)
        if not (1280 <= y1 <= 1505):
            continue
        if side == "left" and x1 < 520 and x2 <= 560:
            candidates.append(node)
        elif side == "right" and x1 >= 520:
            candidates.append(node)
    placeholders = ("选择出发地", "选择目的地", "出发地", "目的地", "单程", "往返")
    values = [
        node.text.strip()
        for node in sorted(candidates, key=lambda n: (n.center[1], n.center[0]))
        if not any(mark in node.text for mark in placeholders)
    ]
    return values[0] if values else None


def city_label_matches(nodes: list[UINode], city: str) -> list[UINode]:
    return [node for node in nodes if node.visible and city in node.text.strip()]


def city_target_letter(city: str) -> str | None:
    city = city.strip()
    return CITY_LETTERS.get(city[0]) if city else None


def tap_city(adb: ADB, city: str) -> None:
    nodes = adb.dump_nodes()
    matches = city_label_matches(nodes, city)
    letter = city_target_letter(city)
    if not matches and letter:
        letter_nodes = [
            node for node in nodes
            if node.visible and node.text.strip() == letter and node.center[0] > 1000
        ]
        if letter_nodes:
            adb.tap(*letter_nodes[0].center)
            time.sleep(0.8)
            nodes = adb.dump_nodes()
            matches = city_label_matches(nodes, city)
    if not matches:
        # Some city item labels are not themselves clickable, but their parent card shares the same area.
        all_label_nodes = city_label_matches(nodes, city)
        if all_label_nodes:
            matches = all_label_nodes
    if not matches:
        raise RuntimeError(f"could not find city {city} on current city picker")
    matches.sort(key=lambda n: (n.center[1], n.center[0]))
    adb.tap(*matches[0].center)


def select_city(adb: ADB, side: str, city: str) -> None:
    nodes = adb.dump_nodes()
    current_city = current_form_city(nodes, side) if is_plus_form(nodes) else None
    if city_matches(current_city, city):
        print(f"{side} city already {current_city}; skip selecting {city}")
        return
    tap_form_field(adb, side)
    nodes = wait_for(adb, is_city_picker, timeout_s=6)
    if not is_city_picker(nodes):
        raise RuntimeError("city picker did not open")
    tap_city(adb, city)
    wait_for(adb, is_plus_form, timeout_s=6)


def parse_query_date(date_text: str) -> tuple[int, int, int]:
    year_match = re.search(r"(\d{4})年", date_text)
    md = re.search(r"(\d{1,2})月(\d{1,2})日?", date_text)
    if not md:
        raise ValueError("date must look like 6月19日 or 2026年6月19日")
    year = int(year_match.group(1)) if year_match else dt.date.today().year
    return year, int(md.group(1)), int(md.group(2))


def current_form_date(nodes: list[UINode]) -> tuple[int, int, int] | None:
    date_nodes = [
        node for node in nodes
        if node.visible and re.search(r"\d{4}年\d{1,2}月\d{1,2}日", node.text)
    ]
    if not date_nodes:
        return None
    date_nodes.sort(key=lambda n: (n.center[1], n.center[0]))
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_nodes[0].text)
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def open_date_picker(adb: ADB) -> None:
    nodes = adb.dump_nodes()
    date_nodes = [
        node for node in nodes
        if node.visible and node.clickable and re.search(r"\d{4}年\d{1,2}月\d{1,2}日", node.text)
    ]
    if not date_nodes:
        raise RuntimeError("could not find date field")
    date_nodes.sort(key=lambda n: n.center[1])
    adb.tap(*date_nodes[0].center)


def is_month_header(nodes: list[UINode], node: UINode, year: int | None = None, month: int | None = None) -> bool:
    if month is not None and node.text.strip() != str(month):
        return False
    if not node.visible or not node.text.strip().isdigit():
        return False
    mx, my = node.center
    if not (40 <= mx <= 170):
        return False
    has_month_mark = any(
        mark.visible and mark.text.strip() == "月" and 20 <= mark.center[0] - mx <= 110 and abs(mark.center[1] - my) < 70
        for mark in nodes
    )
    has_year = any(
        yn.visible
        and yn.text.strip() == str(year if year is not None else "")
        and 70 <= yn.center[0] - mx <= 240
        and abs(yn.center[1] - my) < 80
        for yn in nodes
    )
    if year is None:
        has_year = any(
            yn.visible
            and re.fullmatch(r"\d{4}", yn.text.strip())
            and 70 <= yn.center[0] - mx <= 240
            and abs(yn.center[1] - my) < 80
            for yn in nodes
        )
    return has_month_mark and has_year


def month_header_y(nodes: list[UINode], year: int, month: int) -> int | None:
    for node in nodes:
        if is_month_header(nodes, node, year=year, month=month):
            return node.center[1]
    return None


def tap_calendar_day(adb: ADB, year: int, month: int, day: int) -> bool:
    nodes = adb.dump_nodes()
    header_y = month_header_y(nodes, year, month)
    visible_headers = [
        f"{node.text.strip()}@{node.center[1]}"
        for node in nodes
        if is_month_header(nodes, node)
    ]
    if visible_headers:
        print("calendar headers:", ", ".join(visible_headers))
    if header_y is None:
        return False
    next_headers = [
        node.center[1] for node in nodes
        if is_month_header(nodes, node) and node.center[1] > header_y + 120
    ]
    next_header_y = min(next_headers) if next_headers else SCREEN_H
    day_nodes = [
        node for node in nodes
        if node.visible
        and node.text.strip() == str(day)
        and header_y + 80 < node.center[1] < next_header_y
        and 40 <= node.center[0] <= 1000
    ]
    if not day_nodes:
        return False
    day_nodes.sort(key=lambda n: n.center[1])
    adb.tap(*day_nodes[0].center)
    return True


def select_date(adb: ADB, date_text: str) -> None:
    year, month, day = parse_query_date(date_text)
    nodes = adb.dump_nodes()
    current_date = current_form_date(nodes) if is_plus_form(nodes) else None
    if current_date == (year, month, day):
        print(f"date already {year}-{month:02d}-{day:02d}; skip selecting")
        return
    open_date_picker(adb)
    for _ in range(6):
        if tap_calendar_day(adb, year, month, day):
            wait_for(adb, is_plus_form, timeout_s=6)
            return
        # Move calendar content up only inside the date sheet.
        adb.swipe(540, 1850, 540, 1250, 450)
    raise RuntimeError(f"could not select date {year}-{month:02d}-{day:02d}")


def search(adb: ADB) -> None:
    nodes = adb.dump_nodes()
    if not tap_text(adb, "搜索预订", nodes):
        raise RuntimeError("could not find 搜索预订")
    wait_for(adb, lambda ns: has_text(ns, "日历") or has_text(ns, "起飞时间"), timeout_s=12)


def flight_summary_for_price(nodes: list[UINode], price_node: UINode, price: int) -> str:
    price_y = price_node.center[1]
    time_nodes = [
        node for node in nodes
        if (
            node.visible
            and re.fullmatch(r"\d{2}:\d{2}", node.text.strip())
            and node.center[0] < 760
            and price_y - 90 <= node.center[1] <= price_y + 90
        )
    ]
    time_nodes.sort(key=lambda n: n.center[0])
    route = ""
    if len(time_nodes) >= 2:
        depart_time = time_nodes[0].text.strip()
        arrive_time = time_nodes[1].text.strip()
        day_offset = next(
            (
                node.text.strip()
                for node in nodes
                if (
                    node.visible
                    and re.fullmatch(r"\+\d+天", node.text.strip())
                    and price_y - 90 <= node.center[1] <= price_y + 90
                )
            ),
            "",
        )
        route = f"{depart_time} -> {arrive_time}{f'({day_offset})' if day_offset else ''}"

    flight_nodes = [
        node for node in nodes
        if (
            node.visible
            and re.search(r"[A-Z]{2}\d{3,4}", node.text)
            and price_y < node.center[1] < price_y + 280
        )
    ]
    flight_nodes.sort(key=lambda n: n.center[1])
    flight = ""
    if flight_nodes:
        match = re.search(r"[A-Z]{2}\d{3,4}", flight_nodes[0].text)
        flight = match.group(0) if match else flight_nodes[0].text.strip()

    parts = [f"有 ¥{price} 机票"]
    if route:
        parts.append(route)
    if flight:
        parts.append(flight)
    return "，".join(parts)


def parse_result(adb: ADB, target_price: int) -> tuple[bool, str]:
    nodes = adb.dump_nodes()
    price_nodes = [
        node for node in nodes
        if node.visible and re.fullmatch(r"\d+", node.text.strip()) and node.center[0] > 760 and node.center[1] > 650
    ]
    target_nodes = [
        node for node in price_nodes
        if int(node.text.strip()) == target_price
    ]
    if target_nodes:
        target_nodes.sort(key=lambda n: (n.center[1], n.center[0]))
        return True, flight_summary_for_price(nodes, target_nodes[0], target_price)

    if price_nodes:
        cheapest = min(price_nodes, key=lambda n: int(n.text.strip()))
        cheapest_price = int(cheapest.text.strip())
        cheapest_summary = flight_summary_for_price(nodes, cheapest, cheapest_price)
        return False, f"未找到 ¥{target_price} 机票。当前可见最低价：{cheapest_summary}"

    return False, f"未找到 ¥{target_price} 机票。当前页面未解析到可见航班价格。"


def main() -> int:
    parser = argparse.ArgumentParser(description="Query HNA PLUS fare.")
    parser.add_argument("departure")
    parser.add_argument("destination")
    parser.add_argument("date")
    parser.add_argument("--price", type=int, default=199)
    parser.add_argument("--adb", default=DEFAULT_ADB)
    parser.add_argument("--unlock-script", default="./unlock.sh")
    parser.add_argument("--execute", action="store_true", help="Actually control the phone.")
    args = parser.parse_args()

    if not Path(args.adb).exists():
        raise FileNotFoundError(args.adb)

    adb = ADB(args.adb, execute=args.execute)
    unlocked_before_prepare = prepare_phone(adb, args.unlock_script)
    ensure_hna_plus_form(adb, unlocked_before_prepare)
    select_city(adb, "left", args.departure)
    select_city(adb, "right", args.destination)
    select_date(adb, args.date)
    search(adb)
    found, details = parse_result(adb, args.price)
    print("=" * 50)
    print(f"{args.departure} -> {args.destination}, {args.date}, target ¥{args.price}")
    print(details)
    print("=" * 50)
    return 0 if found else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
