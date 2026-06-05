#!/usr/bin/env python3
"""Automate UnionPay QR-code payment from a recent album image.

Default mode is dry-run. Use --execute to really tap on the phone.

Example:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python unionpay_scan_pay.py 89 2 --execute
"""

from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
PACKAGE = "com.unionpay"
REMOTE_XML = "/sdcard/window.xml"

# Coordinates are verified on a 1080x2340 device.
SCAN_ICON = (675, 330)
CAMERA_ALBUM_ICON = (925, 1900)
SECOND_ROW_PHOTOS = {
    1: (135, 630),
    2: (405, 630),
    3: (675, 630),
}
PHOTO_CONFIRM = (955, 180)
CONFIRM_PAY = (930, 1970)
BOTTOM_CONFIRM_PAY = (540, 2000)

KEYPAD = {
    "1": (135, 1665),
    "2": (405, 1665),
    "3": (665, 1665),
    "4": (135, 1815),
    "5": (405, 1815),
    "6": (665, 1815),
    "7": (135, 1970),
    "8": (405, 1970),
    "9": (665, 1970),
    "0": (270, 2130),
    ".": (665, 2130),
}

CODE_KEY_COORDS = {
    "1": (180, 1685),
    "8": (540, 1980),
    "0": (540, 2130),
}


@dataclass(frozen=True)
class UINode:
    text: str
    desc: str
    bounds: str

    @property
    def value(self) -> str:
        return self.text or self.desc


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

    def shell(self, args: list[str], timeout: int = 10, check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return self.run(["shell", *args], timeout=timeout, check=check)

    def launch(self) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}launch {PACKAGE}")
        if not self.dry_run:
            self.shell(["monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)

    def force_stop(self) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}force-stop {PACKAGE}")
        if not self.dry_run:
            self.shell(["am", "force-stop", PACKAGE], timeout=8)

    def tap(self, x: int, y: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)

    def dump_nodes(self) -> list[UINode]:
        self.shell(["uiautomator", "dump", REMOTE_XML], timeout=8, check=False)
        proc = self.run(["exec-out", "cat", REMOTE_XML], timeout=8)
        try:
            root = ET.fromstring(proc.stdout)
        except ET.ParseError:
            return []

        nodes: list[UINode] = []
        for node in root.iter("node"):
            nodes.append(
                UINode(
                    text=node.attrib.get("text", ""),
                    desc=node.attrib.get("content-desc", ""),
                    bounds=node.attrib.get("bounds", ""),
                )
            )
        return nodes


def ui_text(adb: ADB) -> str:
    return "\n".join(node.value for node in adb.dump_nodes() if node.value)


def ensure_adb_exists(adb_path: str) -> None:
    if not Path(adb_path).exists():
        raise RuntimeError(f"adb not found: {adb_path}")


def normalize_amount(raw: str) -> str:
    amount = raw.strip()
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", amount):
        raise ValueError("amount must be a positive number with at most 2 decimal places, for example 89 or 89.50")
    amount = amount.lstrip("0") or "0"
    if amount.startswith("."):
        amount = "0" + amount
    if amount == "0" or amount.startswith("0."):
        raise ValueError("amount must be greater than 0")
    return amount


def amount_success_text(amount: str) -> str:
    return f"¥{Decimal(amount):.2f}"


def wait_random_after_click(dry_run: bool) -> None:
    delay = random.uniform(2.0, 4.0)
    print(f"{'[dry-run] ' if dry_run else ''}sleep {delay:.2f}s")
    if not dry_run:
        time.sleep(delay)


def wait_for_page(
    adb: ADB,
    name: str,
    *,
    any_markers: tuple[str, ...] = (),
    all_markers: tuple[str, ...] = (),
    absent_markers: tuple[str, ...] = (),
    min_any: int = 1,
    timeout: int = 15,
) -> str:
    if adb.dry_run:
        parts = []
        if any_markers:
            parts.append(f"any={any_markers}")
        if all_markers:
            parts.append(f"all={all_markers}")
        if absent_markers:
            parts.append(f"absent={absent_markers}")
        print(f"[dry-run] wait for {name}: {', '.join(parts)}")
        return ""

    deadline = time.monotonic() + timeout
    last_text = ""
    while time.monotonic() < deadline:
        try:
            joined = ui_text(adb)
        except Exception as exc:
            last_text = str(exc)
            time.sleep(1.0)
            continue

        last_text = joined[:800]
        any_ok = not any_markers or sum(1 for marker in any_markers if marker in joined) >= min_any
        all_ok = all(marker in joined for marker in all_markers)
        absent_ok = all(marker not in joined for marker in absent_markers)
        if any_ok and all_ok and absent_ok:
            print(f"{name} appears ready")
            return joined
        time.sleep(1.0)

    raise TimeoutError(f"{name} failed: not ready after {timeout}s. Last UI text: {last_text!r}")


def tap_and_wait(
    adb: ADB,
    x: int,
    y: int,
    next_page_name: str,
    *,
    any_markers: tuple[str, ...] = (),
    all_markers: tuple[str, ...] = (),
    absent_markers: tuple[str, ...] = (),
    min_any: int = 1,
) -> str:
    adb.tap(x, y)
    wait_random_after_click(adb.dry_run)
    return wait_for_page(
        adb,
        next_page_name,
        any_markers=any_markers,
        all_markers=all_markers,
        absent_markers=absent_markers,
        min_any=min_any,
        timeout=15,
    )


def input_amount(adb: ADB, amount: str) -> None:
    for char in amount:
        if char not in KEYPAD:
            raise ValueError(f"unsupported amount character: {char!r}")
        adb.tap(*KEYPAD[char])
        wait_random_after_click(adb.dry_run)


def tap_digit() -> None:
    code = "880188"
    min_delay = 0.5
    max_delay = 2.0

    for digit in code:
        x, y = CODE_KEY_COORDS[digit]
        subprocess.run(
            [DEFAULT_ADB, "shell", "input", "tap", str(x), str(y)],
            check=True,
        )
        time.sleep(random.uniform(min_delay, max_delay))


def run_flow(adb: ADB, amount: str, photo_index: int) -> None:
    adb.force_stop()
    wait_random_after_click(adb.dry_run)
    adb.launch()
    wait_random_after_click(adb.dry_run)
    wait_for_page(
        adb,
        "UnionPay home page",
        any_markers=("首页", "扫一扫", "收付款", "转账", "卡管理", "我的"),
        min_any=2,
        timeout=15,
    )

    tap_and_wait(
        adb,
        *SCAN_ICON,
        "scan camera page",
        any_markers=("扫二维码", "条码", "付款码", "相册", "UnionPay"),
        min_any=1,
    )

    tap_and_wait(
        adb,
        *CAMERA_ALBUM_ICON,
        "album page",
        any_markers=("最近项目", "系统相册", "照片", "图库"),
        min_any=1,
    )

    tap_and_wait(
        adb,
        *SECOND_ROW_PHOTOS[photo_index],
        "photo confirmation page",
        any_markers=("确定",),
        absent_markers=("最近项目", "系统相册"),
    )

    tap_and_wait(
        adb,
        *PHOTO_CONFIRM,
        "merchant payment page",
        any_markers=("向商家付款", "付款给商家"),
        all_markers=("添加备注",),
    )

    input_amount(adb, amount)
    payment_text = tap_and_wait(
        adb,
        *CONFIRM_PAY,
        "payment verification page",
        any_markers=("支付密码", "请输入支付密码", "确认付款", "付款详情", "确认支付", "云闪付支付"),
        min_any=1,
    )
    if "确认支付" in payment_text and ("云闪付支付" in payment_text or "付款详情" in payment_text):
        tap_and_wait(
            adb,
            *BOTTOM_CONFIRM_PAY,
            "payment password page",
            any_markers=("支付密码", "请输入支付密码", "确认付款", "付款详情", "支付"),
            min_any=1,
        )
    print("Wait your code")
    time.sleep(random.uniform(3, 5))
    tap_digit()
    wait_for_page(
        adb,
        "payment success page",
        any_markers=("支付成功",),
        all_markers=(amount_success_text(amount),),
        timeout=60,
    )
    print("Payment success page appears ready.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open UnionPay, select a QR-code image, enter amount, and confirm pay.")
    parser.add_argument("amount", help="Payment amount, for example 89 or 89.50.")
    parser.add_argument("photo_index", type=int, choices=(1, 2, 3), help="Photo index in the second album row.")
    parser.add_argument("--adb", default=DEFAULT_ADB, help=f"adb path. Defaults to {DEFAULT_ADB}")
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone. Without this, only prints actions.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        ensure_adb_exists(args.adb)
        amount = normalize_amount(args.amount)
        adb = ADB(args.adb, dry_run=not args.execute)
        run_flow(adb, amount, args.photo_index)
        return 0
    except Exception as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
