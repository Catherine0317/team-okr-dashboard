# Team OKR Dashboard — auto-refresh pipeline

Weekly rebuild + Vercel deploy of the Team OKR Dashboard, run by GitHub Actions
(no local bridge needed). Live: https://team-okr-dashboard-nine.vercel.app

## How it works
`.github/workflows/refresh.yml` runs every **Tuesday 07:07 America/Los_Angeles** (and on manual
"Run workflow"):
1. `pipeline/pull_supabase.py` — refresh Supabase-sourced data (direct Postgres, no MCP).
2. `pipeline/pull_lark.py` — *(phase 2)* refresh roster + feature-adoption/binding via a Lark app.
3. `pipeline/build.py` — assemble `public/index.html` via `pipeline/gen_kpi_html4.py`.
4. Commit refreshed `data/` + deploy `public/` to Vercel.

`data/*.json` are the per-brand snapshots the generator consumes; the pull scripts overwrite them.

## Required GitHub secrets
`Settings → Secrets and variables → Actions → New repository secret`:
| Secret | What | Where to get it |
|---|---|---|
| `SUPABASE_PG_URL` | Postgres connection URI (read-only role ideal) | Supabase → Project Settings → Database → Connection string (URI) |
| `VERCEL_TOKEN` | Vercel deploy token | vercel.com/account/tokens (scope: nextwave-talent) |
| `LARK_APP_ID` / `LARK_APP_SECRET` | *(phase 2)* Lark custom app | open.larksuite.com → Developer console |

## Status
- ✅ v1: Supabase refresh (top-20 videos) + build + Vercel deploy, on schedule.
- ⏳ phase 2: full per-brand GMV / affiliate-video / L3+ metrics in `pull_supabase.py`;
  roster + feature-adoption/binding via `pull_lark.py`. Cross-tenant ByteDance tabs
  (Smart Promotion / SnS / SPS) need mirroring or a stored user token.
- GMV **goal** comes from a forecast workbook — committed manually until wired.

## Local build
```
pip install "psycopg[binary]"
python pipeline/build.py       # rebuild public/index.html from data/
```
