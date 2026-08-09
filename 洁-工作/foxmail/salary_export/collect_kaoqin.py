#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect monthly attendance (考勤) mails via IMAP into salary_export."""
from __future__ import annotations

import csv
import email
import imaplib
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

import importlib.util

BASE = Path(__file__).resolve().parent
HEADERS = Path("/Users/weichaofan/Documents/洁-工作/foxmail/mail_headers.csv")
CSV_PATH = BASE / "mail_salary.csv"
BODIES = BASE / "bodies"
ATTACH = BASE / "attachments"

IMAP_HOST = "imap.qiye.163.com"
IMAP_USER = "huijie@bidcenter.cn"


def load_refill():
    spec = importlib.util.spec_from_file_location("refill", BASE / "refill_bodies_imap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dec_hdr(s: str) -> str:
    if not s:
        return ""
    out = []
    for data, enc in decode_header(s):
        if isinstance(data, bytes):
            out.append(data.decode(enc or "utf-8", "replace"))
        else:
            out.append(data)
    return "".join(out)


def is_kaoqin_subject(subj: str) -> bool:
    subj = (subj or "").strip()
    if not subj:
        return False
    if subj.startswith("回复:") or subj.startswith("回复："):
        return False
    if re.search(
        r"号考勤|月考勤|考勤核对|考勤表|考勤汇总|考勤统计|本月考勤|"
        r"\d+\.\d+\s*[-–—]+\s*\d+\.\d+.*考勤|"
        r"考勤打卡",
        subj,
    ):
        return True
    if subj in ("考勤",) or re.fullmatch(r"\d{1,2}月考勤.*", subj):
        return True
    return False


def period_key(subj: str, recv: str) -> str:
    """Group duplicates for same attendance period (include year)."""
    s = subj.replace(" ", "")
    year = (recv or "")[:4] or "0000"
    m = re.search(r"(\d{1,2}\.\d{1,2}\s*[-–—]+\s*\d{1,2}\.\d{1,2})", s)
    if m:
        span = re.sub(r"\s+", "", m.group(1)).replace("—", "-").replace("–", "-")
        return f"{year}:{span}"
    m = re.search(r"(20\d{2}年)?(\d{1,2})月份?考勤", s)
    if m:
        y = m.group(1) or (year + "年")
        return f"{y}{m.group(2)}月"
    if "本月考勤" in s:
        return f"{recv[:7]}-本月"
    if s == "考勤":
        return f"{recv[:7]}-考勤"
    return f"{year}:{s}"


def pick_targets():
    rows = []
    with open(HEADERS, encoding="utf-8-sig", errors="replace") as f:
        for row in csv.DictReader(f):
            if is_kaoqin_subject(row.get("subject") or ""):
                rows.append(row)
    # prefer 以此为准 / 变更
    by_period = {}
    for row in rows:
        recv = row.get("recv_time") or ""
        subj = (row.get("subject") or "").strip()
        key = period_key(subj, recv)
        prev = by_period.get(key)
        score = 0
        if "以此为准" in subj or "以此位置" in subj:
            score += 10
        if "变更" in subj:
            score += 5
        if prev is None:
            by_period[key] = (score, row)
            continue
        ps, prow = prev
        if score > ps or (score == ps and recv > (prow.get("recv_time") or "")):
            by_period[key] = (score, row)
    targets = [v[1] for v in by_period.values()]
    targets.sort(key=lambda r: r.get("recv_time") or "", reverse=True)
    return targets


def subject_match(a: str, b: str) -> bool:
    def norm(s):
        s = re.sub(r"\s+", "", s or "")
        return s.replace("！", "!").replace("—", "-").replace("–", "-").replace("--", "-")

    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def imap_search_days(M, day: datetime, widen: bool = False):
    deltas = range(-2, 3) if widen else (0,)
    ids = []
    for delta in deltas:
        d2 = day + timedelta(days=delta)
        typ, data = M.search(None, "(ON %s)" % d2.strftime("%d-%b-%Y"))
        if data and data[0]:
            ids.extend(data[0].split())
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def main():
    pwd = sys.argv[1] if len(sys.argv) > 1 else ""
    if not pwd:
        envp = BASE / ".imap_pass"
        if envp.exists():
            pwd = envp.read_text().strip()
    if not pwd:
        print("Usage: collect_kaoqin.py <imap_auth_code>")
        return 2

    mod = load_refill()
    targets = pick_targets()
    print("kaoqin targets", len(targets), flush=True)

    existing = {r["id"]: r for r in mod.load_rows()}
    fieldnames = list(next(iter(existing.values())).keys()) if existing else [
        "id",
        "recv_time",
        "send_time",
        "from_name",
        "from_addr",
        "to",
        "subject",
        "size",
        "has_body",
        "body_file",
        "body",
        "source",
        "keywords",
    ]
    # ensure keywords field
    if "keywords" not in fieldnames:
        fieldnames.append("keywords")

    ATTACH.mkdir(exist_ok=True)
    BODIES.mkdir(exist_ok=True)

    M = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=120)
    M.login(IMAP_USER, pwd)
    M.select("INBOX", readonly=True)
    print("imap ok", flush=True)

    def find_msg(day, subj):
        for widen in (False, True):
            for iid in imap_search_days(M, day, widen=widen):
                typ, md = M.fetch(iid, "(BODY.PEEK[HEADER.FIELDS (SUBJECT)])")
                hdr = email.message_from_bytes(md[0][1])
                s = dec_hdr(hdr.get("Subject", ""))
                if subject_match(subj, s):
                    typ, md = M.fetch(iid, "(RFC822)")
                    return email.message_from_bytes(md[0][1]), iid.decode()
            if not widen:
                continue
        return None, None

    ok = miss = skip = 0
    for idx, row in enumerate(targets, 1):
        mid = row["id"]
        subj = (row.get("subject") or "").strip()
        recv = row.get("recv_time") or ""
        if mid in existing and (existing[mid].get("source") == "kaoqin"):
            bf = existing[mid].get("body_file") or ""
            path = BASE / bf if bf else None
            if path and path.exists() and "未找到原文" not in path.read_text("utf-8", "replace")[:80]:
                skip += 1
                continue

        day = None
        try:
            day = datetime.strptime(recv[:19], "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                day = datetime.strptime(recv[:10], "%Y-%m-%d")
            except Exception:
                pass

        msg = None
        imap_id = None
        if day and day >= datetime(2021, 5, 24):
            msg, imap_id = find_msg(day, subj)

        body_file = f"bodies/kaoqin__{mid}.txt"
        if msg:
            body, atts = mod.extract_body_and_attachments(msg, mid)
            if not body and atts:
                body = "【说明】考勤内容见附件：\n" + "\n".join(a.name for a in atts)
            (BASE / body_file).write_text((body or "") + "\n", encoding="utf-8")
            has_body = "yes" if body or atts else "no"
            print(f"[{idx}/{len(targets)}] OK", mid, recv[:10], subj[:36], "atts", len(atts), flush=True)
            ok += 1
            body_save = body
        else:
            note = (
                f"【说明】本地索引有此考勤邮件，但企业邮服务器收件箱未找到原文"
                f"（服务器约自 2021-05 起）。\n"
                f"主题：{subj}\n时间：{recv}\n发件：{row.get('from_addr')}\n"
            )
            (BASE / body_file).write_text(note, encoding="utf-8")
            has_body = "no"
            body_save = note
            print(f"[{idx}/{len(targets)}] MISS", mid, recv[:10], subj[:36], flush=True)
            miss += 1

        existing[mid] = {
            "id": mid,
            "recv_time": recv,
            "send_time": row.get("send_time") or recv,
            "from_name": row.get("from_name") or "",
            "from_addr": row.get("from_addr") or "",
            "to": row.get("to") or "",
            "subject": subj,
            "size": row.get("size") or "",
            "has_body": has_body,
            "body_file": body_file,
            "body": body_save[:5000],
            "source": "kaoqin",
            "keywords": "考勤,月考勤",
        }

    M.logout()

    all_rows = list(existing.values())
    all_rows.sort(key=lambda r: r.get("recv_time") or "", reverse=True)
    mod.save_rows(all_rows, fieldnames)
    mod.rebuild_index(all_rows)
    print("summary ok", ok, "miss", miss, "skip_existing", skip, "total_rows", len(all_rows), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
