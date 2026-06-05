#!/usr/bin/env python3
import argparse
import random
import subprocess
import time


ADB = "/Users/weichaofan/Library/Android/sdk/platform-tools/adb"

# Coordinates measured from the current 1080x2340 screenshot.
KEY_COORDS = {
    "1": (180, 1685),
    "8": (540, 1980),
    "0": (540, 2130),
}


def tap_digit(digit: str, min_delay: float, max_delay: float) -> None:
    x, y = KEY_COORDS[digit]
    subprocess.run(
        [ADB, "shell", "input", "tap", str(x), str(y)],
        check=True,
    )
    time.sleep(random.uniform(min_delay, max_delay))


def main() -> None:
    parser = argparse.ArgumentParser(description="Tap 880188 on the current phone keypad.")
    parser.add_argument("--code", default="880188", help="Digits to tap. Defaults to 880188.")
    parser.add_argument("--min-delay", type=float, default=0.5, help="Minimum delay after each tap.")
    parser.add_argument("--max-delay", type=float, default=2.0, help="Maximum delay after each tap.")
    args = parser.parse_args()

    if args.min_delay < 0 or args.max_delay < args.min_delay:
        raise SystemExit("--max-delay must be greater than or equal to --min-delay, and delays must be non-negative")

    unsupported = sorted(set(args.code) - set(KEY_COORDS))
    if unsupported:
        raise SystemExit(f"Unsupported digits for this keypad script: {', '.join(unsupported)}")

    for digit in args.code:
        tap_digit(digit, args.min_delay, args.max_delay)


if __name__ == "__main__":
    main()
