#!/usr/bin/env python3
"""
make-renamed-redirects.py — after a rebuild renumbers chapters, write redirect
stubs at the old chapter URLs so links already in the wild keep working.

    python3 deploy/make-renamed-redirects.py          # run from the repo root

It looks at the chapter pages git reports as deleted under read/, matches each
to the new page with the same title slug (falling back to the longest shared
prefix), and writes a small noindex page that forwards to it, preserving the
fragment. deploy/finalize.py skips these stubs when it builds the sitemap.
Anything it cannot match is printed for you to handle by hand.
"""
import os, re, subprocess

STUB = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Moved · Finding Mind</title><meta name="robots" content="noindex">
<link rel="canonical" href="https://findingmind.io/read/{t}">
<meta http-equiv="refresh" content="0; url={t}">
<script>location.replace("{t}"+location.hash)</script></head>
<body><p>This chapter has moved to <a href="{t}">{t}</a>.</p></body></html>
"""

def stem(f):
    return re.sub(r"^\d+-", "", f)

def main():
    st = subprocess.check_output(["git", "status", "--short", "read"]).decode().splitlines()
    old = [l[3:] for l in st if l[:2].strip() == "D"]
    new = [f for f in os.listdir("read") if f.endswith(".html")]
    bystem = {}
    for f in new:
        bystem.setdefault(stem(f), f)
    made, miss = 0, []
    for o in old:
        b = os.path.basename(o)
        t = bystem.get(stem(b))
        if not t:
            c = max(new, key=lambda f: len(os.path.commonprefix([stem(f), stem(b)])))
            if len(os.path.commonprefix([stem(c), stem(b)])) >= 12:
                t = c
        if not t:
            miss.append(b); continue
        open(os.path.join("read", b), "w").write(STUB.replace("{t}", t))
        made += 1
    print("redirect stubs written:", made)
    if miss:
        print("unmatched (write by hand):", ", ".join(miss))

if __name__ == "__main__":
    main()
