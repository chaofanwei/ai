#!/usr/bin/env python3
"""从 2026-* 文件夹识别工资条，复制到 梁蓝欣_工资条/YYYY-MM/。"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from paddleocr import PaddleOCR

BASE = Path(__file__).resolve().parent
OUT = BASE / "梁蓝欣_工资条"

KW = [
    "工资条", "工资", "薪资", "薪金", "实发", "应发", "代扣",
    "基本工资", "绩效工资", "税前", "税后", "发薪", "薪酬",
]
WEAK = ["实发工资", "应发合计", "扣款合计", "社保", "公积金", "个税", "出勤天数"]


def log(msg: str) -> None:
    print(msg, flush=True)


def extract_text(ocr: PaddleOCR, path: Path) -> str:
    try:
        result = ocr.predict(str(path))
    except Exception as e:
        log(f"  OCR失败 {path.name}: {e}")
        return ""
    texts: list[str] = []
    if not result:
        return ""
    for block in result:
        if isinstance(block, dict):
            texts.extend(str(t) for t in (block.get("rec_texts") or []))
        elif block:
            for item in block:
                if isinstance(item, dict):
                    texts.extend(str(t) for t in (item.get("rec_texts") or []))
                elif item and len(item) >= 2 and item[1]:
                    texts.append(str(item[1][0]))
    return " ".join(texts)


def main() -> int:
    log("加载快速 OCR 模型...")
    ocr = PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
    )

    OUT.mkdir(parents=True, exist_ok=True)
    for child in OUT.iterdir():
        if child.is_dir() and re.match(r"2026-\d{2}", child.name):
            for f in child.iterdir():
                if f.is_file():
                    f.unlink()
        elif child.is_file():
            child.unlink()

    months = sorted(BASE.glob("2026-*"))
    hits_by_month: dict[str, list] = {}
    checked = 0

    for month_dir in months:
        month = month_dir.name
        files = [
            p
            for p in month_dir.iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
        ]
        log(f"\n=== {month} ({len(files)} 张) ===")
        month_hits = []
        for p in sorted(files):
            checked += 1
            text = extract_text(ocr, p)
            strong = [k for k in KW if k in text]
            weak = [k for k in WEAK if k in text]
            ok = bool(strong) or len(weak) >= 2
            if ok:
                dest_dir = OUT / month
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / p.name
                shutil.copy2(p, dest)
                month_hits.append((p.name, strong or weak, text[:80]))
                log(f"  ✓ {p.name} | {','.join(strong or weak)} | {text[:60]}")
            elif checked % 10 == 0:
                log(f"  ...已检查 {checked} 张")
        hits_by_month[month] = month_hits
        log(f"  -> 本月命中 {len(month_hits)} 张")

    log("\n======== 汇总 ========")
    total = 0
    for m, hits in hits_by_month.items():
        total += len(hits)
        log(f"{m}: {len(hits)} 张")
    log(f"合计: {total} 张 -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
