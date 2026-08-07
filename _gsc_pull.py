#!/usr/bin/env python3
"""
Search Console puller — CLI.

  python3 _gsc_pull.py --list                       # properties this login can read
  python3 _gsc_pull.py --days 28                    # report for $GSC_SITE
  python3 _gsc_pull.py --site https://wwslgc.collaborativeconceptsfl.com --days 28 \
      --permits permits.csv --out wwslgc/_seo
  python3 _gsc_pull.py --all --days 90              # every property, one report each

Writes <out>/gsc-<host>-<end>.md plus queries/pages/cities CSVs, and prints the
report to stdout. Credentials come from env only (see api/gsc.py header) — no
secret is ever printed, logged, or written to the report.
"""
import argparse
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "api"))
import gsc  # noqa: E402


def _host(site):
    return (site.replace("sc-domain:", "").replace("https://", "").replace("http://", "")
            .strip("/").replace("/", "_"))


def build(client, site, days, end=None, permits_csv=None, compare_prev=True):
    start, end = gsc.date_range(days, end=end)
    q_rows = gsc.to_records(client.query(site, start, end, ["query"]), ["query"])
    p_rows = gsc.to_records(client.query(site, start, end, ["page"]), ["page"])
    data = {
        "site": site, "start": start, "end": end,
        "totals": gsc.totals(q_rows),
        "top_queries": gsc.top(q_rows, "clicks", 50),
        "top_pages": gsc.top(p_rows, "clicks", 50),
        "striking": gsc.striking_distance(q_rows),
        "ctr_gaps": gsc.ctr_gaps(q_rows),
        "cities": gsc.by_city(p_rows, key="page"),
        "counties": gsc.by_county(p_rows, key="page"),
        "queries_all": q_rows, "pages_all": p_rows,
    }
    if compare_prev:
        pstart, pend = gsc.previous_range(start, end)
        prev = gsc.to_records(client.query(site, pstart, pend, ["query"]), ["query"])
        data["totals_prev"] = gsc.totals(prev)
        data["movers"] = gsc.compare(q_rows, prev, "query")
    if permits_csv and os.path.exists(permits_csv):
        with open(permits_csv) as f:
            counts = gsc.permit_counts_from_csv(f.read())
        data["permits"] = gsc.cross_permits(data["counties"], counts)
    return data


def write_out(data, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    stem = f"gsc-{_host(data['site'])}-{data['end']}"
    report = gsc.render_report(data["site"], data["start"], data["end"], data)
    paths = []
    md = os.path.join(out_dir, f"{stem}.md")
    with open(md, "w") as f:
        f.write(report + "\n")
    paths.append(md)
    for name, rows, cols in (
        ("queries", data["queries_all"], ["query", "clicks", "impressions", "ctr", "position"]),
        ("pages", data["pages_all"], ["page", "clicks", "impressions", "ctr", "position"]),
        ("cities", data["cities"], ["city", "county", "clicks", "impressions", "ctr", "position"]),
    ):
        if not rows:
            continue
        p = os.path.join(out_dir, f"{stem}-{name}.csv")
        with open(p, "w") as f:
            f.write(gsc.to_csv(rows, cols))
        paths.append(p)
    return report, paths


def main(argv=None):
    ap = argparse.ArgumentParser(description="Pull Google Search Console performance data")
    ap.add_argument("--site", default=os.environ.get("GSC_SITE", ""),
                    help="property URL (or sc-domain:example.com); default $GSC_SITE")
    ap.add_argument("--all", action="store_true", help="run every readable property")
    ap.add_argument("--list", action="store_true", help="list readable properties and exit")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--end", default="", help="YYYY-MM-DD (default: today minus the 3-day lag)")
    ap.add_argument("--permits", default="", help="permits CSV export to cross-reference")
    ap.add_argument("--out", default="wwslgc/_seo", help="output directory")
    ap.add_argument("--no-compare", action="store_true", help="skip the previous-period pull")
    args = ap.parse_args(argv)

    auth = gsc.Auth.from_env()
    problems = auth.configured()
    if problems:
        print("Search Console credentials not configured:\n  " + "\n  ".join(problems),
              file=sys.stderr)
        print("\nSee wwslgc/_seo/GSC_PULLER.md for the 10-minute setup.", file=sys.stderr)
        return 2
    client = gsc.SearchConsole(auth)

    try:
        sites = client.sites() if (args.all or args.list) else [args.site]
    except gsc.GSCError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    if args.list:
        for s in sites:
            print(s)
        return 0
    sites = [s for s in sites if s]
    if not sites:
        print("no site given: pass --site or set GSC_SITE (or use --list)", file=sys.stderr)
        return 2

    end = datetime.strptime(args.end, "%Y-%m-%d").date() if args.end else None
    rc = 0
    for site in sites:
        try:
            data = build(client, site, args.days, end=end, permits_csv=args.permits,
                         compare_prev=not args.no_compare)
        except gsc.GSCError as e:
            print(f"{site}: {e}", file=sys.stderr)
            rc = 1
            continue
        report, paths = write_out(data, args.out)
        print(report)
        print("\nWrote:\n  " + "\n  ".join(paths))
    return rc


if __name__ == "__main__":
    sys.exit(main())
