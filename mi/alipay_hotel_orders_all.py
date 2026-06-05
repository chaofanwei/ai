#!/Users/weichaofan/miniconda3/envs/py3.11/bin/python
"""Run Alipay hotel-order extraction for accounts 01, 02, and 79.

The current account is processed first. The script then switches to the other
configured accounts and processes each one. It always attempts to leave Alipay
on account 02 before exiting.
"""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PYTHON = "/Users/weichaofan/miniconda3/envs/py3.11/bin/python"
SWITCH_SCRIPT = SCRIPT_DIR / "alipay-switch-account.py"
HOTEL_SCRIPT = SCRIPT_DIR / "alipay_hotel_orders.py"
ACCOUNT_LABELS = ("01", "02", "79")
FINAL_ACCOUNT = "02"


def load_switch_module() -> object:
    spec = importlib.util.spec_from_file_location("alipay_switch_account", SWITCH_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {SWITCH_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def detect_current_account(args: argparse.Namespace) -> str:
    switch = load_switch_module()
    switch.ensure_adb_exists(args.adb)
    adb = switch.ADB(args.adb, dry_run=not args.execute)

    if args.execute and not args.skip_unlock_check:
        switch.ensure_unlocked(adb, args.unlock_script)

    switch.launch_alipay(adb, force_relaunch=args.execute or args.relaunch)
    switch.open_my_page(adb)
    current = switch.detect_account_from_my_page(adb)
    if current not in ACCOUNT_LABELS:
        raise RuntimeError(f"unsupported current Alipay account: {current!r}")
    return current


def run_command(title: str, command: list[str]) -> None:
    print("")
    print(f"========== {title} ==========")
    subprocess.run(command, cwd=str(SCRIPT_DIR), check=True)


def switch_to_account(account: str, args: argparse.Namespace) -> None:
    command = [PYTHON, str(SWITCH_SCRIPT), "--target", account, "--adb", args.adb, "--unlock-script", args.unlock_script]
    if args.execute:
        command.append("--execute")
    if args.skip_unlock_check:
        command.append("--skip-unlock-check")
    if args.relaunch:
        command.append("--relaunch")
    run_command(f"切换到支付宝账号 {account}", command)


def run_hotel_orders(account: str, args: argparse.Namespace) -> None:
    command = [PYTHON, str(HOTEL_SCRIPT), "--adb", args.adb]
    if args.execute:
        command.append("--execute")
    run_command(f"支付宝账号 {account}: 酒店订单", command)


def ordered_accounts(current: str) -> list[str]:
    return [current, *[account for account in ACCOUNT_LABELS if account != current]]


def run(args: argparse.Namespace) -> int:
    if not args.execute:
        raise RuntimeError("dry-run cannot detect the current account reliably; rerun with --execute")

    current = detect_current_account(args)
    accounts = ordered_accounts(current)
    print(f"current account: {current}")
    print(f"run order: {' -> '.join(accounts)}")

    failed = False
    try:
        for index, account in enumerate(accounts):
            if index > 0:
                switch_to_account(account, args)
            run_hotel_orders(account, args)
    except Exception:
        failed = True
        raise
    finally:
        try:
            switch_to_account(FINAL_ACCOUNT, args)
        except Exception as exc:
            failed = True
            print(f"error: failed to switch back to account {FINAL_ACCOUNT}: {exc}", file=sys.stderr)
        if failed:
            print(f"final account switch attempted: {FINAL_ACCOUNT}")

    print("done: processed Alipay hotel orders for 01, 02, and 79")
    return 0


def parse_args() -> argparse.Namespace:
    switch = load_switch_module()
    parser = argparse.ArgumentParser(description="Run Alipay hotel-order extraction for accounts 01, 02, and 79.")
    parser.add_argument("--adb", default=switch.DEFAULT_ADB, help="Path to adb.")
    parser.add_argument("--execute", action="store_true", help="Actually operate the phone.")
    parser.add_argument("--relaunch", action="store_true", help="Force-relaunch Alipay when detecting/switching accounts.")
    parser.add_argument("--skip-unlock-check", action="store_true", help="Skip screen lock detection and unlock.sh.")
    parser.add_argument("--unlock-script", default=switch.DEFAULT_UNLOCK_SCRIPT, help="Path to unlock.sh.")
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
