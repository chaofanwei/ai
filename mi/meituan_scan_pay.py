#!/usr/bin/env python3
"""Automate Meituan QR-code payment from a favorite album image.

Default mode is dry-run. Use --execute to really tap on the phone.

Example:
    /Users/weichaofan/miniconda3/envs/py3.11/bin/python meituan_scan_pay.py 92 2 --execute
"""

from __future__ import annotations

import argparse
import random
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass


DEFAULT_ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"
PACKAGE = "com.sankuai.meituan"

# Coordinates are verified on a 1080x2340 device.
SCAN_ICON = (1000, 155)
CAMERA_ALBUM_ICON = (1000, 1820)
ALBUM_TAB = (306, 442)
FAVORITES_ROW = (431, 944)
FAVORITE_PHOTOS = {
    1: (135, 690),
    2: (405, 690),
    3: (675, 690),
}
CONFIRM_PAY = (932, 1985)
KEYPAD = {
    "1": (135, 1688),
    "2": (405, 1688),
    "3": (665, 1688),
    "4": (135, 1836),
    "5": (405, 1836),
    "6": (665, 1836),
    "7": (135, 1984),
    "8": (405, 1984),
    "9": (665, 1984),
    "0": (270, 2130),
    ".": (665, 2130),
}
KEY_COORDS = {
    "1": (180, 1635),
    "8": (540, 1987),
    "0": (540, 2172),
}


def tap_digit(code: str = "880188") -> None:
    for digit in code:
        x, y = KEY_COORDS[digit]
        subprocess.run(
            [DEFAULT_ADB, "shell", "input", "tap", str(x), str(y)],
            check=True,
        )
        time.sleep(random.uniform(0.5, 2))


@dataclass(frozen=True)
class UINode:
    text: str
    bounds: str


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

    def tap(self, x: int, y: int, delay: float = 0.8) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.shell(["input", "tap", str(x), str(y)], timeout=4)
            time.sleep(delay)

    def force_stop(self, package: str) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}force-stop {package}")
        if not self.dry_run:
            self.shell(["am", "force-stop", package], timeout=8)
            time.sleep(1.0)

    def launch(self, package: str) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}launch {package}")
        if not self.dry_run:
            self.shell(["monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"], timeout=8)
            time.sleep(2.0)

    def dump_nodes(self) -> list[UINode]:
        self.shell(["uiautomator", "dump", "/sdcard/window.xml"], timeout=8)
        proc = self.run(["exec-out", "cat", "/sdcard/window.xml"], timeout=8)
        root = ET.fromstring(proc.stdout)
        nodes: list[UINode] = []
        for node in root.iter("node"):
            text = node.attrib.get("text", "")
            desc = node.attrib.get("content-desc", "")
            value = text or desc
            if value:
                nodes.append(UINode(value, node.attrib.get("bounds", "")))
        return nodes


def ui_text(adb: ADB) -> str:
    return "\n".join(node.text for node in adb.dump_nodes())


def normalize_amount(raw: str) -> str:
    amount = raw.strip()
    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", amount):
        raise ValueError("amount must be a positive number with at most 2 decimal places, for example 92 or 92.50")
    amount = amount.lstrip("0") or "0"
    if amount.startswith("."):
        amount = "0" + amount
    if amount == "0" or amount.startswith("0."):
        raise ValueError("amount must be greater than 0")
    return amount


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
    last_texts = ""
    while time.monotonic() < deadline:
        try:
            joined = ui_text(adb)
        except Exception as exc:
            last_texts = str(exc)
            time.sleep(1.0)
            continue

        last_texts = joined[:500]
        any_ok = not any_markers or sum(1 for marker in any_markers if marker in joined) >= min_any
        all_ok = all(marker in joined for marker in all_markers)
        absent_ok = all(marker not in joined for marker in absent_markers)
        if any_ok and all_ok and absent_ok:
            print(f"{name} appears ready")
            return joined
        time.sleep(1.0)

    raise RuntimeError(f"{name} was not ready after {timeout}s. Last UI text: {last_texts!r}")


def wait_for_home(adb: ADB, timeout: int) -> None:
    wait_for_page(
        adb,
        "Meituan home page",
        any_markers=("搜索", "外卖", "团购", "酒店民宿", "推荐", "我的"),
        min_any=2,
        timeout=timeout,
    )


def input_amount(adb: ADB, amount: str) -> None:
    for char in amount:
        if char not in KEYPAD:
            raise ValueError(f"unsupported amount character: {char!r}")
        adb.tap(*KEYPAD[char], delay=0.25)


def run_flow(adb: ADB, amount: str, photo_index: int, home_timeout: int) -> None:
    adb.force_stop(PACKAGE)
    adb.launch(PACKAGE)
    wait_for_home(adb, home_timeout)

    adb.tap(*SCAN_ICON, delay=2.0)
    wait_for_page(
        adb,
        "camera scan page",
        any_markers=("扫一扫", "拍照购", "扫二维码", "扫二维码/条码/搜同款"),
        timeout=20,
    )

    adb.tap(*CAMERA_ALBUM_ICON, delay=1.2)
    wait_for_page(adb, "photo picker page", all_markers=("请选择1张照片",), timeout=20)

    adb.tap(*ALBUM_TAB, delay=0.8)
    wait_for_page(adb, "album list page", all_markers=("全部照片", "收藏"), timeout=15)

    adb.tap(*FAVORITES_ROW, delay=0.8)
    wait_for_page(
        adb,
        "favorites album page",
        any_markers=("今天", "请选择1张照片"),
        absent_markers=("全部照片",),
        timeout=15,
    )

    adb.tap(*FAVORITE_PHOTOS[photo_index], delay=1.0)
    wait_for_page(
        adb,
        "merchant payment page",
        all_markers=("确认", "支付", "备注"),
        timeout=30,
    )

    input_amount(adb, amount)
    adb.tap(*CONFIRM_PAY, delay=2.0)
    time.sleep(3)
    tap_digit()
    #result_text = wait_for_page(
    #    adb,
    #    "payment result or verification page",
    #    any_markers=("支付成功", "支付结果", "支付密码", "验证", "确认付款"),
    #    timeout=20,
    #)
    #if "支付成功" in result_text or "支付结果" in result_text:
    #    print("payment result page appears ready")
    #    return

    #print("payment verification is required; enter the payment password on the phone")
    wait_for_page(
        adb,
        "payment success page after manual verification",
        any_markers=("支付成功", "支付结果"),
        timeout=120,
    )
    print("payment success page appears ready")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pay in Meituan by scanning a QR image from Favorites.")
    parser.add_argument("amount", help="payment amount, for example 92 or 92.50")
    parser.add_argument("photo_index", type=int, choices=(1, 2, 3), help="which photo in Favorites to choose")
    parser.add_argument("--execute", action="store_true", help="really tap on the phone")
    parser.add_argument("--adb", default=DEFAULT_ADB, help=f"adb path, default: {DEFAULT_ADB}")
    parser.add_argument("--home-timeout", type=int, default=45, help="seconds to wait for the home page")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    amount = normalize_amount(args.amount)
    adb = ADB(args.adb, dry_run=not args.execute)
    run_flow(adb, amount, args.photo_index, args.home_timeout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
