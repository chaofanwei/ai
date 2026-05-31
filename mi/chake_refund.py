#!/usr/bin/env python3
"""Automate ChaKe VIP-card refund requests through ADB.

Default mode is dry-run: it only reads and prints the current UI state.
Use --execute to perform taps/swipes and submit eligible refund requests.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

WECHAT_MSG_URL = "http://myroute.cn/msg"
WECHAT_MAX_LINES = 5
WECHAT_MAX_LINE_LEN = 40

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_UNLOCK_SCRIPT = str(SCRIPT_DIR / "unlock.sh")
DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
PACKAGE = "com.slwy.shanglvwuyou"
GREETING_RE = re.compile(r"您好[，,]?\s*(\S+)")


@dataclass(frozen=True)
class RefundRecord:
    order_date: str
    amount: str


@dataclass(frozen=True)
class UINode:
    text: str
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
        return x2 > x1 and y2 > y1 and y2 > 245 and y1 < 2070

    @property
    def center(self) -> tuple[int, int]:
        values = self.nums
        if values is None:
            raise ValueError(f"invalid bounds: {self.bounds}")
        x1, y1, x2, y2 = values
        return (x1 + x2) // 2, (y1 + y2) // 2

    @property
    def center_y(self) -> int:
        return self.center[1]


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
            stderr = proc.stderr.decode("utf-8", "replace").strip()
            stdout = proc.stdout.decode("utf-8", "replace").strip()
            raise RuntimeError(f"adb {' '.join(args)} failed: {stderr or stdout}")
        return proc

    def shell(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell", *args], timeout=timeout)

    def tap(self, x: int, y: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(0.8)

    def tap_node(self, node: UINode) -> None:
        x, y = node.center
        self.tap(x, y)

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
        root = ET.fromstring(proc.stdout)
        nodes: list[UINode] = []
        for node in root.iter("node"):
            text = node.attrib.get("text", "")
            if not text:
                continue
            nodes.append(
                UINode(
                    text=text,
                    bounds=node.attrib.get("bounds", ""),
                    clickable=node.attrib.get("clickable", "false") == "true",
                )
            )
        return nodes


def output_text(proc: subprocess.CompletedProcess[bytes]) -> str:
    return proc.stdout.decode("utf-8", "replace") + proc.stderr.decode("utf-8", "replace")


def device_needs_unlock(adb: ADB) -> bool:
    window_text = output_text(adb.shell(["dumpsys", "window"], timeout=10))
    power_text = output_text(adb.shell(["dumpsys", "power"], timeout=10))

    screen_off_markers = (
        "mWakefulness=Asleep",
        "mWakefulness=Dozing",
        "Display Power: state=OFF",
        "screenState=SCREEN_STATE_OFF",
        "interactiveState=INTERACTIVE_STATE_SLEEP",
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

    # If the keyguard state is unclear, leave the device untouched.
    print("warning: could not confidently determine lock state; assuming unlocked")
    return False


def resolve_unlock_script(unlock_script: str) -> Path:
    candidate = Path(unlock_script)
    if candidate.exists():
        return candidate.resolve()
    fallback = SCRIPT_DIR / candidate.name
    if fallback.exists():
        return fallback.resolve()
    raise FileNotFoundError(f"unlock script not found: {unlock_script} (also tried {fallback})")


def ensure_unlocked(adb: ADB, unlock_script: str) -> None:
    if not device_needs_unlock(adb):
        print("screen appears unlocked")
        return

    script = resolve_unlock_script(unlock_script)
    print(f"screen is locked/off; running {script}")
    subprocess.run([str(script)], check=True, timeout=30, cwd=str(SCRIPT_DIR))
    time.sleep(1)


def status_nodes(nodes: list[UINode]) -> list[UINode]:
    statuses = {"申请退款", "已退款", "预订取消", "等待确认"}
    return [
        node
        for node in nodes
        if node.visible and (node.text.startswith("2026-") or node.text in statuses)
    ]


def find_visible(nodes: list[UINode], text: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.text == text]


def has_text(nodes: list[UINode], pattern: str) -> bool:
    return any(pattern in node.text for node in nodes)


def nearest_order_date(rows: list[UINode], refund_node: UINode) -> str:
    dates = [node for node in rows if node.text.startswith("2026-")]
    above = [node for node in dates if node.center_y <= refund_node.center_y]
    candidates = above or dates
    if not candidates:
        return f"unknown@{refund_node.bounds}"
    return min(candidates, key=lambda node: abs(node.center_y - refund_node.center_y)).text


def nearest_order_amount(nodes: list[UINode], refund_node: UINode) -> str:
    amounts = [node for node in nodes if node.visible and node.text.startswith("￥")]
    above = [node for node in amounts if node.center_y <= refund_node.center_y]
    candidates = above or amounts
    if not candidates:
        return "金额未知"
    return min(candidates, key=lambda node: abs(node.center_y - refund_node.center_y)).text


def detect_account_name(nodes: list[UINode]) -> str | None:
    for node in nodes:
        if not node.visible:
            continue
        match = GREETING_RE.search(node.text)
        if match:
            return match.group(1).strip()
    return None


def account_prefix(account_name: str | None) -> str:
    if account_name:
        return f"差客退款[{account_name}]"
    return "差客退款"


def truncate_wechat_line(text: str, max_len: int = WECHAT_MAX_LINE_LEN) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def build_wechat_message(
    records: list[RefundRecord],
    *,
    had_refundable_order: bool,
    account_name: str | None,
) -> str:
    prefix = account_prefix(account_name)
    if not records:
        if not had_refundable_order:
            return f"{prefix}:本次无可申请退款的订单"
        return f"{prefix}:本次未进入退款申请页"
    lines = [truncate_wechat_line(f"{prefix}:成功{len(records)}笔")]
    detail_slots = WECHAT_MAX_LINES - 1
    for index, record in enumerate(records):
        if index >= detail_slots - 1 and len(records) > detail_slots:
            extra = len(records) - (detail_slots - 1)
            lines.append(truncate_wechat_line(f"另有{extra}笔见运行日志"))
            break
        lines.append(truncate_wechat_line(f"{record.order_date} {record.amount}"))
    return "\n".join(lines[:WECHAT_MAX_LINES])


def send_wechat_message(message: str) -> None:
    url = f"{WECHAT_MSG_URL}?{urllib.parse.urlencode({'echostr': message})}"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            print(f"wechat notify sent: HTTP {response.status}")
    except Exception as exc:
        print(f"warning: wechat notify failed: {exc}")


def print_rows(rows: list[UINode]) -> None:
    if not rows:
        print("visible status rows: <none>")
        return
    print("visible status rows:")
    for node in rows:
        click = " clickable" if node.clickable else ""
        print(f"  {node.text} {node.bounds}{click}")


def wait_for_any_text(adb: ADB, candidates: list[str], timeout_s: int) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            nodes = adb.dump_nodes()
        except Exception:
            time.sleep(0.5)
            continue
        texts = [node.text for node in nodes]
        if any(candidate in text for candidate in candidates for text in texts):
            return True
        time.sleep(0.5)
    return False


def launch_and_navigate(adb: ADB) -> str | None:
    print("force-stop app")
    adb.shell(["am", "force-stop", PACKAGE], timeout=8)
    time.sleep(0.8)

    print("launch app")
    adb.run(["shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
    if not wait_for_any_text(adb, ["首页", "我的行程", "出差申请"], timeout_s=20):
        print("warning: home page text not detected before tapping 我的")

    print("open 我的")
    adb.tap(898, 2098)
    account_name: str | None = None
    if wait_for_any_text(adb, ["我的订单", "个人信息", "贵宾VIP卡"], timeout_s=10):
        account_name = detect_account_name(adb.dump_nodes())
        if account_name:
            print(f"current account: {account_name}")
        else:
            print("warning: could not detect account name on 我的 page")
    else:
        print("warning: 我的 page text not detected before tapping 贵宾VIP卡")

    print("open 贵宾VIP卡")
    adb.tap(165, 732)
    if not wait_for_any_text(adb, ["贵宾VIP卡订单列表"], timeout_s=10):
        print("warning: order list title not detected after tapping 贵宾VIP卡")

    print("move floating window left")
    adb.swipe(820, 330, 180, 330, 700)
    return account_name


def click_ok_if_present(adb: ADB) -> bool:
    nodes = adb.dump_nodes()
    ok_nodes = find_visible(nodes, "确定")
    if ok_nodes:
        adb.tap_node(ok_nodes[0])
        return True
    return False


def process_refund_button(adb: ADB, refund_node: UINode) -> tuple[int, int, str, bool]:
    adb.tap_node(refund_node)

    submitted = 0
    already_submitted = 0
    entered_refund_page = False
    tapped_submit_bounds: set[str] = set()

    for _ in range(24):
        time.sleep(0.3)
        nodes = adb.dump_nodes()

        if has_text(nodes, "退款订单已经提交"):
            print("refund already submitted prompt detected")
            click_ok_if_present(adb)
            already_submitted += 1
            return submitted, already_submitted, "already_submitted", entered_refund_page

        submit_nodes = find_visible(nodes, "提交申请")
        submit_node = next((node for node in submit_nodes if node.bounds not in tapped_submit_bounds), None)
        if submit_node is not None:
            entered_refund_page = True
            print("refund application page detected; submit")
            tapped_submit_bounds.add(submit_node.bounds)
            adb.tap_node(submit_node)
            time.sleep(0.8)
            nodes = adb.dump_nodes()
            if has_text(nodes, "提交成功"):
                print("submit success prompt detected")
            click_ok_if_present(adb)
            submitted += 1
            continue

        if has_text(nodes, "提交成功"):
            print("submit success prompt detected")
            click_ok_if_present(adb)
            if submitted == 0:
                submitted = 1
            continue

        if submitted or already_submitted:
            return submitted, already_submitted, "submitted", entered_refund_page

    print("no refund prompt detected after click; mark as handled and continue")
    return submitted, already_submitted, "unknown", entered_refund_page


def notify_wechat_summary(
    records: list[RefundRecord],
    *,
    had_refundable_order: bool,
    account_name: str | None,
    enabled: bool,
) -> None:
    if not enabled:
        return
    message = build_wechat_message(
        records,
        had_refundable_order=had_refundable_order,
        account_name=account_name,
    )
    print(f"wechat summary:\n{message}")
    send_wechat_message(message)


def run_once(args: argparse.Namespace) -> int:
    adb = ADB(args.adb, dry_run=not args.execute)
    refund_records: list[RefundRecord] = []
    had_refundable_order = False
    send_wechat = args.execute
    account_name: str | None = None

    try:
        if not Path(args.adb).exists():
            print(f"adb not found: {args.adb}", file=sys.stderr)
            return 2

        if args.execute and not args.start_current:
            if not args.skip_unlock_check:
                ensure_unlocked(adb, args.unlock_script)
            account_name = launch_and_navigate(adb)
        elif args.execute and args.start_current:
            account_name = detect_account_name(adb.dump_nodes())
            if account_name:
                print(f"current account: {account_name}")

        if args.max_steps <= 0:
            print("max_steps <= 0: navigation finished; no refund scan performed")
            notify_wechat_summary(
                refund_records,
                had_refundable_order=had_refundable_order,
                account_name=account_name,
                enabled=send_wechat,
            )
            return 0

        handled: set[str] = set()
        submitted = 0
        already_submitted = 0

        for step in range(args.max_steps):
            nodes = adb.dump_nodes()
            rows = status_nodes(nodes)
            print(f"\nSTEP {step}")
            print_rows(rows)

            if any(node.text == "已退款" for node in rows):
                print(f"stop: 已看到已退款. submitted={submitted}, already_submitted={already_submitted}")
                notify_wechat_summary(
                    refund_records,
                    had_refundable_order=had_refundable_order,
                    account_name=account_name,
                    enabled=send_wechat,
                )
                return 0

            refund_nodes = [node for node in rows if node.text == "申请退款"]
            if refund_nodes:
                had_refundable_order = True
            actionable: tuple[str, UINode] | None = None
            for refund_node in refund_nodes:
                order_date = nearest_order_date(rows, refund_node)
                if order_date not in handled:
                    actionable = (order_date, refund_node)
                    break

            if actionable:
                order_date, refund_node = actionable
                print(f"handle refund button for {order_date}: {refund_node.bounds}")
                if args.execute:
                    amount = nearest_order_amount(nodes, refund_node)
                    newly_submitted, newly_already_submitted, result, entered_refund_page = process_refund_button(
                        adb, refund_node
                    )
                    handled.add(order_date)
                    submitted += newly_submitted
                    already_submitted += newly_already_submitted
                    if entered_refund_page:
                        refund_records.append(RefundRecord(order_date=order_date, amount=amount))
                        print(f"refund page entered: {order_date} {amount}")
                    elif result == "unknown":
                        print(
                            f"error: clicked 申请退款 for {order_date} but refund page was not detected",
                            file=sys.stderr,
                        )
                        return 1
                    continue
                print("dry-run: would click refund button here")
                return 0

            if not args.execute:
                print("dry-run: no visible refund button or refunded order on current screen")
                return 0

            adb.swipe(540, 1700, 540, 850, 650)

        print(f"error: reached max steps without seeing 已退款", file=sys.stderr)
        print(f"submitted={submitted}, already_submitted={already_submitted}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"fatal: {exc}", file=sys.stderr)
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automatically submit ChaKe VIP-card refund requests.")
    parser.add_argument("--adb", default=DEFAULT_ADB, help="Path to adb.")
    parser.add_argument("--execute", action="store_true", help="Actually tap/swipe and submit refunds.")
    parser.add_argument(
        "--unlock-script",
        default=DEFAULT_UNLOCK_SCRIPT,
        help="Script used when screen is locked/off.",
    )
    parser.add_argument("--skip-unlock-check", action="store_true", help="Do not check lock state before launch.")
    parser.add_argument(
        "--start-current",
        action="store_true",
        help="Do not launch/navigate; start scanning from the current phone screen.",
    )
    parser.add_argument("--max-steps", type=int, default=45, help="Maximum scroll/check iterations.")
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_once(parse_args()))
