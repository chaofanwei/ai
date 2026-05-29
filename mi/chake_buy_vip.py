#!/usr/bin/env python3
"""Automate buying ChaKe VIP cards through ADB.

Default mode is dry-run. Use --execute to really tap/swipe on the phone.
The script chooses one VIP-card price tier and quantity closest to the target.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
PACKAGE = "com.slwy.shanglvwuyou"
PRICES = [1986, 4986, 9986, 29986, 49986, 99986]
MAX_QTY = 7
SCREENSHOT_PATH = Path("/private/tmp/chake_vip_screen.png")
OCR_CROP_PATH = Path("/private/tmp/chake_vip_ocr_crop.png")
OCR_CROP_BOX = (0, 300, 450, 2050)
_OCR_ENGINE: object | None = None


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
        return values  # type: ignore[return-value]

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
    def __init__(self, adb_path: str, dry_run: bool) -> None:
        self.adb_path = adb_path
        self.dry_run = dry_run

    def run(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        proc = subprocess.run(
            [self.adb_path, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        if check and proc.returncode != 0:
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb {' '.join(args)} failed: {stderr or stdout}")
        return proc

    def shell(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell", *args], timeout=timeout)

    def tap(self, x: int, y: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(0.8)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if not self.dry_run:
            self.shell(
                ["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                timeout=6,
            )
            time.sleep(0.8)

    def dump_nodes(self) -> list[UINode]:
        self.shell(["uiautomator", "dump", "/sdcard/window.xml"], timeout=8)
        proc = self.run(["exec-out", "cat", "/sdcard/window.xml"], timeout=8)
        return parse_nodes(proc.stdout)

    def screencap(self, path: Path = SCREENSHOT_PATH) -> Path:
        proc = self.run(["exec-out", "screencap", "-p"], timeout=12)
        path.write_bytes(proc.stdout)
        return path


def parse_nodes(xml_bytes: bytes) -> list[UINode]:
    root = ET.fromstring(xml_bytes)
    nodes: list[UINode] = []
    for node in root.iter("node"):
        nodes.append(
            UINode(
                text=node.attrib.get("text", ""),
                bounds=node.attrib.get("bounds", ""),
                class_name=node.attrib.get("class", ""),
                clickable=node.attrib.get("clickable", "false") == "true",
            )
        )
    return nodes


def output_text(proc: subprocess.CompletedProcess[bytes]) -> str:
    return proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def get_ocr_engine() -> object:
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR

        _OCR_ENGINE = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
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

    points = list(raw_box)  # type: ignore[arg-type]
    xs = [int(round(float(point[0]))) for point in points]
    ys = [int(round(float(point[1]))) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def parse_paddleocr_result(result: object) -> list[OCRTextBox]:
    pages = result if isinstance(result, list) else [result]
    boxes: list[OCRTextBox] = []
    for page in pages:
        if isinstance(page, dict):
            texts = page.get("rec_texts", [])
            raw_boxes = page.get("rec_boxes")
            if raw_boxes is None:
                raw_boxes = page.get("rec_polys", [])
            scores = page.get("rec_scores", [])
            for index, text in enumerate(texts):
                if index >= len(raw_boxes):
                    continue
                score = float(scores[index]) if index < len(scores) else 0.0
                boxes.append(OCRTextBox(str(text), bounds_from_ocr_box(raw_boxes[index]), score))
            continue

        # PaddleOCR 2.x returns nested tuples: [[box, (text, score)], ...].
        for item in page or []:  # type: ignore[union-attr]
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
    screencap_elapsed = time.monotonic() - started
    crop_started = time.monotonic()
    from PIL import Image

    crop_x1, crop_y1, crop_x2, crop_y2 = OCR_CROP_BOX
    with Image.open(image_path) as image:
        image.crop(OCR_CROP_BOX).save(OCR_CROP_PATH)
    crop_elapsed = time.monotonic() - crop_started

    ocr = get_ocr_engine()
    predict_started = time.monotonic()
    if hasattr(ocr, "predict"):
        result = ocr.predict(str(OCR_CROP_PATH))  # type: ignore[attr-defined]
    else:
        result = ocr.ocr(str(OCR_CROP_PATH), cls=False)  # type: ignore[attr-defined]
    predict_elapsed = time.monotonic() - predict_started
    boxes = [box.translated(crop_x1, crop_y1) for box in parse_paddleocr_result(result)]
    total_elapsed = time.monotonic() - started
    print(
        "ocr timing: "
        f"screencap={screencap_elapsed:.2f}s, "
        f"crop={crop_elapsed:.2f}s, "
        f"predict={predict_elapsed:.2f}s, "
        f"total={total_elapsed:.2f}s, "
        f"boxes={len(boxes)}, "
        f"crop_box={crop_x1},{crop_y1},{crop_x2},{crop_y2}"
    )
    return boxes


def ocr_digits(text: str) -> str:
    return re.sub(r"\D+", "", text)


def locate_price_buy_point(boxes: list[OCRTextBox], price: int) -> tuple[int, int] | None:
    price_text = str(price)
    visible = [box for box in boxes if box.visible]
    price_boxes = [
        box
        for box in visible
        if ocr_digits(box.text) == price_text and box.score >= 0.5 and 300 <= box.center[1] <= 2060
    ]

    for price_box in sorted(price_boxes, key=lambda box: box.center[1]):
        return price_box.center

    return None


def visible_price_values(boxes: list[OCRTextBox]) -> list[int]:
    values: list[int] = []
    known_prices = {str(price): price for price in PRICES}
    for box in boxes:
        if not box.visible or box.score < 0.5:
            continue
        value = known_prices.get(ocr_digits(box.text))
        if value is not None:
            values.append(value)
    return values


def parse_target(value: str) -> int:
    text = value.strip().lower()
    multiplier = 1
    if text.endswith("万") or text.endswith("w"):
        multiplier = 10000
        text = text[:-1]
    amount = float(text)
    if amount <= 0:
        raise ValueError("target amount must be positive")
    return int(round(amount * multiplier))


def choose_plan(target: int) -> tuple[int, int, int, int]:
    best: tuple[int, int, int, int] | None = None
    for price in PRICES:
        for qty in range(1, MAX_QTY + 1):
            total = price * qty
            diff = abs(total - target)
            candidate = (diff, price, qty, total)
            if best is None or candidate < best:
                best = candidate
    if best is None:
        raise RuntimeError("no available VIP-card plan")
    diff, price, qty, total = best
    return price, qty, total, diff


def ensure_adb_exists(adb_path: str) -> None:
    if not Path(adb_path).exists():
        raise FileNotFoundError(f"adb not found: {adb_path}")


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
    if any(marker in power_text or marker in window_text for marker in screen_off_markers):
        return True
    if any(marker in window_text for marker in locked_markers):
        return True
    if any(marker in window_text for marker in unlocked_markers):
        return False
    print("warning: could not confidently determine lock state; assuming unlocked")
    return False


def ensure_unlocked(adb: ADB, unlock_script: str) -> None:
    if not device_needs_unlock(adb):
        print("screen appears unlocked")
        return
    script = Path(unlock_script)
    if not script.exists():
        raise FileNotFoundError(f"unlock script not found: {unlock_script}")
    print(f"screen is locked/off; running {unlock_script}")
    subprocess.run([str(script)], check=True, timeout=30)
    time.sleep(1)


def text_nodes(nodes: list[UINode], text: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.text == text]


def has_text(nodes: list[UINode], text: str) -> bool:
    return any(node.visible and text in node.text for node in nodes)


def wait_for_text(adb: ADB, candidates: list[str], timeout_s: int) -> list[UINode]:
    deadline = time.time() + timeout_s
    last_nodes: list[UINode] = []
    while time.time() < deadline:
        try:
            last_nodes = adb.dump_nodes()
        except Exception:
            time.sleep(0.5)
            continue
        if any(has_text(last_nodes, candidate) for candidate in candidates):
            return last_nodes
        time.sleep(0.5)
    return last_nodes


def wait_until_has_text(adb: ADB, candidates: list[str], timeout_s: int) -> bool:
    nodes = wait_for_text(adb, candidates, timeout_s)
    return any(has_text(nodes, candidate) for candidate in candidates)


def tap_text_center(adb: ADB, nodes: list[UINode], text: str, y_cap: int | None = None) -> bool:
    matches = text_nodes(nodes, text)
    if not matches:
        return False
    x, y = matches[0].center
    if y_cap is not None:
        y = min(y, y_cap)
    adb.tap(x, y)
    return True


def launch_home(adb: ADB) -> None:
    print("force-stop app")
    if not adb.dry_run:
        adb.shell(["am", "force-stop", PACKAGE], timeout=8)
        time.sleep(0.8)
    print("launch app")
    if not adb.dry_run:
        adb.run(["shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
        wait_for_text(adb, ["首页", "我的行程", "出差申请"], timeout_s=20)


def open_vip_service(adb: ADB) -> None:
    print("open 贵宾服务")
    for _ in range(5):
        if not adb.dry_run:
            nodes = adb.dump_nodes()
            if tap_text_center(adb, nodes, "贵宾服务", y_cap=2000):
                wait_for_text(adb, ["贵宾服务", "贵宾vip卡"], timeout_s=8)
                return
        adb.swipe(520, 1650, 520, 560, 600)
    if adb.dry_run:
        return
    raise RuntimeError("could not find 贵宾服务 on home page")


def swipe_vip_list(adb: ADB, direction: str) -> None:
    if direction == "down":
        adb.swipe(520, 1550, 520, 1000, 500)
    elif direction == "up":
        adb.swipe(520, 1000, 520, 1550, 500)
    else:
        raise ValueError(f"unsupported swipe direction: {direction}")


def tap_price_card(adb: ADB, price: int) -> None:
    print(f"open price tier {price}")
    if adb.dry_run:
        print("[dry-run] locate price tier with PaddleOCR")
        return

    for attempt in range(7):
        boxes = ocr_screen(adb)
        point = locate_price_buy_point(boxes, price)
        if point is None:
            recognized = ", ".join(box.text for box in boxes if box.visible and box.score >= 0.5)
            print(f"price {price} not visible by OCR on attempt {attempt + 1}; saw: {recognized}")
            prices = visible_price_values(boxes)
            if prices and price < min(prices):
                swipe_vip_list(adb, "up")
            else:
                swipe_vip_list(adb, "down")
            continue

        x, y = point
        adb.tap(x, y)
        if adb.dry_run:
            return
        if wait_until_has_text(adb, ["贵宾VIP卡详情"], timeout_s=4):
            return
        print(f"tap at {x},{y} did not open detail page; retrying")

    raise RuntimeError(f"failed to enter detail page for price tier {price}")


def verify_detail_page(nodes: list[UINode], price: int) -> None:
    expected_price = f"￥{price}"
    if not has_text(nodes, "10天"):
        raise RuntimeError("10天 product not visible on detail page")
    if not has_text(nodes, expected_price):
        raise RuntimeError(f"expected price {expected_price} not visible on detail page")


def first_visible_plus_button(nodes: list[UINode]) -> UINode | None:
    buttons = [
        node
        for node in nodes
        if node.visible
        and node.class_name == "android.widget.Button"
        and 1500 <= node.center[1] <= 2050
        and node.center[0] < 450
    ]
    if len(buttons) < 2:
        return None
    buttons.sort(key=lambda node: (node.center[1], node.center[0]))
    first_row_y = buttons[0].center[1]
    row = [node for node in buttons if abs(node.center[1] - first_row_y) <= 40]
    return max(row, key=lambda node: node.center[0])


def first_visible_buy_button(nodes: list[UINode]) -> UINode | None:
    candidates = text_nodes(nodes, "立即购买")
    if not candidates:
        return None
    visible = [node for node in candidates if node.center[1] > 1500]
    return visible[0] if visible else candidates[0]


def quantity_text(nodes: list[UINode]) -> str | None:
    fields = [
        node
        for node in nodes
        if node.visible
        and node.class_name == "android.widget.EditText"
        and 1500 <= node.center[1] <= 2050
        and node.center[0] < 450
    ]
    if not fields:
        return None
    fields.sort(key=lambda node: (node.center[1], node.center[0]))
    return fields[0].text


def set_quantity_and_buy(adb: ADB, qty: int, price: int, skip_buy: bool = False) -> None:
    print(f"set quantity {qty} for 10-day product")
    nodes = adb.dump_nodes() if not adb.dry_run else []
    if not adb.dry_run:
        verify_detail_page(nodes, price)

    for _ in range(qty - 1):
        if adb.dry_run:
            adb.tap(324, 1915)
            continue
        nodes = adb.dump_nodes()
        plus = first_visible_plus_button(nodes)
        if plus is None:
            raise RuntimeError("could not locate first product plus button")
        x, y = plus.center
        adb.tap(x, y)

    if not adb.dry_run:
        nodes = adb.dump_nodes()
        actual_qty = quantity_text(nodes)
        if actual_qty != str(qty):
            raise RuntimeError(f"quantity check failed: expected {qty}, saw {actual_qty!r}")
        if skip_buy:
            print("debug stop: quantity set; skip detail-page buy button")
            return
        buy_button = first_visible_buy_button(nodes)
        if buy_button is None:
            raise RuntimeError("could not locate first product buy button")
        x, y = buy_button.center
        adb.tap(x, y)
        wait_for_text(adb, ["收银台", "应付金额"], timeout_s=10)
    else:
        if skip_buy:
            print("[dry-run] debug stop: quantity set; skip detail-page buy button")
            return
        adb.tap(850, 1915)


def start_auto_payment(adb: ADB, expected_total: int) -> None:
    print("start auto-payment on cashier page")
    if not adb.dry_run:
        nodes = adb.dump_nodes()
        if not has_text(nodes, "收银台"):
            raise RuntimeError("cashier page not visible")
        amount_text = f"{expected_total:.2f}"
        if not has_text(nodes, amount_text):
            raise RuntimeError(f"expected cashier amount {amount_text} not visible")
    adb.tap(865, 553)
    adb.tap(540, 2065)


def run_buy(args: argparse.Namespace) -> int:
    target = parse_target(args.target)
    price, qty, total, diff = choose_plan(target)
    print(f"target={target}, selected={price} x {qty} = {total}, diff={diff}")

    if not args.execute:
        print("dry-run only. Pass --execute to operate the phone.")

    ensure_adb_exists(args.adb)
    adb = ADB(args.adb, dry_run=not args.execute)

    if args.execute and not args.start_current:
        if not args.skip_unlock_check:
            ensure_unlocked(adb, args.unlock_script)
        launch_home(adb)
        open_vip_service(adb)

    if args.start_current:
        print("start from current page")

    tap_price_card(adb, price)
    set_quantity_and_buy(adb, qty, price, skip_buy=args.stop_after_quantity)
    if args.stop_after_quantity:
        print("done: stopped after setting quantity on detail page")
        return 0
    start_auto_payment(adb, total)
    print("done: auto-payment flow has been triggered")
    return 0


def run_self_test() -> int:
    assert parse_target("40000") == 40000
    assert parse_target("4万") == 40000
    assert parse_target("4w") == 40000
    assert choose_plan(40000) == (9986, 4, 39944, 56)
    assert choose_plan(10000) == (9986, 1, 9986, 14)

    xml = """<?xml version='1.0' encoding='UTF-8'?>
    <hierarchy>
      <node text="贵宾VIP卡详情" class="android.view.View" bounds="[140,134][448,211]" clickable="false"/>
      <node text="梓如商旅金卡（10天）" class="android.view.View" bounds="[338,1578][786,1655]" clickable="false"/>
      <node text="￥9986" class="android.view.View" bounds="[338,1649][786,1745]" clickable="false"/>
      <node text="" class="android.widget.Button" bounds="[126,1883][192,1946]" clickable="true"/>
      <node text="1" class="android.widget.EditText" bounds="[192,1872][291,1957]" clickable="true"/>
      <node text="" class="android.widget.Button" bounds="[291,1883][357,1946]" clickable="true"/>
      <node text="立即购买" class="android.view.View" bounds="[709,1855][990,1974]" clickable="false"/>
    </hierarchy>""".encode("utf-8")
    nodes = parse_nodes(xml)
    plus = first_visible_plus_button(nodes)
    buy = first_visible_buy_button(nodes)
    assert plus is not None and plus.center == (324, 1914)
    assert buy is not None and buy.center == (849, 1914)
    assert quantity_text(nodes) == "1"
    assert has_text(nodes, "10天")
    assert has_text(nodes, "9986")

    ocr_boxes = [
        OCRTextBox("9986", (115, 688, 220, 771), 0.99),
        OCRTextBox("点击购买", (774, 842, 990, 896), 0.99),
        OCRTextBox("29986", (108, 1436, 260, 1522), 0.99),
        OCRTextBox("点击购买", (788, 1575, 990, 1635), 0.99),
    ]
    assert locate_price_buy_point(ocr_boxes, 9986) == (167, 729)
    assert locate_price_buy_point(ocr_boxes, 29986) == (184, 1479)
    assert visible_price_values(ocr_boxes) == [9986, 29986]
    print("self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Buy ChaKe VIP card closest to a target amount.")
    parser.add_argument("target", nargs="?", default="40000", help="Target amount, e.g. 40000, 4万, or 4w.")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="Path to adb.")
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone.")
    parser.add_argument("--unlock-script", default="./unlock.sh", help="Script used when screen is locked/off.")
    parser.add_argument("--skip-unlock-check", action="store_true", help="Do not check lock state before launch.")
    parser.add_argument(
        "--start-current",
        action="store_true",
        help="Skip app launch/navigation and start from current VIP-card list page.",
    )
    parser.add_argument(
        "--stop-after-quantity",
        action="store_true",
        help="Debug mode: stop after opening the detail page and setting quantity; do not tap 立即购买.",
    )
    parser.add_argument("--self-test", action="store_true", help="Run local tests without touching the phone.")
    return parser.parse_args()


if __name__ == "__main__":
    parsed = parse_args()
    if parsed.self_test:
        raise SystemExit(run_self_test())
    try:
        raise SystemExit(run_buy(parsed))
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
