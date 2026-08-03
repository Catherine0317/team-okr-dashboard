#!/usr/bin/env python3
"""Assemble the dashboard HTML from data/*.json using the generator.
The generator (gen_kpi_html4.py) reads /tmp/*.json and writes /tmp/team_kpi_dash.html,
so we stage data/ -> /tmp, run it, and copy the result to public/index.html."""
import os, shutil, subprocess, sys, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
GEN  = os.path.join(ROOT, "pipeline", "gen_kpi_html4.py")
OUT  = os.path.join(ROOT, "public", "index.html")

for fn in os.listdir(DATA):
    if fn.endswith(".json"):
        shutil.copy(os.path.join(DATA, fn), os.path.join("/tmp", fn))

subprocess.run([sys.executable, GEN], check=True)
shutil.copy("/tmp/team_kpi_dash.html", OUT)

# sanity: syntax-check the embedded script
html = open(OUT).read()
js = re.search(r"<script>(.*?)</script>", html, re.S).group(1)
open("/tmp/_check.js", "w").write(js)
r = subprocess.run(["node", "--check", "/tmp/_check.js"])
if r.returncode != 0:
    sys.exit("node --check failed on generated HTML")
print(f"built {OUT} ({len(html)} bytes)")
