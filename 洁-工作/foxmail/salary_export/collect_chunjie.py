#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect Spring Festival (春节放假) notice mails into salary_export."""
from __future__ import annotations

import csv
import importlib.util
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent
HEADERS = Path("/Users/weichaofan/Documents/洁-工作/foxmail/mail_headers.csv")
BODIES = BASE / "bodies"

MAIN_STORAGE = Path(
    "/Volumes/Storage/foxmail/extracted/Foxmail 7.2/Storage/huijie@bidcenter.cn"
)
INTRA_STORAGE = Path(
    "/Volumes/Storage/foxmail/extracted_old/Program Files/Foxmail 7.2/"
    "Storage/huijie@192.168.1.201"
)


def load_refill():
    spec = importlib.util.spec_from_file_location("refill", BASE / "refill_bodies_imap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_chunjie(subj: str) -> bool:
    s = (subj or "").strip()
    if "撤回" in s:
        return False
    if "春节" not in s:
        return False
    return any(k in s for k in ("放假", "假期", "安排")) or ("假" in s)


def norm_subj(s: str) -> str:
    s = re.sub(r"\s+", "", s or "")
    for pfx in ("转发:", "转发：", "Fw:", "FW:", "未知:", "未知："):
        if s.startswith(pfx):
            s = s[len(pfx) :]
    return s.replace("！", "!").replace("：", ":")


def clean_chunk(chunk: str, title_hint: str = "") -> str:
    chunk = re.sub(r"[\x00-\x08]+", "\n", chunk)
    chunk = re.sub(r"[\ue000-\uf8ff]+", "", chunk)
    for m in ("关于", "有关", "全体", "根据", "春节", title_hint[:8] if title_hint else "@@"):
        if m == "@@":
            continue
        i = chunk.find(m)
        if 0 <= i <= 160:
            chunk = chunk[i:]
            break
    for stop in ("\n中国采招网", "\nbjxingzheng@", "\n保密声明", "\n-----", "\n行政人事部\n"):
        i = chunk.find(stop, 100)
        if i > 160:
            # keep a bit of signature if 行政部
            if stop.endswith("行政人事部\n"):
                chunk = chunk[: i + len("行政人事部")]
            else:
                chunk = chunk[:i]
            break
    return re.sub(r"\n{3,}", "\n\n", chunk).strip()


def harvest_chunjie_bodies(storage: Path) -> dict[str, str]:
    """Scan bodytxt shards; return norm_subj -> body text."""
    found: dict[str, str] = {}
    if not storage.exists():
        return found
    keys = ("春节放假", "春节假期", "元旦春节放假", "春节放假安排")
    files = sorted(storage.rglob("bodytxt_txt.rec0"))
    print(f"scan {storage.name}: {len(files)} body shards", flush=True)
    for fi, p in enumerate(files, 1):
        try:
            bt = p.read_bytes().decode("utf-16le", "ignore")
        except Exception:
            continue
        if "春节" not in bt or "放假" not in bt:
            continue
        hits = []
        for k in keys:
            start = 0
            while True:
                i = bt.find(k, start)
                if i < 0:
                    break
                hits.append(i)
                start = i + len(k)
        for i in sorted(set(hits)):
            # back up to title/start
            start = max(0, i - 80)
            marker = bt.rfind("\ueaf4", start, i)
            if marker >= 0:
                start = marker
            chunk = bt[start : i + 2200]
            nxt = chunk.find("\ueaf4", 10)
            if 180 < nxt < len(chunk):
                chunk = chunk[:nxt]
            text = clean_chunk(chunk)
            if "春节" not in text or "放假" not in text:
                continue
            # title = first line-ish
            title = ""
            for line in text.splitlines():
                line = line.strip()
                if "春节" in line and ("放假" in line or "安排" in line):
                    title = line
                    break
            if not title:
                continue
            # skip spam / unrelated
            if "津贴" in title and "放假通知" not in title:
                continue
            key = norm_subj(title)
            # prefer longer body
            if key not in found or len(text) > len(found[key]):
                found[key] = text
        if fi % 3 == 0:
            print(f"  shard {fi}/{len(files)} harvested {len(found)}", flush=True)
    print(f"  done harvested {len(found)}", flush=True)
    return found


def pick_main_targets():
    rows = []
    with open(HEADERS, encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f):
            if is_chunjie(row.get("subject") or ""):
                rows.append(row)
    seen = set()
    uniq = []
    for r in sorted(rows, key=lambda x: x.get("recv_time") or "", reverse=True):
        key = (norm_subj(r.get("subject") or ""), (r.get("recv_time") or "")[:4])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    return uniq


def match_body(subj: str, bodies: dict[str, str]) -> str:
    ns = norm_subj(subj)
    if ns in bodies:
        return bodies[ns]
    for k, v in bodies.items():
        if ns in k or k in ns:
            return v
    # year-based soft match
    ym = re.search(r"20\d{2}", ns)
    if ym:
        year = ym.group(0)
        cands = [v for k, v in bodies.items() if year in k and "春节" in k]
        if len(cands) == 1:
            return cands[0]
    return ""


def pick_intranet_subjects() -> list[str]:
    p = INTRA_STORAGE / "Indexes/subject/subject_txt.rec0"
    if not p.exists():
        return []
    text = p.read_bytes().decode("utf-16le", "ignore")
    parts = re.split(r"[\x00-\x08\x0b\x0c\x0e-\x1f]+", text)
    out = []
    seen = set()
    for s in parts:
        s = s.strip()
        if not is_chunjie(s):
            continue
        key = norm_subj(s)
        if key in seen or len(key) < 6:
            continue
        seen.add(key)
        out.append(s)
    return out


def main():
    mod = load_refill()
    existing = {r["id"]: r for r in mod.load_rows()}
    fieldnames = list(next(iter(existing.values())).keys())
    BODIES.mkdir(exist_ok=True)

    main_bodies = harvest_chunjie_bodies(MAIN_STORAGE)
    intra_bodies = harvest_chunjie_bodies(INTRA_STORAGE)

    for row in pick_main_targets():
        mid = row["id"]
        subj = (row.get("subject") or "").strip()
        body = match_body(subj, main_bodies)
        body_file = f"bodies/chunjie__{mid}.txt"
        if body:
            note = mod.clean_text(body)
            has = "yes"
        else:
            note = (
                f"【说明】本地索引有此春节放假通知，正文未从全文索引抽出。\n"
                f"主题：{subj}\n时间：{row.get('recv_time')}\n"
                f"发件：{row.get('from_name')} {row.get('from_addr')}\n"
            )
            has = "no"
        (BASE / body_file).write_text(note + ("\n" if note else ""), encoding="utf-8")
        existing[mid] = {
            "id": mid,
            "recv_time": row.get("recv_time") or "",
            "send_time": row.get("send_time") or row.get("recv_time") or "",
            "from_name": row.get("from_name") or "",
            "from_addr": row.get("from_addr") or "",
            "to": row.get("to") or "",
            "subject": subj,
            "size": row.get("size") or "",
            "has_body": has,
            "body_file": body_file,
            "body": note[:5000],
            "source": "chunjie",
            "keywords": "春节放假,放假通知",
        }
        print(("OK" if has == "yes" else "META"), mid, (row.get("recv_time") or "")[:10], subj[:42], flush=True)

    for subj in pick_intranet_subjects():
        mid = f"intra_cj_{abs(hash(norm_subj(subj))) % 10_000_000}"
        body = match_body(subj, intra_bodies) or match_body(subj, main_bodies)
        body_file = f"bodies/chunjie__{mid}.txt"
        if body:
            note = mod.clean_text(body)
            has = "yes"
        else:
            note = (
                f"【说明】内网账号春节放假通知（主题索引命中）。\n"
                f"主题：{subj}\n账号：huijie@192.168.1.201\n"
            )
            has = "no"
        (BASE / body_file).write_text(note + ("\n" if note else ""), encoding="utf-8")
        ym = re.search(r"(20\d{2})", subj)
        recv = f"{ym.group(1)}-02-01 00:00:00" if ym else "2014-02-01 00:00:00"
        existing[mid] = {
            "id": mid,
            "recv_time": recv,
            "send_time": recv,
            "from_name": "内网",
            "from_addr": "huijie@192.168.1.201",
            "to": "",
            "subject": subj,
            "size": "",
            "has_body": has,
            "body_file": body_file,
            "body": note[:5000],
            "source": "chunjie:192.168.1.201",
            "keywords": "春节放假,放假通知,内网",
        }
        print(("OK" if has == "yes" else "META"), mid, recv[:10], subj[:42], flush=True)

    all_rows = list(existing.values())
    all_rows.sort(key=lambda r: r.get("recv_time") or "", reverse=True)
    mod.save_rows(all_rows, fieldnames)
    mod.rebuild_index(all_rows)
    cj = [r for r in all_rows if (r.get("source") or "").startswith("chunjie")]
    ok = sum(1 for r in cj if r.get("has_body") == "yes")
    print("done chunjie", len(cj), "with_body", ok, "total_rows", len(all_rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
