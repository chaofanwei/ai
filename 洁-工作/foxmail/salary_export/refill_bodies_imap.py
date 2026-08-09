#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refill missing salary-related mail bodies via IMAP and rebuild index.html."""
from __future__ import annotations

import csv
import email
import imaplib
import re
import sys
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
BODIES = BASE / "bodies"
ATTACH = BASE / "attachments"
CSV_PATH = BASE / "mail_salary.csv"
INDEX = BASE / "index.html"

IMAP_HOST = "imap.qiye.163.com"
IMAP_USER = "huijie@bidcenter.cn"
# Prefer env; fallback to session auth code if present
IMAP_PASS = ""


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


def clean_text(t: str) -> str:
    if not t:
        return ""
    # drop UTF-16LE BOM-ish / private-use garbage prefixes from Foxmail extract
    t = t.replace("\ufeff", "")
    t = re.sub(r"^[\x00-\x08\x0b\x0c\x0e-\x1f\u200b-\u200f\ue000-\uf8ff]+", "", t)
    # if still starts with garble then CJK/table header, cut to first useful marker
    markers = (
        "姓名",
        "关于",
        "公司",
        "通知",
        "工资",
        "请以下",
        "定点医疗",
        "输入当前",
        "【说明】",
        "月份 公司",  # salary table header only
    )
    for m in markers:
        i = t.find(m)
        if 0 <= i <= 40:
            t = t[i:]
            break
    # keep "7月份考勤情况…" — do not cut at bare 月份
    # normalize newlines
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</p>", "\n", html)
    html = re.sub(r"(?i)</div>", "\n", html)
    html = re.sub(r"(?i)</tr>", "\n", html)
    html = re.sub(r"(?i)</li>", "\n", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    from html import unescape

    text = unescape(html)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def extract_body_and_attachments(msg, mid: str):
    texts = []
    htmls = []
    atts = []
    for part in msg.walk():
        ctype = part.get_content_type()
        disp = str(part.get("Content-Disposition") or "")
        fn = part.get_filename()
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        if fn:
            fn = dec_hdr(fn)
            safe = re.sub(r"[/\\]+", "_", fn)
            ap = ATTACH / f"{mid}__{safe}"
            ap.parent.mkdir(parents=True, exist_ok=True)
            ap.write_bytes(payload)
            atts.append(ap)
            continue
        if "attachment" in disp.lower():
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            s = payload.decode(charset, "replace")
        except Exception:
            s = payload.decode("utf-8", "replace")
        if ctype == "text/plain":
            texts.append(s)
        elif ctype == "text/html":
            htmls.append(s)
        elif ctype == "image/jpeg" and 20_000 < len(payload) < 5_000_000:
            ap = ATTACH / f"{mid}__inline.jpg"
            ap.parent.mkdir(parents=True, exist_ok=True)
            ap.write_bytes(payload)
            atts.append(ap)
    body = ""
    if texts:
        body = max(texts, key=len)
    elif htmls:
        body = html_to_text(max(htmls, key=len))
    return clean_text(body), atts


def parse_recv(r):
    s = (r.get("recv_time") or r.get("send_time") or "").strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    return None


def needs_refill(r) -> bool:
    bf = r.get("body_file") or ""
    path = BASE / bf if bf else None
    t = path.read_text("utf-8", "replace").strip() if path and path.exists() else (r.get("body") or "").strip()
    if not t or len(t) < 20:
        return True
    if "当前无法直接抽出" in t or "不是纯文字，而是截图" in t:
        return True
    if "中国采招网—北京行政部" in t or "中国采招网-北京行政部" in t:
        before = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]", "", t.split("中国采招网")[0])
        if len(before) < 20:
            return True
    # notices from admin without salary table content
    frm = r.get("from_addr") or ""
    if "bjxingzheng" in frm and not re.search(r"常会洁|基本工资|发放\s", t):
        # if mostly short / garble
        useful = re.sub(r"[\x00-\x1f\ue000-\uf8ff]", "", t)
        if len(useful) < 180:
            return True
        # also refill policy mails that look truncated to signature
        if useful.count("通知") == 0 and "请假" in (r.get("subject") or ""):
            return True
    return False


def imap_search_day(M, day: datetime):
    # ON date
    typ, data = M.search(None, "(ON %s)" % day.strftime("%d-%b-%Y"))
    ids = data[0].split() if data and data[0] else []
    # also neighboring days for timezone
    for delta in (-1, 1):
        d2 = day + timedelta(days=delta)
        typ, data = M.search(None, "(ON %s)" % d2.strftime("%d-%b-%Y"))
        if data and data[0]:
            ids += data[0].split()
    # unique preserve order
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def subject_match(a: str, b: str) -> bool:
    def norm(s):
        s = re.sub(r"\s+", "", s or "")
        s = s.replace("！", "!").replace("（", "(").replace("）", ")")
        return s

    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def fetch_match(M, r):
    day = parse_recv(r)
    if not day:
        return None, None
    subj_want = r.get("subject") or ""
    frm_want = (r.get("from_addr") or "").lower()
    candidates = imap_search_day(M, day)
    best = None
    for mid in candidates:
        typ, msg_data = M.fetch(mid, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
        raw = msg_data[0][1] if msg_data and msg_data[0] else b""
        msg = email.message_from_bytes(raw)
        subj = dec_hdr(msg.get("Subject", ""))
        frm = dec_hdr(msg.get("From", "")).lower()
        if not subject_match(subj_want, subj):
            continue
        if frm_want:
            local = frm_want.split("@")[0]
            if local not in frm and frm_want not in frm:
                # allow exact subject match even if from display differs
                if re.sub(r"\s+", "", subj_want) != re.sub(r"\s+", "", subj):
                    continue
        best = mid
        break
    if not best:
        return None, None
    typ, msg_data = M.fetch(best, "(RFC822)")
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    return msg, best.decode()


def load_rows():
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save_rows(rows, fieldnames):
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            # keep body short in csv? original had full body - keep cleaned
            w.writerow(r)


def rebuild_index(rows):
    arts = []
    navs = []
    for r in rows:
        subj = r.get("subject") or ""
        kw = r.get("keywords") or ""
        frm = f"{r.get('from_name') or ''} {r.get('from_addr') or ''}".strip()
        bf = r.get("body_file") or ""
        body = ""
        if bf and (BASE / bf).exists():
            body = clean_text((BASE / bf).read_text("utf-8", "replace"))
        else:
            body = clean_text(r.get("body") or "")
        mid = r.get("id") or ""
        recv = (r.get("recv_time") or "")[:10]
        # attachments for this mail
        imgs = sorted(ATTACH.glob(f"{mid}__*")) if ATTACH.exists() else []
        # handbook special
        handbook_img = BASE / "handbook_20250827" / "handbook_catch.jpg"
        extra_html = ""
        highlight = ""
        anchor = f"mail-{mid}"
        if mid == "129547" and handbook_img.exists():
            highlight = " highlight"
            anchor = "handbook"
            rel = "handbook_20250827/handbook_catch.jpg"
            eml = "handbook_20250827/imap_77230_handbook.eml"
            extra_html = f'''<div class="attach"><a href="{rel}" target="_blank" rel="noopener"><img src="{rel}" alt="员工手册截图" width="658" height="638" loading="lazy"></a></div>
<p class="note">正文为截图附件 · <a href="{rel}" target="_blank">打开原图</a> · <a href="{eml}">下载 .eml</a></p>'''
            body = ""
        elif imgs:
            parts = []
            for ap in imgs:
                rel = ap.relative_to(BASE).as_posix()
                if ap.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                    parts.append(
                        f'<div class="attach"><a href="{escape(rel)}" target="_blank" rel="noopener">'
                        f'<img src="{escape(rel)}" alt="{escape(ap.name)}" loading="lazy"></a></div>'
                    )
                else:
                    parts.append(f'<p class="note">附件：<a href="{escape(rel)}">{escape(ap.name)}</a></p>')
            extra_html = "\n".join(parts)
        pre = f"<pre>{escape(body)}</pre>" if body else ""
        desc = kw or (frm.split()[0] if frm else "邮件")
        navs.append(
            f'''<a class="nav-item" href="#{anchor}" data-subj="{escape(subj)}" data-kw="{escape(kw)}" data-from="{escape(frm)}" title="{escape(subj)}">
<span class="nav-date">{escape(recv)}</span>
<span class="nav-title">{escape(subj)}</span>
<span class="nav-desc">{escape(desc)}</span>
</a>'''
        )
        arts.append(
            f'''<article class="mail{highlight}" id="{anchor}" data-subj="{escape(subj)}" data-kw="{escape(kw)}" data-from="{escape(frm)}">
<header><h3>{escape(subj)}</h3>
<div class="meta">{escape(r.get("recv_time") or "")} · {escape(frm)} · <span class="kw">{escape(kw)}</span> · {escape(r.get("source") or "")}</div>
</header>
{extra_html}
{pre}
</article>'''
        )
    html = f'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>薪酬/社保/政策邮件 ({len(rows)})</title>
<style>
:root {{ --side-w: 300px; --top-h: 72px; }}
* {{ box-sizing: border-box; }}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Segoe UI",sans-serif;margin:0;background:#f6f7f9;color:#222}}
header.top{{position:sticky;top:0;background:#1f3b5b;color:#fff;padding:10px 16px;z-index:5}}
header.top a{{color:#9fd0ff}}
header.top input{{width:min(420px,90%);padding:8px 10px;border:0;border-radius:6px;margin-top:8px}}
.layout{{display:flex;align-items:flex-start;min-height:calc(100vh - var(--top-h));}}
.sidebar{{position:sticky;top:var(--top-h);flex:0 0 var(--side-w);width:var(--side-w);height:calc(100vh - var(--top-h));overflow:auto;background:#fff;border-right:1px solid #e5e8ee;padding:10px 0;z-index:3}}
.sidebar h2{{margin:0;padding:8px 14px 10px;font-size:13px;color:#666;font-weight:600;letter-spacing:.02em}}
.nav-item{{display:block;padding:8px 14px;text-decoration:none;color:inherit;border-left:3px solid transparent;border-bottom:1px solid #f0f2f5}}
.nav-item:hover,.nav-item:focus{{background:#f3f7fc;border-left-color:#0b6bcb}}
.nav-item.active{{background:#eaf2fb;border-left-color:#0b6bcb}}
.nav-date{{display:block;font-size:11px;color:#888;margin-bottom:2px}}
.nav-title{{display:block;font-size:13px;line-height:1.35;color:#1a1a1a;word-break:break-word}}
.nav-desc{{display:block;font-size:11px;color:#0b6bcb;margin-top:3px}}
.content{{flex:1;min-width:0;max-width:960px;padding:12px 16px 40px}}
.mail{{background:#fff;border-radius:10px;padding:14px 16px;margin:12px 0;box-shadow:0 1px 3px rgba(0,0,0,.06);scroll-margin-top:calc(var(--top-h) + 12px)}}
.mail h3{{margin:0 0 6px;font-size:17px}}
.meta{{color:#666;font-size:12px;margin-bottom:10px}}
.kw{{color:#0b6bcb}}
pre{{white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.45;background:#fafbfc;padding:10px;border-radius:6px;max-height:480px;overflow:auto}}
.hidden{{display:none !important}}
.attach{{margin-top:8px}}
.attach a{{display:inline-block;max-width:100%}}
.attach img{{display:block;max-width:min(100%,720px);height:auto;border-radius:8px;border:1px solid #e5e8ee;background:#fff;cursor:zoom-in}}
.note{{color:#666;font-size:12px;margin:8px 0 0}}
.mail.highlight{{outline:2px solid #0b6bcb;outline-offset:1px}}
@media (max-width:900px){{
  .layout{{display:block}}
  .sidebar{{position:relative;top:0;width:100%;height:auto;max-height:42vh;border-right:0;border-bottom:1px solid #e5e8ee}}
  .content{{max-width:none}}
}}
</style></head><body>
<header class="top">
<div><strong>薪酬 / 社保公积金 / 银行卡个税 / 公司政策 / 放假通知</strong> · 共 {len(rows)} 封 · <a href="#handbook">员工手册截图</a></div>
<input id="q" placeholder="搜索标题、关键词、发件人…">
</header>
<div class="layout">
<aside class="sidebar" id="side">
<h2>邮件索引 · {len(rows)}</h2>
{chr(10).join(navs)}
</aside>
<main class="content" id="list">
{chr(10).join(arts)}
</main>
</div>
<script>
const q=document.getElementById('q');
function filter(){{
  const t=q.value.trim().toLowerCase();
  document.querySelectorAll('.mail, .nav-item').forEach(el=>{{
    const hay=(el.dataset.subj+' '+el.dataset.kw+' '+el.dataset.from).toLowerCase();
    el.classList.toggle('hidden', t && !hay.includes(t));
  }});
}}
q.addEventListener('input', filter);
// highlight active nav while scrolling
const arts=[...document.querySelectorAll('.mail')];
const navMap=new Map([...document.querySelectorAll('.nav-item')].map(a=>[a.getAttribute('href').slice(1), a]));
const io=new IntersectionObserver((entries)=>{{
  for (const e of entries){{
    if (!e.isIntersecting) continue;
    const id=e.target.id;
    navMap.forEach(a=>a.classList.remove('active'));
    const n=navMap.get(id); if(n){{ n.classList.add('active'); n.scrollIntoView({{block:'nearest'}}); }}
  }}
}}, {{ rootMargin: '-40% 0px -50% 0px', threshold: 0.01 }});
arts.forEach(a=>io.observe(a));
</script></body></html>
'''
    INDEX.write_text(html, encoding="utf-8")



def main():
    global IMAP_PASS
    IMAP_PASS = (sys.argv[1] if len(sys.argv) > 1 else "") or IMAP_PASS
    if not IMAP_PASS:
        # read from env file if any
        envp = BASE / ".imap_pass"
        if envp.exists():
            IMAP_PASS = envp.read_text().strip()
    if not IMAP_PASS:
        print("Usage: refill_bodies_imap.py <imap_auth_code>")
        return 2

    rows = load_rows()
    fieldnames = list(rows[0].keys())
    ATTACH.mkdir(exist_ok=True)

    # 1) clean all existing bodies first
    cleaned_n = 0
    for r in rows:
        bf = r.get("body_file") or ""
        path = BASE / bf if bf else None
        if not path or not path.exists():
            continue
        old = path.read_text("utf-8", "replace")
        new = clean_text(old)
        # keep handbook placeholder handling later
        if r.get("id") == "129547":
            continue
        if new != old.strip() or old != new:
            path.write_text(new + ("\n" if new else ""), encoding="utf-8")
            r["body"] = new[:5000]
            r["has_body"] = "yes" if new else r.get("has_body")
            cleaned_n += 1
    print("cleaned local bodies:", cleaned_n)

    targets = [r for r in rows if needs_refill(r)]
    # skip clearly internal-only that won't be on qiye (old 192.168) unless already targeted wrongly
    targets = [
        r
        for r in targets
        if "192.168." not in (r.get("from_addr") or "")
        or (r.get("source") or "").startswith("main")
    ]
    print("imap targets:", len(targets))
    for r in targets:
        print(" -", r["id"], r.get("recv_time"), (r.get("subject") or "")[:40])

    M = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=90)
    M.login(IMAP_USER, IMAP_PASS)
    M.select("INBOX", readonly=True)
    print("imap login ok")

    ok = fail = 0
    for r in targets:
        mid = r["id"]
        try:
            msg, imap_id = fetch_match(M, r)
        except Exception as e:
            print("FAIL", mid, e)
            fail += 1
            continue
        if not msg:
            print("MISS", mid, r.get("subject"))
            fail += 1
            continue
        body, atts = extract_body_and_attachments(msg, mid)
        bf = r.get("body_file") or f"bodies/main__{mid}.txt"
        path = BASE / bf
        path.parent.mkdir(exist_ok=True)
        note = ""
        if not body and atts:
            names = ", ".join(a.name for a in atts)
            note = f"【说明】正文为附件/截图：{names}\n"
            body = note
        path.write_text(body + ("\n" if body else ""), encoding="utf-8")
        r["body_file"] = str(Path(bf).as_posix()) if not bf.startswith("bodies/") else bf
        if not r["body_file"].startswith("bodies/"):
            r["body_file"] = bf
        r["body"] = body[:5000]
        r["has_body"] = "yes"
        print("OK", mid, "imap", imap_id, "body_len", len(body), "atts", len(atts))
        ok += 1

    M.logout()

    # handbook: ensure body note + image already present
    for r in rows:
        if r.get("id") == "129547":
            bf = r.get("body_file") or "bodies/main__129547.txt"
            path = BASE / bf
            path.write_text(
                "【说明】此封邮件正文为截图附件 Catch(08-27-10-27-42).jpg，已在 index.html 中直接展示。\n"
                "路径：handbook_20250827/handbook_catch.jpg\n",
                encoding="utf-8",
            )
            r["body"] = path.read_text(encoding="utf-8")
            r["has_body"] = "yes"

    save_rows(rows, fieldnames)
    rebuild_index(rows)
    print("saved csv + index.html")
    print("summary ok", ok, "fail/miss", fail)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
