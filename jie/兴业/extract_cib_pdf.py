#!/usr/bin/env python3
"""从兴业银行交易明细 PDF 中提取表格内容为 CSV。"""

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

COLUMNS = [
    "交易时间", "记账日期", "摘要", "支收", "交易金额", "账户余额",
    "交易用途", "对方户名", "对方账号", "对方银行",
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DATA_RE = re.compile(r"^(\d{8})\s+(\S+)\s+(收|支)\s+([\d,]+\.\d{2})\s+(\S+)(?:\s+(.*))?$")
ACCOUNT_RE = re.compile(r"^\d{10,}$")
SKIP_RE = re.compile(
    r"^(兴业银行|Industrial Bank|Account Name|Account No|Currency|Transfer Amount|Counterparty|Print Time|"
    r"Transaction|Accounting Date|Expenditure|Income|Time$|Type$|Amount$|Usage$|Name：|No\.：|"
    r"sealPos|第 \d|说明：|客户限定|支出 ¥|重要说明|户 名|币 种|对方账号|对方户名|打印日期|"
    r"转账金额|交易时间|Counterparty's|Use/Remark|Range：|2026年|^\d{4}-\d{2}-\d{2}-\d{4})"
)


def extract_raw_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-raw", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_records(text: str) -> list[dict]:
    lines = [line.strip() for line in text.strip().split("\n") if line.strip() and not SKIP_RE.match(line.strip())]
    records = []
    i = 0
    while i < len(lines):
        if not DATE_RE.match(lines[i]):
            i += 1
            continue

        tx_date = lines[i]
        i += 1
        tx_time = lines[i] if i < len(lines) else ""
        i += 1
        if i >= len(lines):
            break

        match = DATA_RE.match(lines[i])
        if not match:
            continue

        acct_date, summary, direction, amount, balance = match.group(1, 2, 3, 4, 5)
        usage = (match.group(6) or "").strip()
        i += 1

        name_parts: list[str] = []
        account = ""
        bank = ""
        while i < len(lines) and not DATE_RE.match(lines[i]):
            if ACCOUNT_RE.match(lines[i]):
                account = lines[i]
                i += 1
                if i < len(lines) and not DATE_RE.match(lines[i]) and not DATA_RE.match(lines[i]):
                    bank = lines[i]
                    i += 1
                break
            name_parts.append(lines[i])
            i += 1

        records.append({
            "交易时间": f"{tx_date} {tx_time}",
            "记账日期": f"{acct_date[:4]}-{acct_date[4:6]}-{acct_date[6:8]}",
            "摘要": summary,
            "支收": direction,
            "交易金额": amount,
            "账户余额": balance,
            "交易用途": usage,
            "对方户名": "".join(name_parts),
            "对方账号": account,
            "对方银行": bank,
        })

    return records


def write_csv(records: list[dict], out_path: Path) -> None:
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(records)


def main() -> None:
    parser = argparse.ArgumentParser(description="提取兴业银行 PDF 明细表格")
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
