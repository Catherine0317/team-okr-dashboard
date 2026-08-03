#!/usr/bin/env python3
"""Refresh Supabase-sourced data (no MCP; direct Postgres via $PG_CONN).
v1 refreshes data/top20.json (per-brand top-20 affiliate videos by month GMV).
Extend here for GMV / affiliate-video / L3+ per-brand metrics.

Env:
  PG_CONN   Postgres connection URI (GitHub secret SUPABASE_PG_URL)
  MONTH     report month 1-12 (default: current month)
  YEAR      report year     (default: current year)
"""
import os, json, re, datetime, sys
try:
    import psycopg
except ImportError:
    sys.exit("psycopg not installed (pip install 'psycopg[binary]')")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
now = datetime.date.today()
MONTH = int(os.environ.get("MONTH", now.month))
YEAR  = int(os.environ.get("YEAR", now.year))
CONN  = os.environ["PG_CONN"]

def nb(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())

# active roster = brands currently in kpi_rows2.json
roster = json.load(open(os.path.join(DATA, "kpi_rows2.json")))
brands = sorted({r["brand"] for r in roster})

TOP20_SQL = """
WITH d AS (
  SELECT DISTINCT ON (video_id, query_end_date) video_id, brand_name, username,
    video_product_ref_name product, list_gmv_amount::numeric gmv,
    overall_customers::numeric orders, list_views::numeric views
  FROM "WBR_Video_Auto"
  WHERE brand_name = ANY(%(brands)s) AND account_type='AFFILIATE_ACCOUNTS'
    AND EXTRACT(MONTH FROM TO_DATE(query_end_date,'YYYY-MM-DD'))=%(m)s
    AND EXTRACT(YEAR  FROM TO_DATE(query_end_date,'YYYY-MM-DD'))=%(y)s
),
pv AS (SELECT brand_name, video_id, max(username) username, max(product) product,
    round(sum(gmv))::int gmv, sum(orders)::int orders, sum(views)::bigint views
    FROM d GROUP BY brand_name, video_id),
rk AS (SELECT *, row_number() OVER (PARTITION BY brand_name ORDER BY gmv DESC) rn
    FROM pv WHERE gmv>0)
SELECT brand_name, rn, video_id, username, product, gmv, orders, views
FROM rk WHERE rn<=20 ORDER BY brand_name, rn;
"""

def main():
    out = {}
    with psycopg.connect(CONN) as c, c.cursor() as cur:
        cur.execute(TOP20_SQL, {"brands": brands, "m": MONTH, "y": YEAR})
        for brand, rn, vid, user, prod, gmv, orders, views in cur.fetchall():
            out.setdefault(nb(brand), []).append(
                [rn, str(vid), user, prod, gmv, orders, views])
    json.dump(out, open(os.path.join(DATA, "top20.json"), "w"), ensure_ascii=False)
    print(f"top20.json: {len(out)} brands, {sum(len(v) for v in out.values())} videos "
          f"(month {YEAR}-{MONTH:02d})")

if __name__ == "__main__":
    main()
