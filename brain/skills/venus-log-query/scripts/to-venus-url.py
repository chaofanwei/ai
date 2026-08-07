#!/usr/bin/env python3
"""将 Venus 查询 SQL 转为浏览器可直接打开的 URL。"""

import argparse
import subprocess
from urllib.parse import quote

SITES = {
    "main": {"domain": "venus.cloud.qiyi.domain", "project_id": 305},
    "intl": {"domain": "venus-intl.cloud.qiyi.domain", "project_id": 2586},
}


def to_ms(timestr: str) -> int:
    return int(subprocess.check_output(["date", "-d", timestr, "+%s%3N"]).decode().strip())


def build_url(
    site: str,
    table: str,
    sql: str,
    start_ts: int,
    end_ts: int,
    interval: str = "1m",
) -> str:
    cfg = SITES[site]
    encoded_sql = quote(sql, safe="*")
    return (
        f"https://{cfg['domain']}/#/projects/{cfg['project_id']}/new-search/{table}/{encoded_sql}"
        f"&startTs={start_ts}&endTs={end_ts}&intervalSearch={interval}"
    )


def main():
    parser = argparse.ArgumentParser(description="Generate Venus browser search URL")
    parser.add_argument("--site", choices=SITES.keys(), default="main", help="main or intl")
    parser.add_argument("--table", default="log_nginx_cache_access", help="log table name")
    parser.add_argument("--sql", required=True, help="queryString SQL")
    parser.add_argument("--start", help="start time, e.g. '2026-07-08 11:00:00'")
    parser.add_argument("--end", help="end time, e.g. '2026-07-08 11:15:00'")
    parser.add_argument("--start-ts", type=int, help="start timestamp ms")
    parser.add_argument("--end-ts", type=int, help="end timestamp ms")
    parser.add_argument("--minutes", type=int, help="recent N minutes (use with --end-ts or now)")
    parser.add_argument("--interval", default="1m", help="intervalSearch, default 1m")
    args = parser.parse_args()

    if args.start_ts and args.end_ts:
        start_ts, end_ts = args.start_ts, args.end_ts
    elif args.start and args.end:
        start_ts, end_ts = to_ms(args.start), to_ms(args.end)
    elif args.minutes:
        end_ts = int(subprocess.check_output(["date", "+%s%3N"]).decode().strip())
        start_ts = end_ts - args.minutes * 60 * 1000
    else:
        parser.error("need --start/--end, --start-ts/--end-ts, or --minutes")

    print(build_url(args.site, args.table, args.sql, start_ts, end_ts, args.interval))


if __name__ == "__main__":
    main()
