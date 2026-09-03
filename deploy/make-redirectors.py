#!/usr/bin/env python3
"""
make-redirectors.py — build one tiny GitHub Pages site per mirror domain.

    python3 deploy/make-redirectors.py findingmind.com findingmind.io findingmind.org findingmind.net

The first argument is the CANONICAL domain. Every other argument gets its own
directory under deploy/redirectors/<domain>/ containing an index.html and a
CNAME. Each of those directories becomes its own one-file GitHub repository
with Pages turned on, and GitHub issues it a free certificate.

Use this only if you want everything to stay on GitHub. A 301 at the DNS
provider (Cloudflare Redirect Rules, or your registrar's URL forwarding) is
better, because it is a real server-side 301 rather than a client-side hop.
"""
import os, sys, html

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Finding Mind</title>
<link rel="canonical" href="https://{canon}/">
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0; url=https://{canon}/">
<script>
  // preserve the path and query, so deep links to the mirror still land right
  location.replace("https://{canon}" + location.pathname + location.search + location.hash);
</script>
<style>
  body{{background:#14100a;color:#e6dcc0;font:400 18px/1.6 Georgia,serif;
        margin:0;display:grid;place-items:center;min-height:100vh;text-align:center}}
  a{{color:#b98d2f}}
</style>
</head>
<body>
<p>Finding Mind now lives at <a href="https://{canon}/">{canon}</a>.</p>
</body>
</html>
"""


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    canon = args[0].strip().lower()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "redirectors")
    for d in args[1:]:
        d = d.strip().lower()
        p = os.path.join(out, d)
        os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "index.html"), "w").write(
            PAGE.format(canon=html.escape(canon)))
        open(os.path.join(p, "CNAME"), "w").write(d + "\n")
        open(os.path.join(p, ".nojekyll"), "w").write("")
        open(os.path.join(p, "404.html"), "w").write(
            PAGE.format(canon=html.escape(canon)))
        print("built", p)
    print("\nEach directory is a separate repo. For each one:")
    print("  gh repo create F1R3FLY-io/redirect-<name> --public --source . --push")
    print("  then Settings > Pages > Deploy from branch: main / (root)")
    print("  then Settings > Pages > Custom domain: the domain in its CNAME file")


if __name__ == "__main__":
    main()
