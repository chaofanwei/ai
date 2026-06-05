#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""Switch Alipay between configured accounts.

Default mode is dry-run. Use --execute to operate the phone.

Examples:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python alipay-switch-account.py --execute
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python alipay-switch-account.py --execute --target 02
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python alipay-switch-account.py --execute --target 79
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


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
DEFAULT_UNLOCK_SCRIPT = str(SCRIPT_DIR / "unlock.sh")
ALIPAY_PACKAGE = "com.eg.android.AlipayGphone"
REMOTE_XML = "/sdcard/window.xml"
SCREENSHOT_PATH = Path("/private/tmp/alipay_switch_account_screen.png")
_OCR_ENGINE: object | None = None

MY_TAB_FALLBACK = (972, 2090)
SETTINGS_FALLBACK = (1005, 155)
ACCOUNT_LABELS = ("01", "02", "79")
AUTO_SWITCH_LABELS = ("01", "02")
CURRENT_MARKERS = ("当前", "已登录", "正在使用")


@dataclass(frozen=True)
class UINode:
    text: str
    content_desc: str
    resource_id: str
    bounds: str
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

    def haystack(self) -> str:
        return "\n".join((self.text, self.content_desc, self.resource_id))

    def matches(self, label: str) -> bool:
        return self.text == label or self.content_desc == label

    def contains(self, pattern: str) -> bool:
        return pattern in self.haystack()


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

    def tap_node(self, node: UINode) -> None:
        x, y = node.center
        self.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 600) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if not self.dry_run:
            self.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)], timeout=6)
            time.sleep(1.0)

    def back(self) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}back")
        if not self.dry_run:
            self.shell(["input", "keyevent", "4"], timeout=4)
            time.sleep(0.8)

    def screencap(self, path: Path = SCREENSHOT_PATH) -> Path:
        proc = self.run(["exec-out", "screencap", "-p"], timeout=12)
        path.write_bytes(proc.stdout)
        return path

    def dump_nodes(self) -> list[UINode]:
        if self.dry_run:
            return []
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
        text = node.attrib.get("text", "")
        content_desc = node.attrib.get("content-desc", "")
        resource_id = node.attrib.get("resource-id", "")
        if not text and not content_desc and not resource_id:
            continue
        nodes.append(
            UINode(
                text=text,
                content_desc=content_desc,
                resource_id=resource_id,
                bounds=node.attrib.get("bounds", ""),
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


def ocr_screen(
    adb: ADB,
    label: str,
    min_score: float = 0.45,
    crop_box: tuple[int, int, int, int] | None = None,
) -> list[OCRTextBox]:
    if adb.dry_run:
        print(f"[dry-run] would OCR screen: {label}")
        return []
    image_path = adb.screencap()
    dx = 0
    dy = 0
    ocr_path = image_path
    if crop_box is not None:
        from PIL import Image

        x1, y1, x2, y2 = crop_box
        crop_path = image_path.with_name(f"{image_path.stem}_{label}_crop.png")
        with Image.open(image_path) as image:
            image.crop(crop_box).save(crop_path)
        dx = x1
        dy = y1
        ocr_path = crop_path
    engine = get_ocr_engine()
    result = engine.predict(str(ocr_path))  # type: ignore[attr-defined]
    boxes = [
        OCRTextBox(box.text, (box.box[0] + dx, box.box[1] + dy, box.box[2] + dx, box.box[3] + dy), box.score)
        for box in parse_paddleocr_result(result)
        if box.score >= min_score
    ]
    boxes = [box for box in boxes if box.visible]
    recognized = ", ".join(f"{box.text}@{box.box}:{box.score:.2f}" for box in boxes)
    print(f"OCR {label}: {recognized}")
    return boxes


def normalized_ocr_text(text: str) -> str:
    return (
        text.replace("帳", "账")
        .replace("賬", "账")
        .replace("號", "号")
        .replace(" ", "")
        .replace("*", "")
        .replace("＊", "")
    )


def ocr_digits(text: str) -> str:
    return re.sub(r"\D", "", text)


def text_matches_account_label(text: str, label: str) -> bool:
    normalized = normalized_ocr_text(text)
    if re.search(rf"(^|\D){re.escape(label)}($|\D)", normalized):
        return True
    digits = ocr_digits(text)
    return len(digits) >= 5 and digits.endswith(label) and ("*" in text or "＊" in text)


def row_ocr_text(boxes: list[OCRTextBox], box: OCRTextBox, y_tolerance: int = 90) -> str:
    _, y = box.center
    parts = [candidate.text for candidate in boxes if abs(candidate.center[1] - y) <= y_tolerance]
    return " ".join(parts)


def find_ocr_text(boxes: list[OCRTextBox], patterns: tuple[str, ...]) -> OCRTextBox | None:
    for box in sorted(boxes, key=lambda item: (item.box[1], item.box[0])):
        text = normalized_ocr_text(box.text)
        if any(pattern in text for pattern in patterns):
            return box
    return None


def detect_account_from_my_page(adb: ADB) -> str:
    print("detect current account on 我的")
    if adb.dry_run:
        print("[dry-run] would OCR current account on 我的")
        return ""
    boxes = ocr_screen(adb, "my-page-current-account", crop_box=(0, 0, 1080, 585))
    candidates = [
        box
        for box in boxes
        if 220 <= box.center[1] <= 520 and ("*" in box.text or "＊" in box.text)
    ]
    for box in sorted(candidates, key=lambda item: (item.box[1], item.box[0])):
        for label in ACCOUNT_LABELS:
            if text_matches_account_label(box.text, label):
                print(f"current account: {label} ({box.text})")
                return label

    recognized = ", ".join(f"{box.text}@{box.box}" for box in boxes)
    raise RuntimeError(f"could not detect current 01/02 account on 我的 page by OCR; saw: {recognized}")


def other_account_label(current: str) -> str:
    if current == "01":
        return "02"
    if current == "02":
        return "01"
    raise RuntimeError(f"cannot auto-switch from account {current!r}; rerun with --target 01, --target 02, or --target 79")


def visible_text(nodes: list[UINode]) -> list[str]:
    values: list[str] = []
    for node in nodes:
        if not node.visible:
            continue
        if node.text:
            values.append(node.text)
        if node.content_desc:
            values.append(node.content_desc)
    return values


def has_text(nodes: list[UINode], pattern: str) -> bool:
    return any(node.visible and node.contains(pattern) for node in nodes)


def find_visible(nodes: list[UINode], label: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.matches(label)]


def find_visible_contains(nodes: list[UINode], pattern: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.contains(pattern)]


def wait_for_any_text(adb: ADB, candidates: list[str], timeout_s: int) -> list[UINode]:
    if adb.dry_run:
        print(f"[dry-run] would wait for any text: {', '.join(candidates)}")
        return []
    deadline = time.time() + timeout_s
    last_nodes: list[UINode] = []
    while time.time() < deadline:
        last_nodes = adb.dump_nodes()
        if any(has_text(last_nodes, candidate) for candidate in candidates):
            return last_nodes
        time.sleep(0.5)
    return last_nodes


def tap_label(adb: ADB, nodes: list[UINode], label: str) -> bool:
    matches = find_visible(nodes, label)
    if not matches:
        matches = find_visible_contains(nodes, label)
    if not matches:
        return False
    preferred = next((node for node in matches if node.clickable), matches[0])
    adb.tap_node(preferred)
    return True


def row_text(nodes: list[UINode], node: UINode, y_tolerance: int = 80) -> str:
    _, y = node.center
    parts: list[str] = []
    for candidate in nodes:
        if not candidate.visible:
            continue
        _, cy = candidate.center
        if abs(cy - y) <= y_tolerance:
            parts.append(candidate.text)
            parts.append(candidate.content_desc)
    return " ".join(part for part in parts if part)


def launch_alipay(adb: ADB, *, force_relaunch: bool) -> None:
    print("launch Alipay")
    if adb.dry_run:
        return
    if force_relaunch:
        adb.shell(["am", "force-stop", ALIPAY_PACKAGE], timeout=8)
        time.sleep(1)
    adb.run(["shell", "monkey", "-p", ALIPAY_PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
    time.sleep(4)


def open_my_page(adb: ADB) -> None:
    print("open 我的")
    # The Alipay home page can also contain labels like 账单/余额宝, and the
    # current 我的 page is Compose-based on this phone, so the hierarchy often
    # hides the page body. A direct tab tap is more reliable than text probing.
    adb.tap(*MY_TAB_FALLBACK)
    if not adb.dry_run:
        time.sleep(4)


def open_settings(adb: ADB) -> None:
    print("open 设置")
    if adb.dry_run:
        print("[dry-run] would OCR top area and tap 设置")
        return
    top_boxes = ocr_screen(adb, "my-page-top-before-settings", crop_box=(0, 0, 1080, 585))
    if not any("*" in box.text or "＊" in box.text for box in top_boxes):
        print("warning: account marker not detected before tapping settings")
    # The settings entry is a gear icon without reliable OCR text, but it is in
    # the top area beside the account header.
    adb.tap(*SETTINGS_FALLBACK)
    if adb.dry_run:
        return
    time.sleep(2)
    nodes = wait_for_any_text(adb, ["设置"], timeout_s=6)
    if not has_text(nodes, "设置"):
        print(f"warning: settings title not detected; saw: {visible_text(nodes)}")


def open_login_other_account(adb: ADB) -> None:
    print("open 登录其他账号")
    if adb.dry_run:
        print("[dry-run] would OCR and tap 登录其他账号")
        return
    for attempt in range(3):
        boxes = ocr_screen(
            adb,
            f"settings-login-other-attempt-{attempt + 1}",
            crop_box=(0, 1600, 1080, 2135),
        )
        target = find_ocr_text(boxes, ("登录其他账号", "登录其他帐号", "其他账号", "其他帐号"))
        if target is not None:
            x, y = target.center
            print(f"tap 登录其他账号 by OCR at {x} {y}")
            adb.tap(x, y)
            time.sleep(2)
            return
        if attempt < 2:
            print("登录其他账号 not found by OCR; scroll slightly")
            adb.swipe(540, 1700, 540, 1250, 450)
    raise RuntimeError("could not locate 登录其他账号 by OCR")


def account_nodes(nodes: list[UINode]) -> dict[str, list[UINode]]:
    result: dict[str, list[UINode]] = {label: [] for label in ACCOUNT_LABELS}
    for node in nodes:
        if not node.visible:
            continue
        text = node.haystack()
        for label in ACCOUNT_LABELS:
            if re.search(rf"(^|\D){re.escape(label)}($|\D)", text):
                result[label].append(node)
    return {label: items for label, items in result.items() if items}


def choose_target(nodes: list[UINode], requested_target: str) -> tuple[str, UINode]:
    accounts = account_nodes(nodes)
    if requested_target:
        requested_nodes = accounts.get(requested_target)
        if not requested_nodes:
            raise RuntimeError(f"target account {requested_target} is not visible; saw: {visible_text(nodes)}")
        return requested_target, requested_nodes[0]

    current_labels: set[str] = set()
    for label, matches in accounts.items():
        for node in matches:
            text = row_text(nodes, node)
            if any(marker in text for marker in CURRENT_MARKERS):
                current_labels.add(label)

    if len(current_labels) == 1:
        current = next(iter(current_labels))
        if current not in AUTO_SWITCH_LABELS:
            raise RuntimeError(
                f"cannot auto-switch from account {current}; rerun with --target 01, --target 02, or --target 79"
            )
        target = other_account_label(current)
        target_nodes = accounts.get(target)
        if not target_nodes:
            raise RuntimeError(f"current account appears to be {current}, but account {target} is not visible")
        return target, target_nodes[0]

    if len(accounts) == 1:
        label, matches = next(iter(accounts.items()))
        return label, matches[0]

    raise RuntimeError(
        "could not infer the current Alipay account from the switch page; "
        "rerun with --target 01 or --target 02"
    )


def account_ocr_boxes(boxes: list[OCRTextBox]) -> dict[str, list[OCRTextBox]]:
    result: dict[str, list[OCRTextBox]] = {label: [] for label in ACCOUNT_LABELS}
    for box in boxes:
        for label in ACCOUNT_LABELS:
            if text_matches_account_label(box.text, label):
                result[label].append(box)
    return {label: items for label, items in result.items() if items}


def choose_target_ocr(boxes: list[OCRTextBox], target_label: str) -> OCRTextBox:
    accounts = account_ocr_boxes(boxes)
    target_boxes = accounts.get(target_label)
    if not target_boxes:
        recognized = ", ".join(f"{box.text}@{box.box}" for box in boxes)
        raise RuntimeError(f"target account {target_label} was not found by OCR on switch page; saw: {recognized}")
    return sorted(target_boxes, key=lambda item: item.box[1])[0]


def switch_account(adb: ADB, target: str) -> str:
    print(f"choose target account {target}")
    if adb.dry_run:
        print(f"[dry-run] would find and tap account {target}")
        return target

    nodes = adb.dump_nodes()
    if nodes:
        try:
            _, node = choose_target(nodes, target)
            x, y = node.center
            print(f"tap account {target} by UI node at {x} {y}")
            adb.tap_node(node)
            time.sleep(3)
            print(f"switched to account {target}")
            return target
        except RuntimeError as exc:
            print(f"UI node account lookup failed: {exc}")

    boxes = ocr_screen(adb, "account-switch", crop_box=(270, 585, 810, 1755))
    box = choose_target_ocr(boxes, target)
    x, y = box.center
    print(f"tap account {target} by OCR at {x} {y}")
    adb.tap(x, y)
    time.sleep(3)
    print(f"switched to account {target}")
    return target


def device_needs_unlock(adb: ADB) -> bool:
    window_text = adb.shell(["dumpsys", "window"], timeout=10).stdout.decode("utf-8", "replace")
    power_text = adb.shell(["dumpsys", "power"], timeout=10).stdout.decode("utf-8", "replace")

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
        "isStatusBarKeyguard=true",
        "mShowingLockscreen=true",
    )
    unlocked_markers = ("showing=false", "mIsShowing=false", "inputRestricted=false", "mInputRestricted=false")

    if any(marker in power_text or marker in window_text for marker in screen_off_markers):
        return True
    if any(marker in window_text for marker in locked_markers):
        return True
    if any(marker in window_text for marker in unlocked_markers):
        return False
    print("warning: could not confidently determine lock state; assuming unlocked")
    return False


def ensure_unlocked(adb: ADB, unlock_script: str) -> None:
    if adb.dry_run:
        print("[dry-run] would check lock state")
        return
    if not device_needs_unlock(adb):
        print("screen appears unlocked")
        return

    script = Path(unlock_script)
    if not script.exists():
        fallback = SCRIPT_DIR / script.name
        if fallback.exists():
            script = fallback
        else:
            raise FileNotFoundError(f"unlock script not found: {unlock_script}")
    print(f"screen is locked/off; running {script.resolve()}")
    subprocess.run([str(script.resolve())], check=True, timeout=30, cwd=str(SCRIPT_DIR))
    time.sleep(1)


def run(args: argparse.Namespace) -> int:
    ensure_adb_exists(args.adb)
    adb = ADB(args.adb, dry_run=not args.execute)

    if args.execute and not args.skip_unlock_check:
        ensure_unlocked(adb, args.unlock_script)

    launch_alipay(adb, force_relaunch=args.execute or args.relaunch)
    open_my_page(adb)
    current_account = detect_account_from_my_page(adb)
    target_account = args.target or (other_account_label(current_account) if current_account else "auto")
    print(f"target account: {target_account}")

    if current_account and current_account == target_account:
        print(f"already on target account {target_account}; no switch needed")
        if args.execute:
            print(f"done: Alipay is on account {target_account}")
        else:
            print("done: dry-run finished")
        return 0

    open_settings(adb)
    open_login_other_account(adb)
    switched_to = switch_account(adb, target_account)

    open_my_page(adb)
    if args.execute:
        verified_account = detect_account_from_my_page(adb)
        if verified_account != target_account:
            raise RuntimeError(f"switch verification failed: expected {target_account}, saw {verified_account}")
        print(f"verified: now on account {verified_account}")

    if args.execute:
        print(f"done: Alipay switched to account {switched_to}")
    else:
        print("done: dry-run finished")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Switch Alipay between configured accounts.")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="Path to adb.")
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone.")
    parser.add_argument("--target", choices=ACCOUNT_LABELS, default="", help="Explicit target account. Without it, auto-switches between 01 and 02.")
    parser.add_argument("--relaunch", action="store_true", help="Compatibility option; --execute already force-stops Alipay before launching.")
    parser.add_argument("--skip-unlock-check", action="store_true", help="Skip screen lock detection and unlock.sh.")
    parser.add_argument("--unlock-script", default=DEFAULT_UNLOCK_SCRIPT, help="Path to unlock.sh.")
    return parser.parse_args()


def main() -> int:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    args = parse_args()
    return run(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
