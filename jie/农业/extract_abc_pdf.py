#!/usr/bin/env python3
"""从中国农业银行账户活期交易明细 PDF 中提取表格内容为 CSV。"""

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

COLUMNS = [
    "交易日期", "交易时间", "交易摘要", "交易金额", "本次余额",
    "对手信息", "日志号", "交易渠道", "交易附言",
]

DATE_RE = re.compile(r"^\d{8}\s")
AMOUNT_RE = re.compile(r"^[+-][\d,]+\.\d{2}$")
BALANCE_RE = re.compile(r"^[\d,]+\.\d{2}$")
SKIP_RE = re.compile(
    r"^(户名|币种|起止日期|交易日期|该交易|中国农业银行|第\d+页|电子流水号)"
)
KNOWN_CHANNELS = {"超级网银", "电子商务", "柜面", "ATM", "手机银行"}


def extract_raw_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-raw", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def format_date(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"


def format_time(t: str) -> str:
    if not t:
        return ""
    return f"{t[:2]}:{t[2:4]}:{t[4:6]}"


def parse_rest(rest: list[str]) -> tuple[str, str, str, str]:
    if not rest:
        return "", "", "", ""

    log_idx = None
    for i in range(len(rest) - 1, -1, -1):
        if re.match(r"^\d+$", rest[i]):
            log_idx = i
            break

    if log_idx is None:
        return " ".join(rest), "", "", ""

    counterparty = " ".join(rest[:log_idx]) if log_idx > 0 else ""
    log_id = rest[log_idx]
    after = rest[log_idx + 1 :]

    if not after:
        return counterparty, log_id, "", ""
    if len(after) == 1:
        if after[0] in KNOWN_CHANNELS:
            return counterparty, log_id, after[0], ""
        return counterparty, log_id, "", after[0]

    channel = after[0] if after[0] in KNOWN_CHANNELS else ""
    if channel:
        remark = " ".join(after[1:])
    else:
        channel = ""
        remark = " ".join(after)
    return counterparty, log_id, channel, remark


def parse_record_text(text: str) -> dict | None:
    tokens = text.split()
    if len(tokens) < 5 or not re.match(r"^\d{8}$", tokens[0]):
        return None

    date = tokens[0]
    idx = 1
    time = ""
    if idx < len(tokens) and re.match(r"^\d{6}$", tokens[idx]):
        time = tokens[idx]
        idx += 1

    amount_idx = None
    for i in range(idx, len(tokens)):
        if AMOUNT_RE.match(tokens[i]):
            amount_idx = i
            break
    if amount_idx is None or amount_idx + 1 >= len(tokens):
        return None
    if not BALANCE_RE.match(tokens[amount_idx + 1]):
        return None

    summary = " ".join(tokens[idx:amount_idx])
    amount = tokens[amount_idx]
    balance = tokens[amount_idx + 1]
    counterparty, log_id, channel, remark = parse_rest(tokens[amount_idx + 2 :])

    return {
        "交易日期": format_date(date),
        "交易时间": format_time(time),
        "交易摘要": summary,
        "交易金额": amount,
        "本次余额": balance,
        "对手信息": counterparty or "--",
        "日志号": log_id,
        "交易渠道": channel,
        "交易附言": remark,
    }


def parse_records(text: str) -> list[dict]:
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    records = []
    buffer: list[str] = []

    def flush_buffer() -> None:
        nonlocal buffer
        if not buffer:
            return
        parsed = parse_record_text(" ".join(buffer))
        if parsed:
            records.append(parsed)
        buffer = []

    for line in lines:
        if SKIP_RE.match(line):
            continue
        if DATE_RE.match(line):
            flush_buffer()
            buffer = [line]
        elif buffer:
            buffer.append(line)

    flush_buffer()
    return records


def write_csv(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="提取农业银行 PDF 明细表格")
    parser.add_argument("pdf", type=Path, help="PDF 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出 CSV 路径")
    args = parser.parse_args()

    if not args.pdf.exists():
        sys.exit(f"文件不存在: {args.pdf}")

    text = extract_raw_text(args.pdf)
    records = parse_records(text)
    if not records:
        sys.exit("未能解析到任何交易记录，请检查 PDF 格式")

    out_csv = args.output or args.pdf.with_suffix(".csv")
    write_csv(records, out_csv)
    print(f"已提取 {len(records)} 条记录 -> {out_csv}")


if __name__ == "__main__":
    main()
