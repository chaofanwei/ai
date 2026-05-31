#!/usr/bin/env python3
"""Switch between the two configured ChaKe app accounts via uiautomator2.

Detects the current account from the greeting on 我的 (您好，<name>),
logs out, then logs into the other account.

Default mode is dry-run. Use --execute to operate the phone.

Examples:
  python chake-switch-account.py --execute
  python chake-switch-account.py --execute --relaunch
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_UNLOCK_SCRIPT = str(SCRIPT_DIR / "unlock.sh")
PACKAGE = "com.slwy.shanglvwuyou"
PASSWORD = "Claw8801"

MY_TAB_FALLBACK = (898, 2098)
BOTTOM_TAB_MIN_Y = 2000
MAX_BACK_TO_MAIN = 3
GREETING_RE = re.compile(r"您好[，,]?\s*(\S+)")
FIELD_PLACEHOLDERS = {
    "输入手机号码/邮箱",
    "输入密码",
    "输入短信验证码",
    "输入图片验证码",
}


@dataclass(frozen=True)
class Account:
    name: str
    phone: str


ACCOUNTS: dict[str, Account] = {
    "魏超凡": Account("魏超凡", "13716268801"),
    "常会洁": Account("常会洁", "13716268679"),
}


@dataclass(frozen=True)
class UINode:
    text: str
    content_desc: str
    resource_id: str
    bounds: str
    clickable: bool
    checkable: bool
    checked: bool

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

    def matches(self, label: str) -> bool:
        return self.text == label or self.content_desc == label

    def contains(self, pattern: str) -> bool:
        return pattern in self.text or pattern in self.content_desc or pattern in self.resource_id


def parse_nodes_xml(xml_bytes: bytes | str) -> list[UINode]:
    if isinstance(xml_bytes, str):
        xml_bytes = xml_bytes.encode("utf-8")
    root = ET.fromstring(xml_bytes)
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
                checkable=node.attrib.get("checkable", "false") == "true",
                checked=node.attrib.get("checked", "false") == "true",
            )
        )
    return nodes


class Phone:
    """Thin wrapper around uiautomator2 for all UI automation."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run
        self._device: object | None = None

    @property
    def d(self) -> object:
        if self._device is None:
            import uiautomator2 as u2

            self._device = u2.connect()
        return self._device

    def shell(self, cmd: str, timeout: int = 10) -> str:
        print(f"{'[dry-run] ' if self.dry_run else ''}shell {cmd}")
        if self.dry_run:
            return ""
        output = self.d.shell(cmd, timeout=timeout)  # type: ignore[attr-defined]
        if isinstance(output, bytes):
            return output.decode("utf-8", "replace")
        return str(output)

    def tap(self, x: int, y: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}tap {x} {y}")
        if not self.dry_run:
            self.d.click(x, y)  # type: ignore[attr-defined]
            time.sleep(0.8)

    def tap_node(self, node: UINode) -> None:
        x, y = node.center
        self.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}swipe {x1} {y1} {x2} {y2} {duration_ms}")
        if not self.dry_run:
            self.d.swipe(x1, y1, x2, y2, duration_ms / 1000)  # type: ignore[attr-defined]
            time.sleep(0.8)

    def keyevent(self, key: str, *, pause_s: float = 0.1) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}keyevent {key}")
        if not self.dry_run:
            self.shell(f"input keyevent {key}", timeout=4)
            time.sleep(pause_s)

    def set_field_text(self, resource_suffix: str, text: str) -> None:
        resource_id = f"{PACKAGE}:id/{resource_suffix}"
        print(f"{'[dry-run] ' if self.dry_run else ''}set field {resource_suffix}")
        if self.dry_run:
            return
        elem = self.d(resourceId=resource_id)  # type: ignore[attr-defined]
        elem.click()
        elem.set_text(text)
        time.sleep(0.3)

    def clear_field(self, node: UINode) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}clear field {node.resource_id or node.text}")
        if self.dry_run:
            return
        if node.resource_id:
            elem = self.d(resourceId=node.resource_id)  # type: ignore[attr-defined]
            elem.click()
            elem.clear_text()
            time.sleep(0.2)
            return
        self.tap_node(node)
        self.shell("input keyevent KEYCODE_MOVE_END")
        for _ in range(8):
            self.shell("input keyevent KEYCODE_DEL")
        time.sleep(0.2)

    def set_clipboard(self, text: str) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}set clipboard")
        if not self.dry_run:
            self.d.set_clipboard(text)  # type: ignore[attr-defined]

    def dump_nodes(self) -> list[UINode]:
        if self.dry_run:
            return []
        last_error: Exception | None = None
        for _ in range(3):
            try:
                xml = self.d.dump_hierarchy()  # type: ignore[attr-defined]
                return parse_nodes_xml(xml)
            except Exception as exc:
                last_error = exc
                time.sleep(0.6)
        raise RuntimeError(f"failed to dump ui hierarchy: {last_error}")

    def stop_app(self) -> None:
        print("force-stop app")
        if not self.dry_run:
            self.d.app_stop(PACKAGE)  # type: ignore[attr-defined]
            time.sleep(0.8)

    def start_app(self) -> None:
        print("launch app")
        if not self.dry_run:
            self.d.app_start(PACKAGE, stop=False)  # type: ignore[attr-defined]
            time.sleep(1.5)

    def relaunch_app(self) -> None:
        self.stop_app()
        self.start_app()

    def press_back(self) -> None:
        print(f"{'[dry-run] ' if self.dry_run else ''}press back")
        if not self.dry_run:
            self.d.press("back")  # type: ignore[attr-defined]
            time.sleep(0.8)

    def foreground_package(self) -> str | None:
        if self.dry_run:
            return None
        info = self.d.app_current()  # type: ignore[attr-defined]
        if isinstance(info, dict):
            package = info.get("package")
            return str(package) if package else None
        return None


def device_needs_unlock(phone: Phone) -> bool:
    window_text = phone.shell("dumpsys window", timeout=10)
    power_text = phone.shell("dumpsys power", timeout=10)

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


def ensure_unlocked(phone: Phone, unlock_script: str) -> None:
    if phone.dry_run:
        print("[dry-run] would check lock state")
        return
    if not device_needs_unlock(phone):
        print("screen appears unlocked")
        return

    script = resolve_unlock_script(unlock_script)
    print(f"screen is locked/off; running {script}")
    subprocess.run([str(script)], check=True, timeout=30, cwd=str(SCRIPT_DIR))
    time.sleep(1)


def find_visible(nodes: list[UINode], label: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.matches(label)]


def has_text(nodes: list[UINode], pattern: str) -> bool:
    return any(node.contains(pattern) for node in nodes)


def find_visible_contains(nodes: list[UINode], pattern: str) -> list[UINode]:
    return [node for node in nodes if node.visible and node.contains(pattern)]


def find_by_resource(nodes: list[UINode], resource_suffix: str) -> list[UINode]:
    return [
        node
        for node in nodes
        if node.visible and node.resource_id.endswith(f":id/{resource_suffix}")
    ]


def wait_for_any_text(phone: Phone, candidates: list[str], timeout_s: int) -> list[UINode]:
    deadline = time.time() + timeout_s
    last_nodes: list[UINode] = []
    while time.time() < deadline:
        try:
            last_nodes = phone.dump_nodes()
        except Exception:
            time.sleep(0.5)
            continue
        if any(has_text(last_nodes, candidate) for candidate in candidates):
            return last_nodes
        time.sleep(0.5)
    return last_nodes


def tap_label(phone: Phone, nodes: list[UINode], label: str) -> bool:
    matches = find_visible(nodes, label)
    if not matches:
        return False
    preferred = next((node for node in matches if node.clickable), matches[0])
    phone.tap_node(preferred)
    return True


def bottom_tab_my_visible(nodes: list[UINode]) -> bool:
    for node in find_visible(nodes, "我的"):
        if node.center[1] >= BOTTOM_TAB_MIN_Y:
            return True
    return False


def on_my_page(nodes: list[UINode]) -> bool:
    return has_text(nodes, "我的订单") or has_text(nodes, "账号安全")


def detect_current_account(nodes: list[UINode]) -> Account:
    for node in nodes:
        if not node.visible:
            continue
        match = GREETING_RE.search(node.text)
        if not match:
            continue
        name = match.group(1).strip()
        account = ACCOUNTS.get(name)
        if account is not None:
            return account
        known = ", ".join(ACCOUNTS)
        raise RuntimeError(f"unknown account name on 我的 page: {name!r} (known: {known})")

    if has_text(nodes, "差客e族登录"):
        raise RuntimeError("not logged in; open 我的 page requires an active session")
    raise RuntimeError("could not find greeting on 我的 page (expected 您好，<name>)")


def other_account(current: Account) -> Account:
    for account in ACCOUNTS.values():
        if account.name != current.name:
            return account
    raise RuntimeError("no alternate account configured")


def ensure_main_tab_bar(phone: Phone) -> None:
    if phone.dry_run:
        print("[dry-run] would ensure bottom tab 我的 is visible")
        return

    for attempt in range(MAX_BACK_TO_MAIN + 1):
        nodes = phone.dump_nodes()
        if bottom_tab_my_visible(nodes):
            print("bottom tab 我的 visible")
            return
        if attempt >= MAX_BACK_TO_MAIN:
            break
        print(f"bottom tab 我的 not visible; back attempt {attempt + 1}/{MAX_BACK_TO_MAIN}")
        phone.press_back()

    nodes = phone.dump_nodes()
    if bottom_tab_my_visible(nodes):
        print("bottom tab 我的 visible")
        return

    print("bottom tab 我的 still not visible after back; relaunch chake")
    phone.relaunch_app()
    wait_for_any_text(
        phone,
        ["首页", "我的行程", "出差申请", "差客e族登录"],
        timeout_s=20,
    )
    nodes = phone.dump_nodes()
    if bottom_tab_my_visible(nodes):
        print("bottom tab 我的 visible after relaunch")
        return

    raise RuntimeError("could not reach main tab bar with 我的 after relaunch")


def prepare_chake_app(phone: Phone, *, force_relaunch: bool) -> None:
    if force_relaunch:
        print("force relaunch chake")
        phone.relaunch_app()
        if not phone.dry_run:
            wait_for_any_text(
                phone,
                ["首页", "我的行程", "出差申请", "差客e族登录"],
                timeout_s=20,
            )
        return

    if phone.dry_run:
        print("[dry-run] would prepare chake app")
        return

    current = phone.foreground_package()
    if current != PACKAGE:
        print(f"foreground app is {current or 'unknown'}; launch chake")
        phone.start_app()
        wait_for_any_text(
            phone,
            ["首页", "我的行程", "出差申请", "差客e族登录"],
            timeout_s=20,
        )
    else:
        print("chake already in foreground")

    ensure_main_tab_bar(phone)


def open_my_page(phone: Phone) -> None:
    print("open 我的")
    nodes = phone.dump_nodes()
    if on_my_page(nodes):
        print("already on 我的 page")
        return
    if not tap_label(phone, nodes, "我的"):
        x, y = MY_TAB_FALLBACK
        phone.tap(x, y)
    nodes = wait_for_any_text(phone, ["我的订单", "个人信息", "账号安全", "您好"], timeout_s=10)
    if not on_my_page(nodes) and not any(GREETING_RE.search(node.text) for node in nodes if node.visible):
        print("warning: 我的 page markers not detected")


def open_account_security(phone: Phone) -> None:
    print("open 账号安全")
    if phone.dry_run:
        print("[dry-run] would open 账号安全")
        return

    for attempt in range(4):
        nodes = phone.dump_nodes()
        if tap_label(phone, nodes, "账号安全"):
            break
        print(f"账号安全 not visible on attempt {attempt + 1}; scrolling")
        phone.swipe(540, 1700, 540, 900, 650)
    else:
        raise RuntimeError("could not find 账号安全 on 我的 page")

    nodes = wait_for_any_text(phone, ["修改登录密码", "退出登录"], timeout_s=10)
    if not has_text(nodes, "退出登录") and not has_text(nodes, "修改登录密码"):
        raise RuntimeError("account security page not detected")


def tap_logout_button(phone: Phone) -> None:
    print("tap 退出登录")
    if phone.dry_run:
        print("[dry-run] would tap 退出登录")
        return

    for attempt in range(4):
        nodes = phone.dump_nodes()
        if tap_label(phone, nodes, "退出登录"):
            return
        print(f"退出登录 not visible on attempt {attempt + 1}; scrolling")
        phone.swipe(540, 1700, 540, 900, 650)

    raise RuntimeError("could not find 退出登录 on account security page")


def confirm_logout_if_needed(phone: Phone) -> None:
    if phone.dry_run:
        print("[dry-run] would confirm logout if dialog appears")
        return

    for _ in range(8):
        time.sleep(0.4)
        nodes = phone.dump_nodes()
        if has_text(nodes, "差客e族登录"):
            print("already on login page")
            return
        if has_text(nodes, "确定退出登录"):
            print("confirm logout dialog detected")
            if tap_label(phone, nodes, "确定"):
                return
            raise RuntimeError("could not tap 确定 on logout confirmation dialog")
        if not has_text(nodes, "退出登录"):
            return

    print("warning: logout confirmation dialog not detected; checking login page")


def verify_logged_out(phone: Phone) -> None:
    if phone.dry_run:
        print("[dry-run] would verify login page after logout")
        return

    nodes = wait_for_any_text(
        phone,
        ["差客e族登录", "输入手机号码/邮箱", "输入密码"],
        timeout_s=12,
    )
    if not has_text(nodes, "差客e族登录"):
        raise RuntimeError("logout may have failed: login page not detected")


def ensure_login_page(phone: Phone) -> list[UINode]:
    nodes = wait_for_any_text(
        phone,
        ["差客e族登录", "输入手机号码/邮箱", "输入密码"],
        timeout_s=12,
    )
    if not has_text(nodes, "差客e族登录"):
        raise RuntimeError("login page not detected")
    return nodes


def dismiss_blocking_dialogs(phone: Phone) -> None:
    if phone.dry_run:
        return
    for _ in range(4):
        nodes = phone.dump_nodes()
        if tap_label(phone, nodes, "确定"):
            time.sleep(0.5)
            continue
        if tap_label(phone, nodes, "知道了"):
            time.sleep(0.5)
            continue
        return


def ensure_password_login_mode(phone: Phone, nodes: list[UINode]) -> list[UINode]:
    if has_text(nodes, "输入密码"):
        return nodes

    print("switch to 账号密码登录")
    toggle_nodes = find_visible(nodes, "账号密码登录")
    if not toggle_nodes:
        toggle_nodes = find_visible_contains(nodes, "账号密码登录")
    if toggle_nodes:
        phone.tap_node(toggle_nodes[0])
        nodes = wait_for_any_text(phone, ["输入密码", "差客e族登录"], timeout_s=8)
        if has_text(nodes, "输入密码"):
            return nodes

    if phone.dry_run:
        print("[dry-run] would switch to password login mode")
        return nodes

    raise RuntimeError("could not switch to password login mode")


def field_has_content(node: UINode) -> bool:
    return bool(node.text) and node.text not in FIELD_PLACEHOLDERS


def fill_field_paste(phone: Phone, node: UINode, text: str) -> None:
    if phone.dry_run:
        print(f"[dry-run] would paste into field: {text}")
        return
    if node.resource_id:
        elem = phone.d(resourceId=node.resource_id)  # type: ignore[attr-defined]
        elem.click()
        if field_has_content(node):
            elem.clear_text()
    else:
        phone.tap_node(node)
        if field_has_content(node):
            phone.clear_field(node)
    phone.set_clipboard(text)
    phone.keyevent("KEYCODE_PASTE")
    phone.tap(540, 300)
    time.sleep(0.2)


def agree_privacy_policy(phone: Phone, nodes: list[UINode]) -> None:
    print("agree privacy policy")
    checkbox_nodes = find_by_resource(nodes, "login_checkbox")
    if checkbox_nodes and checkbox_nodes[0].checked:
        print("privacy checkbox already checked")
        return

    if checkbox_nodes:
        phone.tap_node(checkbox_nodes[0])
        return

    privacy_nodes = find_visible_contains(nodes, "隐私政策")
    if privacy_nodes:
        phone.tap_node(privacy_nodes[0])
        return

    if phone.dry_run:
        print("[dry-run] would tap privacy policy checkbox")
        return

    raise RuntimeError("could not find privacy policy checkbox")


def perform_login(phone: Phone, account: Account) -> None:
    print(f"login as {account.name} ({account.phone})")
    dismiss_blocking_dialogs(phone)
    nodes = ensure_login_page(phone)
    nodes = ensure_password_login_mode(phone, nodes)

    account_nodes = find_by_resource(nodes, "cedt_account")
    if not account_nodes:
        account_nodes = find_visible(nodes, "输入手机号码/邮箱")
    if not account_nodes:
        raise RuntimeError("could not find account input field")
    print("fill phone into account field")
    phone.set_field_text("cedt_account", account.phone)

    nodes = phone.dump_nodes()
    password_nodes = find_by_resource(nodes, "cedt_pwd")
    if not password_nodes:
        password_nodes = find_visible(nodes, "输入密码")
    if not password_nodes:
        raise RuntimeError("could not find password input field")
    print("paste password into password field")
    fill_field_paste(phone, password_nodes[0], PASSWORD)

    nodes = phone.dump_nodes()
    agree_privacy_policy(phone, nodes)

    print("tap 登录")
    nodes = phone.dump_nodes()
    login_nodes = find_by_resource(nodes, "tv_login")
    if not login_nodes:
        login_nodes = find_visible(nodes, "登录")
    if not login_nodes:
        raise RuntimeError("could not find 登录 button")
    phone.tap_node(login_nodes[0])

    time.sleep(2)
    dismiss_blocking_dialogs(phone)
    nodes = phone.dump_nodes()
    if has_text(nodes, "账户或密码错误"):
        raise RuntimeError("login failed: 账户或密码错误")
    if has_text(nodes, "输入图片验证码"):
        raise RuntimeError("login blocked by image captcha; retry later or log in manually once")


def verify_logged_in(phone: Phone) -> None:
    if phone.dry_run:
        print("[dry-run] would verify home page after login")
        return

    nodes = wait_for_any_text(phone, ["首页", "我的行程", "出差申请", "我的订单"], timeout_s=20)
    if not any(has_text(nodes, marker) for marker in ("首页", "我的行程", "出差申请", "我的订单")):
        raise RuntimeError("login may have failed: home page not detected")


def verify_switched_account(phone: Phone, expected: Account) -> None:
    if phone.dry_run:
        print(f"[dry-run] would verify switched account is {expected.name}")
        return

    open_my_page(phone)
    nodes = phone.dump_nodes()
    actual = detect_current_account(nodes)
    if actual.name != expected.name:
        raise RuntimeError(f"switch verification failed: expected {expected.name}, saw {actual.name}")
    print(f"verified: now logged in as {actual.name}")


def run_switch_account(phone: Phone, *, force_relaunch: bool) -> None:
    prepare_chake_app(phone, force_relaunch=force_relaunch)
    open_my_page(phone)

    if phone.dry_run:
        print("[dry-run] would detect current account, logout, login the other account")
        return

    nodes = phone.dump_nodes()
    current = detect_current_account(nodes)
    target = other_account(current)
    print(f"current account: {current.name} ({current.phone})")
    print(f"target account:  {target.name} ({target.phone})")

    open_account_security(phone)
    tap_logout_button(phone)
    confirm_logout_if_needed(phone)
    verify_logged_out(phone)

    perform_login(phone, target)
    verify_logged_in(phone)
    verify_switched_account(phone, target)


def run_switch(args: argparse.Namespace) -> int:
    phone = Phone(dry_run=not args.execute)

    try:
        if args.execute and not args.skip_unlock_check:
            ensure_unlocked(phone, args.unlock_script)

        run_switch_account(phone, force_relaunch=args.relaunch)
        if args.execute:
            print("done: account switch finished")
        else:
            print("done: dry-run finished")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Switch ChaKe app between 魏超凡 and 常会洁.",
    )
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone.")
    parser.add_argument(
        "--unlock-script",
        default=DEFAULT_UNLOCK_SCRIPT,
        help="Script used when screen is locked/off.",
    )
    parser.add_argument("--skip-unlock-check", action="store_true", help="Do not check lock state.")
    parser.add_argument(
        "--relaunch",
        action="store_true",
        help="Force-stop and restart ChaKe before switching.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_switch(parse_args()))
