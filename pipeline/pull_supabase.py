#!/usr/bin/env python3
"""Refresh Supabase-sourced data via the Data API (PostgREST) — no DB password.
Uses the project's secret API key ($SUPABASE_API_KEY, the `sb_secret_...` value)
which authorizes table reads over HTTPS. Aggregation (dedupe/sum/top-N) is done
in Python since PostgREST can't do window functions.

Env:
  SUPABASE_API_KEY       project secret API key (sb_secret_...)
  SUPABASE_PROJECT_REF   project ref (default: qiorojsrqguemncypfhs)
  MONTH / YEAR           report month/year (default: current)

v1 refreshes data/top20.json (per-brand top-20 affiliate videos by month GMV).
"""
import os, json, re, datetime, sys, urllib.request, urllib.parse, urllib.error, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
now  = datetime.date.today()
MONTH = int(os.environ.get("MONTH", now.month))
YEAR  = int(os.environ.get("YEAR", now.year))
REF   = os.environ.get("SUPABASE_PROJECT_REF", "qiorojsrqguemncypfhs")
KEY   = os.environ["SUPABASE_API_KEY"]
BASE  = f"https://{REF}.supabase.co/rest/v1"

first = datetime.date(YEAR, MONTH, 1)
nxt   = datetime.date(YEAR + (MONTH // 12), (MONTH % 12) + 1, 1)  # first of next month

def nb(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

def fetch_all(table, params, page=1000):
    rows, offset = [], 0
    while True:
        q = dict(params); q["limit"] = page; q["offset"] = offset
        q.setdefault("order", "video_id.asc,query_end_date.asc,list_gmv_amount.asc")
        url = f"{BASE}/{table}?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={
            "apikey": KEY, "Authorization": f"Bearer {KEY}"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                batch = json.load(r)
        except urllib.error.HTTPError as e:
            sys.exit(f"Data API error {e.code}: {e.read().decode()[:300]}")
        rows.extend(batch)
        if len(batch) < page:
            return rows
        offset += page

def main():
    roster = json.load(open(os.path.join(DATA, "kpi_rows2.json")))
    keep = {nb(r["brand"]) for r in roster}

    rows = fetch_all("WBR_Video_Auto", {
        "account_type": "eq.AFFILIATE_ACCOUNTS",
        "list_gmv_amount": "gt.0",
        "query_end_date": f"gte.{first.isoformat()}",
        "select": "brand_name,video_id,query_end_date,username,"
                  "video_product_ref_name,list_gmv_amount,overall_customers,list_views",
    })
    rows = [x for x in rows if x["query_end_date"] < nxt.isoformat()]

    # dedupe (video_id, query_end_date), then sum per (brand, video)
    seen = set()
    agg = collections.defaultdict(lambda: {"gmv": 0.0, "orders": 0.0, "views": 0.0,
                                           "user": None, "prod": None, "brand": None})
    for x in rows:
        b = nb(x["brand_name"])
        if b not in keep:
            continue
        k = (x["video_id"], x["query_end_date"])
        if k in seen:
            continue
        seen.add(k)
        a = agg[(b, x["video_id"])]
        a["gmv"]    += float(x["list_gmv_amount"] or 0)
        a["orders"] += float(x["overall_customers"] or 0)
        a["views"]  += float(x["list_views"] or 0)
        a["user"], a["prod"], a["brand"] = x["username"], x["video_product_ref_name"], b

    by_brand = collections.defaultdict(list)
    for (b, vid), a in agg.items():
        by_brand[b].append((round(a["gmv"]), int(a["orders"]), int(a["views"]),
                            a["user"], a["prod"], vid))

    out = {}
    for b, vids in by_brand.items():
        vids.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)  # gmv, orders, views
        out[b] = [[i + 1, vid, user, prod, gmv, orders, views]
                  for i, (gmv, orders, views, user, prod, vid) in enumerate(vids[:20])]

    json.dump(out, open(os.path.join(DATA, "top20.json"), "w"), ensure_ascii=False)
    print(f"top20.json: {len(out)} brands, {sum(len(v) for v in out.values())} videos "
          f"({first} .. {nxt})")

if __name__ == "__main__":
    main()
