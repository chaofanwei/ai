#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""Extract Alipay hotel-order payment cards from the bill page.

Example:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python alipay_hotel_orders.py --end-date 4-1 --execute
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
ALIPAY_PACKAGE = "com.eg.android.AlipayGphone"
CHAKE_LEDGER_BASE_URL = "http://myroute.cn/chake"
DEFAULT_LEDGER_LOOKBACK_DAYS = 15
DEFAULT_LEDGER_MATCH_TOLERANCE_MINUTES = 20
ALIPAY_LEDGER_ACCOUNT_BY_SUFFIX = {
    "01": "wei",
    "02": "wei",
    "79": "chang",
}
REMOTE_XML = "/sdcard/window.xml"
SCREENSHOT_PATH = Path("/private/tmp/alipay_hotel_orders_screen.png")
OCR_CROP_PATH = Path("/private/tmp/alipay_hotel_orders_crop.png")
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
    def center(self) -> tuple[int, int]:
        x1, y1, x2, y2 = self.box
        return (x1 + x2) // 2, (y1 + y2) // 2

    @property
    def visible(self) -> bool:
        x1, y1, x2, y2 = self.box
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2135

    def translated(self, dx: int, dy: int) -> OCRTextBox:
        x1, y1, x2, y2 = self.box
        return OCRTextBox(self.text, (x1 + dx, y1 + dy, x2 + dx, y2 + dy), self.score)


@dataclass(frozen=True)
class BillOrder:
    title: str
    amount_text: str
    category: str
    month: int
    day: int
    time_text: str
    raw: str

    def date(self, year: int) -> dt.date:
        return dt.date(year, self.month, self.day)

    @property
    def key(self) -> str:
        return f"{self.title}|{self.amount_text}|{self.month:02d}-{self.day:02d} {self.time_text}"


@dataclass
class HotelOrderResult:
    account_phone: str
    order_date: str
    order_time: str
    title: str
    amount: str
    bank_name: str
    card_tail: str
    payment_method: str
    merchant: str
    raw_order: str


@dataclass
class DetailRead:
    result: HotelOrderResult
    detail_payment_time: str
    list_payment_time: str
    time_matches: bool


@dataclass(frozen=True)
class LedgerSyncPlan:
    account: str
    need_card_items: list[dict]
    end_date: dt.date | None


@dataclass(frozen=True)
class LedgerSyncSummary:
    synced: list[dict]
    skipped: list[dict]
    abnormal: list[dict]


class ADB:
    def __init__(self, adb_path: str, dry_run: bool) -> None:
        self.adb_path = adb_path
        self.dry_run = dry_run

    def run(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        cmd = [self.adb_path, *args]
        if self.dry_run and args[:2] == ["shell", "input"]:
            print("[dry-run]", " ".join(cmd))
            return subprocess.CompletedProcess(cmd, 0, b"", b"")
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        if check and proc.returncode != 0:
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb {' '.join(args)} failed: {stderr or stdout}")
        return proc

    def shell(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell", *args], timeout=timeout, check=check)

    def tap(self, x: int, y: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(0.8)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 600) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if not self.dry_run:
            self.shell(
                ["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                timeout=6,
            )
            time.sleep(1.0)

    def back(self) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}back")
        if not self.dry_run:
            self.shell(["input", "keyevent", "4"], timeout=4)
            time.sleep(1.0)

    def screencap(self, path: Path = SCREENSHOT_PATH) -> Path:
        proc = self.run(["exec-out", "screencap", "-p"], timeout=12)
        path.write_bytes(proc.stdout)
        return path

    def dump_nodes(self) -> list[UINode]:
        # Alipay H5 pages sometimes return "could not get idle state" even while the
        # hierarchy is still available. Dump, then read whatever uiautomator wrote.
        self.shell(["uiautomator", "dump", REMOTE_XML], timeout=12, check=False)
        proc = self.run(["exec-out", "cat", REMOTE_XML], timeout=12)
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
                class_name=node.attrib.get("class", ""),
                clickable=node.attrib.get("clickable", "false") == "true",
            )
        )
    return nodes


def ensure_adb_exists(adb_path: str) -> None:
    if not Path(adb_path).exists():
        raise FileNotFoundError(f"adb not found: {adb_path}")


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


def ocr_region(adb: ADB, crop_box: tuple[int, int, int, int], label: str) -> list[OCRTextBox]:
    started = time.monotonic()
    image_path = adb.screencap()
    from PIL import Image

    x1, y1, x2, y2 = crop_box
    with Image.open(image_path) as image:
        image.crop(crop_box).save(OCR_CROP_PATH)

    ocr = get_ocr_engine()
    if hasattr(ocr, "predict"):
        result = ocr.predict(str(OCR_CROP_PATH))  # type: ignore[attr-defined]
    else:
        result = ocr.ocr(str(OCR_CROP_PATH), cls=False)  # type: ignore[attr-defined]
    boxes = [box.translated(x1, y1) for box in parse_paddleocr_result(result)]
    elapsed = time.monotonic() - started
    print(f"ocr {label}: {elapsed:.2f}s, boxes={len(boxes)}, crop={crop_box}")
    return boxes


def normalized_digits(text: str) -> str:
    return re.sub(r"\D+", "", text)


def parse_date_time_text(text: str) -> tuple[int, int, str] | None:
    match = re.search(r"(?P<month>\d{2})-(?P<day>\d{2})\s*(?P<time>\d{2}:\d{2})", text)
    if not match:
        return None
    return int(match.group("month")), int(match.group("day")), match.group("time")


def looks_like_list_amount(text: str) -> bool:
    return bool(re.fullmatch(r"[+-]?\d[\d,]*\.\d{2}", text.strip()))


def parse_bill_orders_from_ocr_boxes(boxes: list[OCRTextBox]) -> list[BillOrder]:
    visible_boxes = [box for box in boxes if box.visible and box.score >= 0.35]
    amount_boxes = [box for box in visible_boxes if looks_like_list_amount(box.text)]
    date_boxes = [box for box in visible_boxes if parse_date_time_text(box.text)]
    orders: list[BillOrder] = []
    seen: set[str] = set()

    for amount_box in amount_boxes:
        _, amount_y = amount_box.center
        title_box = min(
            (
                box
                for box in visible_boxes
                if box.center[0] < 620
                and abs(box.center[1] - amount_y) <= 80
                and box is not amount_box
                and not looks_like_list_amount(box.text)
                and not parse_date_time_text(box.text)
                and "￥" not in box.text
            ),
            key=lambda box: abs(box.center[1] - amount_y),
            default=None,
        )
        if title_box is None:
            continue
        _, title_y = title_box.center
        date_box = min(
            (box for box in date_boxes if 40 <= box.center[1] - title_y <= 220),
            key=lambda box: abs(box.center[1] - (title_y + 150)),
            default=None,
        )
        if date_box is None:
            continue
        parsed_date = parse_date_time_text(date_box.text)
        if parsed_date is None:
            continue
        month, day, time_text = parsed_date
        category_box = min(
            (
                box
                for box in visible_boxes
                if box.center[0] < 620 and 25 <= box.center[1] - title_y <= 110 and box is not date_box
            ),
            key=lambda box: abs(box.center[1] - (title_y + 75)),
            default=None,
        )
        title = title_box.text.strip()
        category = category_box.text.strip() if category_box is not None else ""
        raw = f"{title}，{amount_box.text.strip()}元，，{category}，，{month:02d}-{day:02d} {time_text}"
        if raw in seen:
            continue
        orders.append(
            BillOrder(
                title=title,
                amount_text=amount_box.text.strip(),
                category=category,
                month=month,
                day=day,
                time_text=time_text,
                raw=raw,
            )
        )
        seen.add(raw)
    orders.sort(key=lambda order: (order.month, order.day, order.time_text), reverse=True)
    return orders


def parse_hotel_orders_from_ocr_boxes(boxes: list[OCRTextBox]) -> list[BillOrder]:
    hotel_orders: list[BillOrder] = []
    seen: set[str] = set()
    for order in parse_bill_orders_from_ocr_boxes(boxes):
        if order.title != "酒店订单" or order.raw in seen:
            continue
        hotel_orders.append(order)
        seen.add(order.raw)
    return hotel_orders


def write_results(path: str, results: list[HotelOrderResult]) -> None:
    if not path:
        return
    Path(path).write_text(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2), "utf-8")


def bill_order_record(order: BillOrder, year: int) -> dict[str, object]:
    return {
        "order_date": order.date(year).isoformat(),
        "order_time": order.time_text,
        "title": order.title,
        "amount": order.amount_text,
        "category": order.category,
        "raw_order": order.raw,
    }


def write_bill_orders(path: str, orders: list[BillOrder], year: int) -> None:
    if not path:
        return
    data = [bill_order_record(order, year) for order in orders]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")


def results_record(results: list[HotelOrderResult]) -> list[dict[str, object]]:
    return [asdict(item) for item in results]


def parse_purchase_datetime(value: str) -> dt.datetime | None:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            parsed = dt.datetime.strptime(value.strip(), fmt)
            if fmt == "%Y-%m-%d":
                return parsed.replace(hour=0, minute=0, second=0)
            return parsed
        except ValueError:
            continue
    return None


def parse_ledger_amount(value: object) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def parse_result_amount_int(amount: str) -> int | None:
    normalized = amount.strip().replace(",", "")
    match = re.fullmatch(r"(\d+)\.00", normalized)
    if not match:
        return None
    return int(match.group(1))


def ledger_card_missing(item: dict) -> bool:
    return not str(item.get("payment_card_bank") or "").strip() or not str(
        item.get("payment_card_last_digits") or ""
    ).strip()


def chake_ledger_json(method: str, path: str, *, params: dict[str, str] | None = None, data: dict | None = None) -> dict:
    url = f"{CHAKE_LEDGER_BASE_URL}{path}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = response.read().decode("utf-8", "replace")
    return json.loads(payload)


def ledger_items(account: str, lookback_days: int) -> list[dict]:
    cutoff_date = dt.date.today() - dt.timedelta(days=lookback_days)
    cutoff = dt.datetime.combine(cutoff_date, dt.time.min)
    page = 1
    page_size = 100
    total: int | None = None
    items: list[dict] = []
    reached_cutoff = False
    while total is None or len(items) < total:
        payload = chake_ledger_json(
            "GET",
            "/list",
            params={"account_name": account, "page": str(page), "page_size": str(page_size)},
        )
        if payload.get("code") != 0:
            raise RuntimeError(payload.get("msg") or payload)
        page_items = payload.get("items") or []
        for item in page_items:
            purchase_dt = parse_purchase_datetime(str(item.get("purchase_time", "")))
            if purchase_dt is not None and purchase_dt < cutoff:
                reached_cutoff = True
                break
            items.append(item)
        total = int(payload.get("total") or len(items))
        if not page_items or reached_cutoff:
            break
        page += 1
    return items


def build_ledger_sync_plan(account: str, lookback_days: int) -> LedgerSyncPlan:
    items = ledger_items(account, lookback_days)
    need_card_items = [item for item in items if ledger_card_missing(item)]
    purchase_times = [
        parsed
        for parsed in (parse_purchase_datetime(str(item.get("purchase_time", ""))) for item in need_card_items)
        if parsed is not None
    ]
    end_date = min(purchase_times).date() if purchase_times else None
    return LedgerSyncPlan(account=account, need_card_items=need_card_items, end_date=end_date)


def alipay_account_suffix(account_phone: str) -> str:
    digits = normalized_digits(account_phone)
    if len(digits) >= 2:
        return digits[-2:]
    return ""


def ledger_account_for_alipay(account_phone: str) -> str | None:
    suffix = alipay_account_suffix(account_phone)
    if not suffix:
        return None
    return ALIPAY_LEDGER_ACCOUNT_BY_SUFFIX.get(suffix)


def format_end_date(value: dt.date) -> str:
    return f"{value.month}-{value.day}"


def result_payment_datetime(result: HotelOrderResult) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(f"{result.order_date} {result.order_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def ledger_match_candidates(
    result: HotelOrderResult,
    items: list[dict],
    *,
    tolerance_minutes: int,
) -> tuple[list[dict], str]:
    result_amount = parse_result_amount_int(result.amount)
    if result_amount is None:
        return [], "non_integer_amount"
    result_dt = result_payment_datetime(result)
    if result_dt is None:
        return [], "invalid_result_time"
    matches: list[dict] = []
    for item in items:
        item_amount = parse_ledger_amount(item.get("purchase_amount"))
        item_dt = parse_purchase_datetime(str(item.get("purchase_time", "")))
        if item_amount is None or item_dt is None:
            continue
        if item_amount != result_amount:
            continue
        if abs(item_dt - result_dt) <= dt.timedelta(minutes=tolerance_minutes):
            matches.append(item)
    if not matches:
        return [], "no_match"
    if len(matches) > 1:
        return matches, "multiple_matches"
    return matches, ""


def update_ledger_payment_card(item_id: int, bank_name: str, card_tail: str, *, dry_sync: bool) -> dict:
    data = {
        "id": item_id,
        "payment_card_bank": bank_name,
        "payment_card_last_digits": card_tail,
    }
    if dry_sync:
        print("dry-sync ledger update", json.dumps(data, ensure_ascii=False))
        return {"code": 0, "updated": 0, "dry_sync": True}
    payload = chake_ledger_json("POST", "/update", data=data)
    if payload.get("code") != 0:
        raise RuntimeError(payload.get("msg") or payload)
    return payload


def sync_results_to_ledger(
    results: list[HotelOrderResult],
    plan: LedgerSyncPlan,
    *,
    tolerance_minutes: int,
    dry_sync: bool,
) -> LedgerSyncSummary:
    pending_items_by_id = {int(item["id"]): item for item in plan.need_card_items if str(item.get("id", "")).isdigit()}
    synced: list[dict] = []
    skipped: list[dict] = []
    abnormal: list[dict] = []

    for result in results:
        result_record = asdict(result)
        if not result.bank_name or not result.card_tail:
            abnormal.append({"reason": "missing_card_info", "result": result_record})
            continue
        candidates, reason = ledger_match_candidates(
            result,
            list(pending_items_by_id.values()),
            tolerance_minutes=tolerance_minutes,
        )
        if reason:
            abnormal.append(
                {
                    "reason": reason,
                    "result": result_record,
                    "candidate_ids": [item.get("id") for item in candidates],
                }
            )
            continue
        item = candidates[0]
        item_id = int(item["id"])
        existing_bank = str(item.get("payment_card_bank") or "").strip()
        existing_tail = str(item.get("payment_card_last_digits") or "").strip()
        if existing_bank == result.bank_name and existing_tail == result.card_tail:
            skipped.append({"reason": "already_synced", "ledger_item": item, "result": result_record})
            pending_items_by_id.pop(item_id, None)
            continue
        try:
            payload = update_ledger_payment_card(item_id, result.bank_name, result.card_tail, dry_sync=dry_sync)
        except Exception as exc:
            abnormal.append({"reason": "ledger_api_error", "error": str(exc), "ledger_item": item, "result": result_record})
            continue
        item["payment_card_bank"] = result.bank_name
        item["payment_card_last_digits"] = result.card_tail
        synced.append({"ledger_id": item_id, "update": payload, "ledger_item": item, "result": result_record})
        pending_items_by_id.pop(item_id, None)

    for item in pending_items_by_id.values():
        skipped.append({"reason": "not_seen_in_alipay_results", "ledger_item": item})

    return LedgerSyncSummary(synced=synced, skipped=skipped, abnormal=abnormal)


def print_ledger_sync_success_summary(synced: list[dict]) -> None:
    if not synced:
        print("LEDGER_SYNC_SUCCESS_SUMMARY none")
        return
    lines: list[dict[str, object]] = []
    for record in synced:
        item = record.get("ledger_item") or {}
        result = record.get("result") or {}
        if not isinstance(item, dict) or not isinstance(result, dict):
            continue
        lines.append(
            {
                "id": item.get("id") or record.get("ledger_id"),
                "purchase_time": item.get("purchase_time"),
                "purchase_amount": item.get("purchase_amount"),
                "payment_card_bank": result.get("bank_name"),
                "payment_card_last_digits": result.get("card_tail"),
                "alipay_time": f"{result.get('order_date', '')} {result.get('order_time', '')}".strip(),
                "alipay_amount": result.get("amount"),
            }
        )
    print("LEDGER_SYNC_SUCCESS_SUMMARY", json.dumps(lines, ensure_ascii=False))


def parse_end_date(value: str, year: int) -> dt.date:
    match = re.fullmatch(r"\s*(\d{1,2})[-/月](\d{1,2})(?:日)?\s*", value)
    if not match:
        raise ValueError("end-date must look like 4-1 or 4月1日")
    month, day = map(int, match.groups())
    return dt.date(year, month, day)


def launch_alipay(adb: ADB) -> None:
    print("launch Alipay")
    if adb.dry_run:
        return
    adb.shell(["am", "force-stop", ALIPAY_PACKAGE], timeout=8)
    time.sleep(1)
    adb.run(["shell", "monkey", "-p", ALIPAY_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
    time.sleep(4)


def open_my_page(adb: ADB) -> None:
    print("open 我的 page")
    # Bottom tab layout is stable on this device: 5 tabs across 1080px.
    adb.tap(972, 2090)
    time.sleep(3)


def extract_account_phone(adb: ADB) -> str:
    boxes = ocr_region(adb, (230, 185, 720, 390), "my-page-phone")
    text = " ".join(box.text for box in boxes if box.score >= 0.35)
    match = re.search(r"1\d{2}\*{2,}\d{2}", text)
    if match:
        return match.group(0)
    match = re.search(r"1\d{2}.{2,8}\d{2}", text)
    if match:
        return match.group(0)
    print(f"warning: phone OCR did not match expected pattern; OCR text={text!r}")
    return ""


def locate_bill_button(adb: ADB) -> tuple[int, int]:
    boxes = ocr_region(adb, (0, 250, 1080, 1600), "my-page-bill")
    for box in boxes:
        if box.score >= 0.45 and "账单" in box.text:
            x, y = box.center
            return x, y
    recognized = ", ".join(f"{box.text}@{box.box}:{box.score:.2f}" for box in boxes)
    raise RuntimeError(f"could not locate 账单 by OCR; saw: {recognized}")


def wait_for_bill_page(adb: ADB, timeout_s: int = 12) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        nodes = adb.dump_nodes()
        if parse_orders(nodes):
            return
        texts = visible_text(nodes)
        text_set = set(texts)
        if any("搜索交易记录" in text for text in texts):
            return
        if {"全部", "支出", "订单", "筛选"}.issubset(text_set):
            return
        time.sleep(0.8)
    raise RuntimeError("bill page did not appear")


def load_existing_results(path: str) -> list[HotelOrderResult]:
    if not path:
        return []
    file_path = Path(path)
    if not file_path.exists():
        return []
    data = json.loads(file_path.read_text("utf-8"))
    return [HotelOrderResult(**item) for item in data]


ORDER_RE = re.compile(
    r"^(?P<title>.+?)，(?P<amount>[+-]?\d[\d,]*\.\d{2})元，，(?P<category>.*?)，，"
    r"(?P<month>\d{2})-(?P<day>\d{2}) (?P<time>\d{2}:\d{2})$"
)


def parse_orders(nodes: list[UINode]) -> list[BillOrder]:
    orders: list[BillOrder] = []
    for node in nodes:
        text = node.text.strip()
        match = ORDER_RE.match(text)
        if not match:
            continue
        orders.append(
            BillOrder(
                title=match.group("title"),
                amount_text=match.group("amount"),
                category=match.group("category"),
                month=int(match.group("month")),
                day=int(match.group("day")),
                time_text=match.group("time"),
                raw=text,
            )
        )
    return orders


def visible_text(nodes: list[UINode]) -> list[str]:
    return [node.text for node in nodes if node.text.strip()]


def locate_order_in_boxes(boxes: list[OCRTextBox], order: BillOrder) -> tuple[int, int] | None:
    amount_digits = normalized_digits(order.amount_text)
    date_text = f"{order.month:02d}-{order.day:02d}"
    amount_matches = [
        box
        for box in boxes
        if box.visible and box.score >= 0.35 and normalized_digits(box.text) == amount_digits
    ]
    date_boxes = [box for box in boxes if box.visible and box.score >= 0.35 and date_text in box.text]
    title_boxes = [box for box in boxes if box.visible and box.score >= 0.35 and order.title in box.text]

    candidates: list[OCRTextBox] = []
    for amount_box in amount_matches:
        _, y = amount_box.center
        near_date = any(abs(date_box.center[1] - y) <= 180 for date_box in date_boxes)
        near_title = any(abs(title_box.center[1] - y) <= 120 for title_box in title_boxes)
        if near_date or near_title:
            candidates.append(amount_box)
    if not candidates and amount_matches:
        candidates = amount_matches

    if candidates:
        candidates.sort(key=lambda box: box.center[1])
        _, y = candidates[0].center
        return 300, y

    for date_box in date_boxes:
        _, y = date_box.center
        if any(abs(title_box.center[1] - y) <= 160 for title_box in title_boxes):
            return 300, y - 70

    return None


def parse_payment_method(nodes: list[UINode]) -> tuple[str, str, str]:
    texts = visible_text(nodes)
    joined = "\n".join(texts)
    parsed = parse_payment_method_text(joined)
    if parsed is not None:
        return parsed
    return "", "", ""


def parse_payment_method_text(text: str) -> tuple[str, str, str] | None:
    patterns = [
        r"([\u4e00-\u9fa5]+银行信用卡)[(（](\d{2,})[)）]",
        r"([\u4e00-\u9fa5]+银行储蓄卡)[(（](\d{2,})[)）]",
        r"([\u4e00-\u9fa5]+银行卡)[(（](\d{2,})[)）]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            payment_method = f"{match.group(1)}({match.group(2)})"
            bank_name = re.sub(r"(信用卡|储蓄卡|银行卡)$", "", match.group(1))
            return bank_name, match.group(2), payment_method
    return None


def text_right_of_label(boxes: list[OCRTextBox], label: str) -> str:
    visible_boxes = [box for box in boxes if box.visible and box.score >= 0.35]
    label_boxes = [box for box in visible_boxes if label in box.text]
    if not label_boxes:
        return ""
    label_box = min(label_boxes, key=lambda box: box.center[1])
    label_x, label_y = label_box.center
    candidates = [
        box
        for box in visible_boxes
        if box.center[0] > label_x + 80 and abs(box.center[1] - label_y) <= 80
    ]
    if not candidates:
        return ""
    candidates.sort(key=lambda box: box.center[0])
    return "".join(box.text.strip() for box in candidates).strip()


def parse_detail_payment_time_from_ocr(boxes: list[OCRTextBox]) -> str:
    text = text_right_of_label(boxes, "支付时间")
    match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})\s*(\d{2}):(\d{2})(?::\d{2})?", text)
    if match:
        year, month, day, hour, minute = match.groups()
        return f"{year}-{month}-{day} {hour}:{minute}"
    joined = "\n".join(box.text for box in boxes if box.visible and box.score >= 0.35)
    match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})\s*(\d{2}):(\d{2})(?::\d{2})?", joined)
    if match:
        year, month, day, hour, minute = match.groups()
        return f"{year}-{month}-{day} {hour}:{minute}"
    return ""


def payment_times_match(list_payment_time: str, detail_payment_time: str, tolerance_minutes: int = 30) -> bool:
    if not list_payment_time or not detail_payment_time:
        return False
    try:
        list_dt = dt.datetime.strptime(list_payment_time, "%Y-%m-%d %H:%M")
        detail_dt = dt.datetime.strptime(detail_payment_time, "%Y-%m-%d %H:%M")
    except ValueError:
        return False
    delta = abs(detail_dt - list_dt)
    return delta <= dt.timedelta(minutes=tolerance_minutes)


def parse_detail_order_amount_from_ocr(boxes: list[OCRTextBox]) -> str:
    text = text_right_of_label(boxes, "订单金额")
    text = text.replace("O", "0").replace("o", "0").replace("，", ",")
    match = re.search(r"\d[\d,]*\.\d{1,2}", text)
    if match:
        amount = match.group(0).replace(",", "")
        if re.fullmatch(r"\d+\.\d", amount):
            amount += "0"
        return amount
    match = re.search(r"\d[\d,]{3,}", text)
    if match:
        return f"{match.group(0).replace(',', '')}.00"
    return ""


def normalize_order_amount(amount_text: str) -> str:
    amount = amount_text.strip().replace(",", "")
    amount = amount.lstrip("+-")
    match = re.search(r"\d+(?:\.\d{1,2})?", amount)
    if not match:
        return ""
    value = match.group(0)
    if "." not in value:
        return f"{value}.00"
    if re.fullmatch(r"\d+\.\d", value):
        return f"{value}0"
    return value


def parse_payment_method_from_ocr(boxes: list[OCRTextBox]) -> tuple[str, str, str]:
    text = text_right_of_label(boxes, "付款方式")
    parsed = parse_payment_method_text(text)
    if parsed is not None:
        return parsed
    joined = "\n".join(box.text for box in boxes if box.visible and box.score >= 0.35)
    parsed = parse_payment_method_text(joined)
    if parsed is not None:
        return parsed
    return "", "", ""


def parse_detail_merchant(nodes: list[UINode]) -> str:
    texts = visible_text(nodes)
    for index, text in enumerate(texts):
        if text in {"收款方全称", "收款方"} and index + 1 < len(texts):
            candidate = texts[index + 1]
            if candidate not in {"收款方全称", "收款方"}:
                return candidate
    for text in texts:
        if "旅行社" in text or "酒店" in text:
            return text
    return ""


def parse_detail_merchant_from_ocr(boxes: list[OCRTextBox]) -> str:
    merchant = text_right_of_label(boxes, "收款方全称")
    if merchant:
        return merchant
    merchant = text_right_of_label(boxes, "收款方")
    if merchant:
        return merchant
    for box in boxes:
        if box.visible and box.score >= 0.35 and ("旅行社" in box.text or "酒店" in box.text):
            return box.text
    return ""


def open_order_detail(adb: ADB, order: BillOrder, boxes: list[OCRTextBox]) -> bool:
    point = locate_order_in_boxes(boxes, order)
    if point is None:
        print(f"skip not visible: {order.raw}")
        return False
    adb.tap(*point)
    if adb.dry_run:
        return False
    time.sleep(2.0)
    return True


def read_detail(adb: ADB, account_phone: str, order: BillOrder, year: int) -> DetailRead:
    detail_boxes = ocr_region(adb, (0, 250, 1080, 1700), "detail-fields")
    bank_name, card_tail, payment_method = parse_payment_method_from_ocr(detail_boxes)
    merchant = parse_detail_merchant_from_ocr(detail_boxes)
    detail_order_amount = parse_detail_order_amount_from_ocr(detail_boxes)
    if not detail_order_amount:
        detail_order_amount = normalize_order_amount(order.amount_text)
    detail_payment_time = parse_detail_payment_time_from_ocr(detail_boxes)
    list_payment_time = f"{order.date(year).isoformat()} {order.time_text}"
    time_matches = payment_times_match(list_payment_time, detail_payment_time)

    return DetailRead(
        result=HotelOrderResult(
            account_phone=account_phone,
            order_date=order.date(year).isoformat(),
            order_time=order.time_text,
            title=order.title,
            amount=detail_order_amount,
            bank_name=bank_name,
            card_tail=card_tail,
            payment_method=payment_method,
            merchant=merchant,
            raw_order=order.raw,
        ),
        detail_payment_time=detail_payment_time,
        list_payment_time=list_payment_time,
        time_matches=time_matches,
    )


def has_visible_order_before_cutoff(orders: list[BillOrder], boxes: list[OCRTextBox], cutoff: dt.date, year: int) -> bool:
    for order in orders:
        if order.date(year) < cutoff and locate_order_in_boxes(boxes, order) is not None:
            return True
    return False


def visible_orders_on_or_after_cutoff(
    orders: list[BillOrder], boxes: list[OCRTextBox], cutoff: dt.date, year: int
) -> list[BillOrder]:
    visible: list[BillOrder] = []
    for order in orders:
        if order.date(year) >= cutoff and locate_order_in_boxes(boxes, order) is not None:
            visible.append(order)
    return visible


def xml_has_order_before_cutoff(orders: list[BillOrder], cutoff: dt.date, year: int) -> bool:
    return any(order.date(year) < cutoff for order in orders)


def open_bill_page_from_home(adb: ADB) -> None:
    launch_alipay(adb)
    open_my_page(adb)
    x, y = locate_bill_button(adb)
    print(f"账单 OCR point: {x},{y}")
    adb.tap(x, y)
    time.sleep(3)


def screen_has_order_before_cutoff(orders: list[BillOrder], cutoff: dt.date, year: int) -> bool:
    return any(order.date(year) < cutoff for order in orders)


def scroll_half_screen(adb: ADB) -> None:
    adb.swipe(540, 1650, 540, 1050, 650)


def scan_hotel_orders_until_cutoff(adb: ADB, cutoff: dt.date, year: int, max_scrolls: int) -> list[BillOrder]:
    targets: list[BillOrder] = []
    seen: set[str] = set()
    for scroll_index in range(max_scrolls + 1):
        nodes = adb.dump_nodes()
        orders = parse_orders(nodes)
        print(f"scan scroll={scroll_index}, xml_orders={len(orders)}")
        if not orders:
            print("warning: XML has no bill orders on this screen")
            break
        list_boxes = ocr_region(adb, (0, 330, 1080, 1960), "scan-visible")
        visible_in_scope = visible_orders_on_or_after_cutoff(orders, list_boxes, cutoff, year)
        for order in visible_in_scope:
            if order.title == "酒店订单" and order.key not in seen:
                targets.append(order)
                seen.add(order.key)
                print(f"target {order.key}")
        if not visible_in_scope and xml_has_order_before_cutoff(orders, cutoff, year):
            print("scan reached XML orders before cutoff; stop")
            break
        if scroll_index >= max_scrolls:
            break
        adb.swipe(540, 1780, 540, 720, 700)
    return targets


def find_and_open_order_detail(adb: ADB, order: BillOrder, cutoff: dt.date, year: int, max_scrolls: int) -> bool:
    for scroll_index in range(max_scrolls + 1):
        nodes = adb.dump_nodes()
        orders = parse_orders(nodes)
        print(f"find {order.key}: scroll={scroll_index}, xml_orders={len(orders)}")
        if not orders:
            print("warning: XML has no bill orders while finding target; stop")
            return False
        list_boxes = ocr_region(adb, (0, 330, 1080, 1960), "find-visible")
        matching = [item for item in orders if item.key == order.key]
        if matching:
            point = locate_order_in_boxes(list_boxes, matching[0])
            if point is not None:
                adb.tap(*point)
                if adb.dry_run:
                    return False
                deadline = time.time() + 10
                while time.time() < deadline:
                    detail_nodes = adb.dump_nodes()
                    if any("账单详情" in text or "交易成功" in text for text in visible_text(detail_nodes)):
                        return True
                    time.sleep(0.5)
                raise RuntimeError(f"order detail did not open: {order.raw}")
        visible_in_scope = visible_orders_on_or_after_cutoff(orders, list_boxes, cutoff, year)
        if not visible_in_scope and xml_has_order_before_cutoff(orders, cutoff, year):
            return False
        if scroll_index >= max_scrolls:
            return False
        adb.swipe(540, 1780, 540, 720, 700)
    return False


def collect_hotel_orders(args: argparse.Namespace) -> tuple[list[HotelOrderResult], LedgerSyncPlan | None]:
    year = args.year

    ensure_adb_exists(args.adb)
    adb = ADB(args.adb, dry_run=not args.execute)
    if not args.execute:
        print("dry-run only. Pass --execute to operate the phone.")

    if args.start_bill_page:
        print("start from current bill page")
        account_phone = args.account_phone
        ledger_plan = prepare_ledger_sync(args, account_phone)
    else:
        if not args.start_current:
            launch_alipay(adb)
            open_my_page(adb)
        account_phone = extract_account_phone(adb)
        print(f"ACCOUNT {account_phone or '(not recognized)'}")
        ledger_plan = prepare_ledger_sync(args, account_phone)
        if args.sync_ledger and ledger_plan is not None and not ledger_plan.need_card_items:
            return [], ledger_plan
        x, y = locate_bill_button(adb)
        print(f"账单 OCR point: {x},{y}")
        adb.tap(x, y)
        time.sleep(3)

    if args.sync_ledger and ledger_plan is not None and not ledger_plan.need_card_items:
        return [], ledger_plan

    cutoff = parse_end_date(args.end_date or "4-1", year)
    print(f"cutoff: include orders on/after {cutoff.isoformat()}")

    results: list[HotelOrderResult] = []
    abnormal_records: list[dict[str, object]] = []
    seen_orders: set[str] = set()

    for screen_index in range(args.max_scrolls + 1):
        list_boxes = ocr_region(adb, (0, 330, 1080, 1960), f"bill-list-screen-{screen_index}")
        screen_orders = parse_bill_orders_from_ocr_boxes(list_boxes)
        hotel_orders = [
            order
            for order in screen_orders
            if order.title == "酒店订单" and order.date(year) >= cutoff and order.raw not in seen_orders
        ]
        print(f"screen {screen_index}: orders={len(screen_orders)}, new_hotel_orders={len(hotel_orders)}")
        for order in hotel_orders:
            print("HOTEL_ORDER", json.dumps(bill_order_record(order, year), ensure_ascii=False))

        for index, order in enumerate(hotel_orders, start=1):
            seen_orders.add(order.raw)
            print(f"open detail {index}/{len(hotel_orders)} on screen {screen_index}: {order.key}")
            if not open_order_detail(adb, order, list_boxes):
                abnormal_records.append(
                    {
                        "reason": "order_not_visible_or_not_opened",
                        "list_order": bill_order_record(order, year),
                    }
                )
                continue
            detail = read_detail(adb, account_phone, order, year)
            result = detail.result
            missing_fields = [
                field
                for field, value in {
                    "detail_payment_time": detail.detail_payment_time,
                    "detail_order_amount": result.amount,
                    "payment_method": result.payment_method,
                    "merchant": result.merchant,
                }.items()
                if not value
            ]
            if missing_fields or not detail.time_matches:
                abnormal_records.append(
                    {
                        "reason": "missing_fields" if missing_fields else "time_mismatch",
                        "missing_fields": missing_fields,
                        "list_payment_time": detail.list_payment_time,
                        "detail_payment_time": detail.detail_payment_time,
                        "list_order": bill_order_record(order, year),
                        "detail_result": asdict(result),
                    }
                )
            else:
                results.append(result)
            adb.back()
            time.sleep(1.5)

        if screen_has_order_before_cutoff(screen_orders, cutoff, year):
            print(f"reached order before cutoff on screen {screen_index}; stop")
            break
        if screen_index >= args.max_scrolls:
            print(f"reached max-scrolls={args.max_scrolls}; stop")
            break
        scroll_half_screen(adb)

    print("FINAL_RESULTS", json.dumps(results_record(results), ensure_ascii=False))
    print("ABNORMAL_RECORDS", json.dumps(abnormal_records, ensure_ascii=False))
    return results, ledger_plan


def run_self_test() -> int:
    assert parse_end_date("4-1", 2026) == dt.date(2026, 4, 1)
    assert parse_end_date("4月1日", 2026) == dt.date(2026, 4, 1)
    xml = """<hierarchy>
      <node text="酒店订单，-49,979.90元，，酒店旅游，，05-06 12:00" bounds="[1,2][3,4]" class="android.widget.Button" clickable="true"/>
      <node text="便民餐车，-13.85元，，餐饮美食，，04-27 19:24" bounds="[1,2][3,4]" class="android.widget.Button" clickable="true"/>
      <node text="中信银行信用卡(0983)" bounds="[1,2][3,4]" class="android.widget.TextView" clickable="false"/>
      <node text="收款方全称" bounds="[1,2][3,4]" class="android.widget.TextView" clickable="false"/>
      <node text="南京梓如旅行社有限公司" bounds="[1,2][3,4]" class="android.widget.TextView" clickable="false"/>
    </hierarchy>""".encode()
    nodes = parse_nodes(xml)
    orders = parse_orders(nodes)
    assert len(orders) == 2
    assert orders[0].key == "酒店订单|-49,979.90|05-06 12:00"
    assert parse_payment_method(nodes) == ("中信银行", "0983", "中信银行信用卡(0983)")
    assert parse_detail_merchant(nodes) == "南京梓如旅行社有限公司"
    ocr_orders = parse_hotel_orders_from_ocr_boxes(
        [
            OCRTextBox("酒店订单", (188, 1040, 352, 1082), 1.0),
            OCRTextBox("-24,929.98", (791, 1036, 1018, 1090), 1.0),
            OCRTextBox("酒店旅游", (188, 1116, 331, 1151), 1.0),
            OCRTextBox("05-0712:08", (188, 1188, 366, 1219), 0.99),
        ]
    )
    assert len(ocr_orders) == 1
    assert ocr_orders[0].key == "酒店订单|-24,929.98|05-07 12:08"
    detail_boxes = [
        OCRTextBox("订单金额", (68, 729, 220, 776), 1.0),
        OCRTextBox("49986.00", (338, 724, 520, 784), 1.0),
        OCRTextBox("支付时间", (68, 913, 220, 963), 1.0),
        OCRTextBox("2026-05-06 12:00:41", (338, 908, 780, 968), 1.0),
        OCRTextBox("付款方式", (68, 1007, 220, 1054), 1.0),
        OCRTextBox("中信银行信用卡(0983)", (338, 1001, 760, 1062), 1.0),
        OCRTextBox("收款方全称", (68, 1395, 258, 1444), 1.0),
        OCRTextBox("南京梓如旅行社有限公司", (338, 1389, 830, 1450), 1.0),
    ]
    assert parse_detail_order_amount_from_ocr(detail_boxes) == "49986.00"
    one_decimal_amount_boxes = [
        OCRTextBox("订单金额", (68, 729, 220, 776), 1.0),
        OCRTextBox("39944.0", (338, 724, 520, 784), 1.0),
    ]
    assert parse_detail_order_amount_from_ocr(one_decimal_amount_boxes) == "39944.00"
    o_confused_amount_boxes = [
        OCRTextBox("订单金额", (68, 729, 220, 776), 1.0),
        OCRTextBox("49986.O0", (338, 724, 520, 784), 1.0),
    ]
    assert parse_detail_order_amount_from_ocr(o_confused_amount_boxes) == "49986.00"
    integer_amount_boxes = [
        OCRTextBox("订单金额", (68, 729, 220, 776), 1.0),
        OCRTextBox("49986", (338, 724, 520, 784), 1.0),
    ]
    assert parse_detail_order_amount_from_ocr(integer_amount_boxes) == "49986.00"
    assert normalize_order_amount("-49,986.00") == "49986.00"
    assert normalize_order_amount("+19,951.9") == "19951.90"
    assert parse_detail_payment_time_from_ocr(detail_boxes) == "2026-05-06 12:00"
    assert payment_times_match("2026-05-07 12:08", "2026-05-07 12:11")
    assert payment_times_match("2026-05-07 12:08", "2026-05-07 12:38")
    assert not payment_times_match("2026-05-07 12:08", "2026-05-07 12:39")
    assert parse_payment_method_from_ocr(detail_boxes) == ("中信银行", "0983", "中信银行信用卡(0983)")
    assert parse_detail_merchant_from_ocr(detail_boxes) == "南京梓如旅行社有限公司"
    assert parse_result_amount_int("49986.00") == 49986
    assert parse_result_amount_int("49,986.00") == 49986
    assert parse_result_amount_int("49986.50") is None
    assert alipay_account_suffix("171 ******01") == "01"
    assert alipay_account_suffix("171******02") == "02"
    assert alipay_account_suffix("186******79") == "79"
    assert ledger_account_for_alipay("171 ******01") == "wei"
    assert ledger_account_for_alipay("171 ******02") == "wei"
    assert ledger_account_for_alipay("186******79") == "chang"
    ledger_items_for_test = [
        {
            "id": 1,
            "purchase_time": "2026-05-06 11:45:00",
            "purchase_amount": 49986,
            "payment_card_bank": "",
            "payment_card_last_digits": "",
        },
        {
            "id": 2,
            "purchase_time": "2026-05-06 10:00:00",
            "purchase_amount": 49986,
            "payment_card_bank": "",
            "payment_card_last_digits": "",
        },
    ]
    result_for_test = HotelOrderResult(
        account_phone="171 ******01",
        order_date="2026-05-06",
        order_time="12:00",
        title="酒店订单",
        amount="49986.00",
        bank_name="中信银行",
        card_tail="0983",
        payment_method="中信银行信用卡(0983)",
        merchant="南京梓如旅行社有限公司",
        raw_order="酒店订单，-49,986.00元，，酒店旅游，，05-06 12:00",
    )
    matches, reason = ledger_match_candidates(result_for_test, ledger_items_for_test, tolerance_minutes=20)
    assert reason == "" and len(matches) == 1 and matches[0]["id"] == 1
    matches, reason = ledger_match_candidates(result_for_test, ledger_items_for_test, tolerance_minutes=14)
    assert reason == "no_match" and matches == []
    matches, reason = ledger_match_candidates(
        result_for_test,
        [ledger_items_for_test[0], {**ledger_items_for_test[0], "id": 3, "purchase_time": "2026-05-06 12:05:00"}],
        tolerance_minutes=20,
    )
    assert reason == "multiple_matches" and len(matches) == 2
    print("self-test passed")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Alipay hotel-order payment card info from bill details.")
    parser.add_argument("--end-date", required=False, default="", help="Stop date, e.g. 4-1 means include Apr 1 and later.")
    parser.add_argument("--year", type=int, default=dt.date.today().year, help="Year for bill dates that only show MM-DD.")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="Path to adb.")
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone.")
    parser.add_argument("--start-current", action="store_true", help="Assume Alipay 我的 page is already open.")
    parser.add_argument("--start-bill-page", action="store_true", help="Assume the bill list page is already open.")
    parser.add_argument("--account-phone", default="", help="Account phone mask to include when using --start-bill-page.")
    parser.add_argument("--max-scrolls", type=int, default=20, help="Maximum bill-list scrolls.")
    parser.add_argument("--output", default="", help="Optional JSON output path.")
    parser.add_argument(
        "--no-sync-ledger",
        dest="sync_ledger",
        action="store_false",
        help="Only collect Alipay hotel-order details; do not sync payment card info to the ChaKe ledger.",
    )
    parser.set_defaults(sync_ledger=True)
    parser.add_argument(
        "--ledger-account",
        default="",
        help="Override ChaKe ledger account name if the Alipay 01/02 account cannot be detected.",
    )
    parser.add_argument("--ledger-lookback-days", type=int, default=DEFAULT_LEDGER_LOOKBACK_DAYS, help="Days of recent ledger records to inspect.")
    parser.add_argument(
        "--match-tolerance-minutes",
        type=int,
        default=DEFAULT_LEDGER_MATCH_TOLERANCE_MINUTES,
        help="Maximum allowed time delta between Alipay order time and ledger purchase_time.",
    )
    parser.add_argument("--dry-sync", action="store_true", help="Print ledger updates without POSTing them.")
    parser.add_argument("--self-test", action="store_true", help="Run local parser tests.")
    return parser.parse_args()


def prepare_ledger_sync(args: argparse.Namespace, account_phone: str) -> LedgerSyncPlan | None:
    if not args.sync_ledger:
        return None
    account = args.ledger_account.strip() or ledger_account_for_alipay(account_phone)
    if not account:
        raise RuntimeError(
            "could not map current Alipay account to ledger account; "
            "make sure the phone mask ends with 01/02, or pass --ledger-account as an override"
        )
    print(
        "ALIPAY_LEDGER_ACCOUNT",
        json.dumps(
            {
                "account_phone": account_phone,
                "alipay_suffix": alipay_account_suffix(account_phone),
                "ledger_account": account,
                "override": bool(args.ledger_account.strip()),
            },
            ensure_ascii=False,
        ),
    )
    plan = build_ledger_sync_plan(account, args.ledger_lookback_days)
    print(
        "LEDGER_NEED_SYNC",
        json.dumps(
            {
                "account": plan.account,
                "count": len(plan.need_card_items),
                "end_date": plan.end_date.isoformat() if plan.end_date else "",
                "items": plan.need_card_items,
            },
            ensure_ascii=False,
        ),
    )
    if not plan.need_card_items:
        print("no ledger records need payment card sync")
        return plan
    if not args.end_date and plan.end_date is not None:
        args.end_date = format_end_date(plan.end_date)
        print(f"auto end-date from ledger: {args.end_date}")
    return plan


def main() -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    args = parse_args()
    if args.self_test:
        return run_self_test()
    results, ledger_plan = collect_hotel_orders(args)
    if args.output:
        write_results(args.output, results)
        print(f"wrote {args.output}")
    if ledger_plan is not None:
        sync_summary = sync_results_to_ledger(
            results,
            ledger_plan,
            tolerance_minutes=args.match_tolerance_minutes,
            dry_sync=args.dry_sync,
        )
        print("LEDGER_SYNCED", json.dumps(sync_summary.synced, ensure_ascii=False))
        print_ledger_sync_success_summary(sync_summary.synced)
        print("LEDGER_SKIPPED", json.dumps(sync_summary.skipped, ensure_ascii=False))
        print("LEDGER_ABNORMAL", json.dumps(sync_summary.abnormal, ensure_ascii=False))
    print(f"done: {len(results)} hotel order details")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
