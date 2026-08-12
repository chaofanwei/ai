#!/usr/bin/env python3
"""从微信支付账单 xlsx 中识别疑似工资收入并生成汇总 md。"""

import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

COLUMNS = [
    "交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)",
    "支付方式", "当前状态", "交易单号", "商户单号", "备注", "说明",
]

LARGE_INCOME_COLUMNS = [
    "来源文件", "交易时间", "交易类型", "交易对方", "商品", "收/支", "金额(元)",
    "支付方式", "当前状态", "交易单号", "商户单号", "备注",
]

LARGE_INCOME_THRESHOLD = 2000

NON_SALARY_KEYWORDS = [
    "助力领现金", "全额返", "拼多多", "浏览奖励", "邀一得一", "打款啦", "活动打款",
]

LARGE_INCOME_EXCLUDE_KEYWORDS = [
    "好哥哥", "fanfan", "爸", "退款", "亚楠", "柯梦",
]

SALARY_COUNTERPARTIES = {"11", "12", "1", "`", "``", "、"}


def col_row(cell_ref: str) -> tuple[str, int]:
    match = re.match(r"([A-Z]+)(\d+)", cell_ref)
    return match.group(1), int(match.group(2))


def excel_datetime(serial: str) -> str:
    try:
        dt = datetime(1899, 12, 30) + timedelta(days=float(serial))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return str(serial)


def read_xlsx(path: Path) -> dict:
    with zipfile.ZipFile(path) as z:
        strings = []
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall("m:si", NS):
            text = si.find("m:t", NS)
            if text is not None:
                strings.append(text.text or "")
            else:
                strings.append("".join(node.text or "" for node in si.findall(".//m:t", NS)))

        sheet = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
        rows: dict[int, dict[str, str]] = {}
        for cell in sheet.findall(".//m:c", NS):
            ref = cell.get("r")
            col, row = col_row(ref)
            value = cell.find("m:v", NS)
            if value is None:
                continue
            text = strings[int(value.text)] if cell.get("t") == "s" else value.text
            rows.setdefault(row, {})[col] = text
        return rows


def parse_wechat_xlsx(path: Path) -> list[dict]:
    rows = read_xlsx(path)
    header_row = next((r for r in sorted(rows) if rows[r].get("A") == "交易时间"), None)
    if header_row is None:
        return []

    col_map = {
        "A": "交易时间", "B": "交易类型", "C": "交易对方", "D": "商品",
        "E": "收/支", "F": "金额(元)", "G": "支付方式", "H": "当前状态",
        "I": "交易单号", "J": "商户单号", "K": "备注",
    }

    records = []
    for row_num in sorted(rows):
        if row_num <= header_row or not rows[row_num].get("A"):
            continue
        data = rows[row_num]
        record = {name: data.get(col, "") or "" for col, name in col_map.items()}
        record["交易时间"] = excel_datetime(record["交易时间"])
        record["金额(元)"] = float(record["金额(元)"] or 0)
        records.append(record)
    return records


def is_large_income_excluded(record: dict) -> bool:
    text = f"{record['交易类型']} {record['交易对方']} {record['商品']} {record['备注']}"
    return any(keyword in text for keyword in LARGE_INCOME_EXCLUDE_KEYWORDS)


def is_salary_like(record: dict) -> bool:
    if record["收/支"] != "收入" or record["金额(元)"] <= 0:
        return False
    if record["交易类型"] != "其他":
        return False

    text = f"{record['交易对方']} {record['备注']} {record['商品']}"
    if any(keyword in text for keyword in NON_SALARY_KEYWORDS):
        return False
    if "企业工资" in text:
        return True

    counterparty = record["交易对方"]
    if re.match(r"^\d{1,2}月?奖?$", counterparty) or counterparty in SALARY_COUNTERPARTIES:
        return record["金额(元)"] >= 1000
    return False


def next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def salary_label(record: dict) -> str:
    label = record["交易对方"]
    amount = record["金额(元)"]
    if "企业工资" in f"{record['交易对方']} {record['备注']} {record['商品']}":
        return "企业工资"
    if label.endswith("月奖") or label.endswith("奖"):
        return label
    if label.isdigit() and amount >= 12000:
        return f"{label}月工资"
    if label.isdigit():
        return f"{label}月奖金" if amount < 12000 else f"{label}月工资"
    if label in {"`", "``", "、"}:
        month = record["交易时间"][5:7]
        kind = "工资" if amount >= 5000 else "奖金"
        return f"疑似{int(month)}月{kind}"
    return "疑似工资"


def md_cell(value) -> str:
    text = str(value).replace("|", "\\|").replace("\n", " ")
    return text if text else "（空）"


def build_markdown(records: list[dict]) -> str:
    for record in records:
        record["说明"] = salary_label(record)

    records.sort(key=lambda item: item["交易时间"])
    total = sum(item["金额(元)"] for item in records)

    if not records:
        return "\n".join([
            "# 工资汇总",
            "",
            "来源：微信支付账单，筛选疑似工资的收入记录。",
            "",
            "未找到符合条件的记录。",
        ])

    months_with = {item["交易时间"][:7] for item in records}
    start_year, start_month = map(int, min(months_with).split("-"))
    end_year, end_month = map(int, max(months_with).split("-"))

    missing = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        ym = f"{year:04d}-{month:02d}"
        if ym not in months_with:
            missing.append(ym)
        year, month = next_month(year, month)

    header = "| " + " | ".join(COLUMNS) + " |"
    sep = "|" + "|".join(["------"] * len(COLUMNS)) + "|"

    lines = [
        "# 工资汇总",
        "",
        "来源：微信支付账单，筛选疑似工资的收入记录。",
        "",
        "识别规则：交易类型为 **其他**，且交易对方为月份标记（如 `11`、`12`、`1`、`、` 等）或 **企业工资**；排除助力领现金等活动小额打款。",
        "",
        f"- **开始时间**：{records[0]['交易时间']}",
        f"- **结束时间**：{records[-1]['交易时间']}",
        f"- **缺失月份**：{'、'.join(missing) if missing else '无'}",
        f"- **共 {len(records)} 笔，合计 {total:,.2f} 元**",
        "",
        "## 汇总明细",
        "",
        header,
        sep,
    ]

    for record in records:
        amount = record["金额(元)"]
        row = [
            record["交易时间"],
            record["交易类型"],
            record["交易对方"],
            record["商品"],
            record["收/支"],
            f"{amount:,.2f}",
            record["支付方式"],
            record["当前状态"],
            record["交易单号"],
            record["商户单号"],
            record["备注"],
            record["说明"],
        ]
        lines.append("| " + " | ".join(md_cell(v) for v in row) + " |")

    return "\n".join(lines)


def build_large_income_markdown(records: list[dict]) -> str:
    records.sort(key=lambda item: item["交易时间"])
    total = sum(item["金额(元)"] for item in records)

    header = "| " + " | ".join(LARGE_INCOME_COLUMNS) + " |"
    sep = "|" + "|".join(["------"] * len(LARGE_INCOME_COLUMNS)) + "|"

    lines = [
        "# 大额收入核查",
        "",
        "来源：微信支付账单，筛选 **收入** 且 **金额 > 2000 元** 的记录（已排除工资汇总及好哥哥、fanfan、爸、退款、亚楠、柯梦相关条目），供逐一核查。",
        "",
        f"- **共 {len(records)} 笔，合计 {total:,.2f} 元**",
        "",
        "## 大额收入明细",
        "",
        header,
        sep,
    ]

    for record in records:
        amount = record["金额(元)"]
        row = [
            record.get("来源文件", ""),
            record["交易时间"],
            record["交易类型"],
            record["交易对方"],
            record["商品"],
            record["收/支"],
            f"{amount:,.2f}",
            record["支付方式"],
            record["当前状态"],
            record["交易单号"],
            record["商户单号"],
            record["备注"],
        ]
        lines.append("| " + " | ".join(md_cell(v) for v in row) + " |")

    return "\n".join(lines)


def load_all_xlsx(base: Path) -> list[dict]:
    all_records = []
    for path in sorted(base.glob("*.xlsx")):
        if path.name.startswith("."):
            continue
        for item in parse_wechat_xlsx(path):
            item["来源文件"] = path.name
            all_records.append(item)
    return all_records


def main() -> None:
    base = Path("/home/fan/mac/ai/jie/微信")
    all_records = load_all_xlsx(base)

    salary_records = [item for item in all_records if is_salary_like(item)]
    salary_output = base / "工资汇总.md"
    salary_output.write_text(build_markdown(salary_records), encoding="utf-8")
    print(f"已写入 {len(salary_records)} 条工资记录 -> {salary_output}")

    large_income_records = [
        item for item in all_records
        if item["收/支"] == "收入"
        and item["金额(元)"] > LARGE_INCOME_THRESHOLD
        and not is_salary_like(item)
        and not is_large_income_excluded(item)
    ]
    large_output = base / "大额收入核查.md"
    large_output.write_text(build_large_income_markdown(large_income_records), encoding="utf-8")
    print(f"已写入 {len(large_income_records)} 条大额收入 -> {large_output}")


if __name__ == "__main__":
    main()
