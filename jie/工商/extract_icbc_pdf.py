#!/usr/bin/env python3
"""从工商银行借记账户明细 PDF 中提取表格内容为文本/CSV。"""

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

COLUMNS = [
    "交易日期", "交易时间", "账号", "储种", "序号", "币种", "钞汇",
    "摘要", "地区", "收入/支出金额", "余额", "对方户名", "对方账号", "渠道",
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
AMOUNT_RE = re.compile(r"^[+-][\d,]+\.\d{2}$")
BALANCE_RE = re.compile(r"^[\d,]+\.\d{2}$")
ACCOUNT_RE = re.compile(r"^\d{19}$")
SKIP_RE = re.compile(
    r"^(请扫描|识别明细|中国工商银行|卡号|户名|起止日期|交易日期|本页|共\s+\d+\s+页|"
    r"第\s+\d+\s+页|下单时间|\d{8}\s+\d{4}-\d{2}-\d{2})"
)


def extract_raw_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-raw", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_data_tokens(text: str) -> dict | None:
    tokens = text.split()
    if len(tokens) < 12:
        return None
    if not ACCOUNT_RE.match(tokens[0]):
        return None

    channel = tokens[-1]
    counter_account = tokens[-2]

    balance_idx = None
    for i in range(len(tokens) - 3, 4, -1):
        if BALANCE_RE.match(tokens[i]):
            balance_idx = i
            break
    if balance_idx is None or balance_idx < 7:
        return None

    balance = tokens[balance_idx]
    amount = tokens[balance_idx - 1]
    region = tokens[balance_idx - 2]
    if not AMOUNT_RE.match(amount):
        return None
    if not re.match(r"^\d{4,5}$", region):
        return None

    summary_tokens = tokens[5 : balance_idx - 2]
    counterparty_tokens = tokens[balance_idx + 1 : -2]

    if not summary_tokens:
        return None

    # 摘要可能被拆成多个 token（如"微信零钱提"+"现"）
    if len(summary_tokens) == 2 and all(len(t) <= 4 for t in summary_tokens):
        summary = summary_tokens[0] + summary_tokens[1]
    else:
        summary = " ".join(summary_tokens)

    counterparty = " ".join(counterparty_tokens) if counterparty_tokens else "（空）"

    return {
        "账号": tokens[0],
        "储种": tokens[1],
        "序号": tokens[2],
        "币种": tokens[3],
        "钞汇": tokens[4],
        "摘要": summary,
        "地区": region,
        "收入/支出金额": amount,
        "余额": balance,
        "对方户名": counterparty,
        "对方账号": counter_account,
        "渠道": channel,
    }


def parse_records(text: str) -> list[dict]:
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    records = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if SKIP_RE.match(line) or line.startswith("账号"):
            i += 1
            continue
        if not DATE_RE.match(line):
            i += 1
            continue

        date = line
        if i + 1 >= len(lines) or not TIME_RE.match(lines[i + 1]):
            i += 1
            continue

        time = lines[i + 1]
        i += 2

        data_parts: list[str] = []
        parsed = None
        while i < len(lines):
            if DATE_RE.match(lines[i]):
                break
            if SKIP_RE.match(lines[i]):
                i += 1
                continue
            data_parts.append(lines[i])
            parsed = parse_data_tokens(" ".join(data_parts))
            if parsed:
                records.append({"交易日期": date, "交易时间": time, **parsed})
                i += 1
                break
            i += 1

    return records


def write_txt(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for r in records:
            f.write("\t".join(r[c] for c in COLUMNS) + "\n")


def write_csv(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="提取工商银行 PDF 明细表格")
    parser.add_argument("pdf", type=Path, help="PDF 文件路径")
    parser.add_argument("-o", "--output", type=Path, help="输出文件（默认与 PDF 同名 .txt）")
    parser.add_argument("--csv", action="store_true", help="同时输出 CSV 文件")
    args = parser.parse_args()

    if not args.pdf.exists():
        sys.exit(f"文件不存在: {args.pdf}")

    text = extract_raw_text(args.pdf)
    records = parse_records(text)
    if not records:
        sys.exit("未能解析到任何交易记录，请检查 PDF 格式")

    out_txt = args.output or args.pdf.with_suffix(".txt")
    write_txt(records, out_txt)
    print(f"已提取 {len(records)} 条记录 -> {out_txt}")

    if args.csv:
        out_csv = out_txt.with_suffix(".csv")
        write_csv(records, out_csv)
        print(f"CSV 已保存 -> {out_csv}")


if __name__ == "__main__":
    main()
