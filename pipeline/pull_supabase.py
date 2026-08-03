#!/usr/bin/env python3
"""Refresh Supabase-sourced data via the Supabase Management API (SQL over HTTPS).
No database password / no psycopg — just a Personal Access Token.

Env:
  SUPABASE_ACCESS_TOKEN   Supabase PAT (sbp_...) from https://supabase.com/dashboard/account/tokens
  SUPABASE_PROJECT_REF    project ref (default: qiorojsrqguemncypfhs)
  MONTH / YEAR            report month/year (default: current)

v1 refreshes data/top20.json (per-brand top-20 affiliate videos by month GMV).
"""
import os, json, re, datetime, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
now  = datetime.date.today()
MONTH = int(os.environ.get("MONTH", now.month))
YEAR  = int(os.environ.get("YEAR", now.year))
REF   = os.environ.get("SUPABASE_PROJECT_REF", "qiorojsrqguemncypfhs")
TOKEN = os.environ["SUPABASE_ACCESS_TOKEN"]
API   = f"https://api.supabase.com/v1/projects/{REF}/database/query"

def nb(s): return re.sub(r"[^a-z0-9]", "", (s or "").lower())
def sql_str(s): return "'" + str(s).replace("'", "''") + "'"

def run_sql(sql):
    req = urllib.request.Request(
        API, method="POST", data=json.dumps({"query": sql}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Management API error {e.code}: {e.read().decode()[:300]}")

def main():
    roster = json.load(open(os.path.join(DATA, "kpi_rows2.json")))
    brands = sorted({r["brand"] for r in roster})
    arr = "ARRAY[" + ",".join(sql_str(b) for b in brands) + "]"
    sql = f"""
    WITH d AS (
      SELECT DISTINCT ON (video_id, query_end_date) video_id, brand_name, username,
        video_product_ref_name product, list_gmv_amount::numeric gmv,
        overall_customers::numeric orders, list_views::numeric views
      FROM "WBR_Video_Auto"
      WHERE brand_name = ANY({arr}) AND account_type='AFFILIATE_ACCOUNTS'
        AND EXTRACT(MONTH FROM TO_DATE(query_end_date,'YYYY-MM-DD'))={MONTH}
        AND EXTRACT(YEAR  FROM TO_DATE(query_end_date,'YYYY-MM-DD'))={YEAR}
    ),
    pv AS (SELECT brand_name, video_id, max(username) username, max(product) product,
        round(sum(gmv))::int gmv, sum(orders)::int orders, sum(views)::bigint views
        FROM d GROUP BY brand_name, video_id),
    rk AS (SELECT *, (row_number() OVER (PARTITION BY brand_name ORDER BY gmv DESC))::int rn
        FROM pv WHERE gmv>0)
    SELECT brand_name, rn, video_id::text vid, username, product, gmv, orders, views
    FROM rk WHERE rn<=20 ORDER BY brand_name, rn;
    """
    rows = run_sql(sql)
    out = {}
    for r in rows:
        out.setdefault(nb(r["brand_name"]), []).append(
            [r["rn"], str(r["vid"]), r["username"], r["product"], r["gmv"], r["orders"], r["views"]])
    json.dump(out, open(os.path.join(DATA, "top20.json"), "w"), ensure_ascii=False)
    print(f"top20.json: {len(out)} brands, {sum(len(v) for v in out.values())} videos "
          f"(month {YEAR}-{MONTH:02d})")

if __name__ == "__main__":
    main()
