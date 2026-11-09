# Hosting Finding Mind on GitHub Pages, with several domains

## The constraint everything follows from

**GitHub Pages serves exactly one custom domain per site.** The `CNAME` file in the
repository holds a single hostname, and the Pages settings page has a single "Custom
domain" field. If you set `findingmind.io` on the repo, `findingmind.io` cannot also be
served from it.

So the shape is: **one canonical domain serves the site; every other domain 301-redirects
to it.** That is also what you want for search — several domains serving identical text is
duplicate content, and it splits whatever authority the site accumulates.

The canonical domain is **`findingmind.io`**. It is in the `CNAME` file, the `<link
rel="canonical">` tags, `robots.txt` and `sitemap.xml`, and `_build/build.sh` writes it
by default. Steps 1–3 below are done and kept for the record; steps 5–7 are the DNS and
organisation-level settings that have to stay in place.

---

## Step 1 — Make a dedicated repository (done: `F1R3FLY-io/findingmind`)

Put the book in its own repo rather than in `f1r3lang-io.github.io/finding-mind/`.

Two reasons. First, a custom domain applies to the whole Pages site, so attaching
`findingmind.io` to the existing repo would put the book at
`findingmind.io/finding-mind/` rather than at the root, and would hand that domain to a
repo full of unrelated design comps. Second, `F1R3FLY-io/f1r3lang-io.github.io` is a
*project* repo, not an organization site — an org site would have to be named
`f1r3fly-io.github.io` — so its Pages URL is already awkward.

```bash
gh repo create F1R3FLY-io/findingmind --public
git clone https://github.com/F1R3FLY-io/findingmind.git
cd findingmind
```

## Step 2 — Generate the build in place (done)

The generator lives in `_build/` and writes the site into the **root** of the repo, so
that `index.html` sits next to `read/`, `book.css`, `katex/` and `figures/`. See
"Rebuilding when a new draft lands" below.

`.nojekyll` is already there and matters: without it GitHub runs Jekyll, which ignores
directories beginning with an underscore, and `_build/` would silently vanish. It also
makes deploys faster and stops Jekyll interpreting any `{{ }}` that appears in the text.

The generator in `_build/` is published along with the site; it is small and harmless
where it is. Earlier full-site snapshots (`v1`–`v5`) were removed from the published tree
and are kept under the git tag `site-archive-v1-v5`.

## Step 3 — Turn on Pages

Settings → Pages → Build and deployment → **Deploy from a branch** → `main` → `/ (root)`.

Wait for the green check, then confirm at `https://f1r3fly-io.github.io/findingmind/`
that it renders. Do this before touching DNS, so that if something is wrong you know it is
the site and not the domain.

## Step 4 — Set the canonical domain (done: `findingmind.io`)

`_build/build.sh` runs the finalizer for `findingmind.io` after every generation. To
finalize for a different domain by hand:

```bash
python3 deploy/finalize.py findingmind.io --site findingmind   # run from the parent directory
```

It rewrites `CNAME`, the `<link rel="canonical">` tag on every page, `robots.txt` and
`sitemap.xml`, and is idempotent. Rebuild, then finalize, then push.

Then Settings → Pages → Custom domain → enter the same domain → Save. GitHub will read the
`CNAME` file you already committed and agree with it.

## Step 5 — DNS for the canonical domain

At the registrar for your canonical domain, delete any parking or default A records first,
then add:

| Type | Host | Value |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| AAAA | `@` | `2606:50c0:8000::153` |
| AAAA | `@` | `2606:50c0:8001::153` |
| AAAA | `@` | `2606:50c0:8002::153` |
| AAAA | `@` | `2606:50c0:8003::153` |
| CNAME | `www` | `f1r3fly-io.github.io.` |

Add both the apex and `www` — GitHub redirects between them once both exist. If your DNS
provider supports ALIAS or ANAME at the apex, you can use a single
`@ → f1r3fly-io.github.io` record instead of the eight A/AAAA records; it survives IP
changes.

Do **not** use a wildcard `*` record. GitHub warns about this specifically: a wildcard
exposes you to subdomain takeover even on a verified domain.

Check propagation, then tick **Enforce HTTPS** in Settings → Pages. The certificate is
issued automatically but can take fifteen minutes to a day; the checkbox stays greyed out
until it lands.

```bash
dig findingmind.io +noall +answer -t A
dig www.findingmind.io +noall +answer -t CNAME
```

If you already have a CAA record on the domain, it must permit `letsencrypt.org` or the
certificate will never issue.

## Step 6 — The other domains

Three ways, best first.

### A. Cloudflare redirect rules — recommended

Move each mirror domain's nameservers to Cloudflare (free plan), then for each one:

1. DNS → add a proxied `AAAA` record, `@` → `100::` (the documented discard address), and
   the same for `www`. Cloudflare needs a record to exist before a rule can fire; the
   traffic never reaches it.
2. Rules → Redirect Rules → Create.
   - When incoming requests match: **All incoming requests**
   - Then: **Dynamic** redirect, status **301**, expression
     `concat("https://findingmind.io", http.request.uri.path)`
   - Preserve query string: on.

That gives a real server-side 301 with a free certificate, it preserves deep links, and it
costs nothing. Repeat per domain; it's about two minutes each.

### B. Registrar URL forwarding

Most registrars offer "URL forwarding" or "domain redirect". Set each mirror to forward to
`https://findingmind.io` with a **permanent (301)** redirect and, if offered, **path
forwarding** on. Simplest option, but quality varies by registrar — some only do 302,
some only forward the bare domain and drop the path, and a few use an HTML frame, which
you do not want.

### C. Redirector repos on GitHub

If you want everything to stay on GitHub:

```bash
python3 deploy/make-redirectors.py findingmind.io findingmind.io findingmind.org findingmind.net
```

This writes `deploy/redirectors/<domain>/` for each mirror, containing an `index.html`, a
`404.html`, and a `CNAME`. Each directory becomes its own tiny public repo with Pages on
and its own custom domain, and GitHub issues each a certificate. The redirect page carries
`rel=canonical`, `noindex`, a meta refresh and a JS `location.replace` that preserves the
path, so `findingmind.io/read/ledger.html` still lands correctly.

The catch: it is a client-side redirect, not a 301. Search engines handle it, but less
cleanly than A or B. Use it only if you'd rather not put Cloudflare in front of anything.

Each mirror still needs the same DNS records as step 5 — pointed at whichever redirector
repo serves it.

## Step 7 — Verify the domains at the organisation level

Organisation settings → Pages → **Add a domain**. GitHub gives you a `TXT` record to add
at `_github-pages-challenge-f1r3fly-io.<domain>`. Do this for every domain including the
mirrors.

This is not optional housekeeping. Without verification, if a domain is ever removed from
its repo, anyone else on GitHub can claim it and serve their content on your hostname.

---

## Rebuilding when a new draft lands

The book source is the `FindingMind/` directory of `F1R3FLY-io/publications`, which is a
baseline plus the `draftN/` (and `draftN/src/`) delta directories. Assemble the current
book first — copy the baseline somewhere, then copy each `draftN/{,src/}*.tex` over it in
`sort -V` order, placing `pledge_*` in `ThePledge/`, `turn_*` in `TheTurn/`, `prestige_*`
in `ThePrestige/`, `int_*` in `Interludes/`, `*.rho` in `TheTurn/code/`, and
`finding_mind.tex`/`bibliography.tex` at the top — and point the build at it:

```bash
_build/build.sh /path/to/assembled/FindingMind      # domain defaults to findingmind.io
git add -A && git commit -m "site: draftNN" && git push
```

`build.sh` sets `FM_BOOK`/`FM_OUT`/`FM_WORK` for `_build/gen.py`, renders the TikZ figures
to SVG (needs `pdflatex` and `pdftocairo`), writes `read/`, `figures/`, `macros.js` and
`index.html`, then runs the finalizer. The landing-page and contents counts (chapters,
words, numbered results, cross-references) are computed from the source, not typed in.
Pages redeploys in a minute or two.

The comment form in `read/contact.html` posts to the FormSubmit endpoint named in
`_build/contact.py`. Until `FORM_ENDPOINT` carries a real FormSubmit hash (activate once by
posting to `https://formsubmit.co/<address>` and confirming the email they send), the form
falls through to a plain POST that will fail, and the page shows the mailto fallback.

## Things worth knowing about the limits

- Soft limits: 1 GB per repository, 100 GB bandwidth per month, ten builds per hour. The
  site is 8.6 MB, so none of these will bite.
- 4.3 MB of that is the SVG figures, which compress to roughly a fifth over the wire.
- GitHub Pages sets its own cache headers and you cannot change them; there is no
  server-side redirect, no `.htaccess`, and no way to serve two domains from one repo.
  If you ever need any of those, Cloudflare Pages or Netlify will take the same static
  directory unchanged and will serve several domains from one deployment.

## Two decisions this forces

**Which domain is canonical.** It is the one that appears in every search result, every
citation, and every link anyone shares for the life of the book. `.com` is the safe
default; if the book is going to read as a research artifact rather than a trade book,
`.org` is defensible.

**Whether the mirrors redirect to the root or to matching paths.** The setup above
redirects `findingmind.io/read/ledger.html` to `findingmind.io/read/ledger.html`.
The alternative — sending everything to the front page — is simpler but breaks any deep
link that ever gets shared on a mirror. Path-preserving is the right default.
