#!/usr/bin/env python3
"""
finalize.py — prepare the built site for a specific canonical domain.

    python3 deploy/finalize.py findingmind.com [--site finding-mind]

Writes, into the site directory:
  CNAME          the one hostname GitHub Pages will serve
  .nojekyll      stops Jekyll touching the output (needed: _build/ starts with _)
  404.html       a real not-found page
  robots.txt     points crawlers at the sitemap
  sitemap.xml    every page, so the book is indexable
and inserts <link rel="canonical"> into every HTML page, so the mirror
domains cannot compete with the canonical one in search results.

Re-run it after every rebuild. It is idempotent.
"""
import os, re, sys, html, datetime

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        sys.exit(1)
    domain = args[0].strip().lower().rstrip("/")
    site = "finding-mind"
    if "--site" in sys.argv:
        site = sys.argv[sys.argv.index("--site") + 1]
    if not os.path.isdir(site):
        sys.exit("no such directory: %s" % site)

    base = "https://%s" % domain

    open(os.path.join(site, "CNAME"), "w").write(domain + "\n")
    open(os.path.join(site, ".nojekyll"), "w").write("")

    pages = []
    for root, dirs, files in os.walk(site):
        dirs[:] = [d for d in dirs if d not in ("_build", "katex", "figures", ".git")]
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(root, f))

    today = datetime.date.today().isoformat()
    urls = []
    for p in sorted(pages):
        rel = os.path.relpath(p, site).replace(os.sep, "/")
        if rel == "404.html":
            continue
        url = base + "/" + ("" if rel == "index.html" else rel)
        urls.append(url)
        t = open(p, encoding="utf-8").read()
        t = re.sub(r'\n?<link rel="canonical"[^>]*>', "", t)
        tag = '\n<link rel="canonical" href="%s">' % html.escape(url)
        t = t.replace("</title>", "</title>" + tag, 1)
        open(p, "w", encoding="utf-8").write(t)

    open(os.path.join(site, "sitemap.xml"), "w").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join('  <url><loc>%s</loc><lastmod>%s</lastmod></url>\n'
                  % (html.escape(u), today) for u in urls)
        + "</urlset>\n")

    open(os.path.join(site, "robots.txt"), "w").write(
        "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % base)

    open(os.path.join(site, "404.html"), "w").write(NOTFOUND.replace("{{BASE}}", base))

    print("canonical domain : %s" % domain)
    print("pages canonicalised: %d" % len(urls))
    print("wrote CNAME, .nojekyll, 404.html, robots.txt, sitemap.xml")


NOTFOUND = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Not found \u00b7 Finding Mind</title>
<link rel="icon" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..600&display=swap">
<link rel="stylesheet" href="/book.css">
</head>
<body class="plainpage">
<div class="page">
<header class="phead"><a class="back" href="/">Finding Mind</a>
<h1>That page is not here</h1>
<p class="lede">The book is still being written, so chapters move. The contents list is
always current.</p></header>
<ul class="links" style="max-width:34rem">
  <li><a href="/read/contents.html">Contents</a></li>
  <li><a href="/read/ledger.html">The ledger \u2014 every numbered result</a></li>
  <li><a href="/">The front page</a></li>
</ul>
</div>
</body>
</html>
"""

if __name__ == "__main__":
    main()
