#!/usr/bin/env python3
import os, re, json, html, shutil, sys
sys.path.insert(0, "/home/claude/build")
from convert import (ROOT, OUT, B, convert_file, parse_macros, parse_bib,
                     render_tikz, strip_comments, take_group, ROMAN)

READ = os.path.join(OUT, "read")

# ------------------------------------------------------------------ spine

def build_spine():
    src = strip_comments(open(os.path.join(ROOT, "finding_mind.tex")).read())
    body = src[src.index("\\begin{document}"):]
    spine = []
    act = None
    part = None
    partn = 0
    chapn = 0
    for m in re.finditer(r"\\(part\*?|input)\{([^}]*)\}", body):
        kind, arg = m.group(1), m.group(2)
        if kind.startswith("part"):
            star = kind.endswith("*")
            keys = []
            tail = body[m.end():m.end() + 400]
            off = 0
            while True:
                lm = re.match(r"\s*\\label\{([^}]*)\}", tail[off:])
                if not lm:
                    break
                keys.append(lm.group(1).strip()); off += lm.end()
            if arg in ("The Pledge", "The Turn", "The Prestige"):
                act = arg
                spine.append(dict(t="act", title=arg, keys=keys))
                part = None
                continue
            if not star:
                partn += 1
            part = arg
            spine.append(dict(t="part", title=arg, num=ROMAN[partn] if not star else "",
                              act=act, keys=keys))
            continue
        if arg.startswith("Interludes/"):
            spine.append(dict(t="interlude", path=arg + ".tex", act=act))
            continue
        if arg == "bibliography":
            continue
        p = arg + ".tex"
        if not os.path.exists(os.path.join(ROOT, p)):
            continue
        raw = open(os.path.join(ROOT, p)).read()
        star = bool(re.search(r"\\chapter\*", raw))
        if not star:
            chapn += 1
        spine.append(dict(t="chapter", path=p, num=(chapn if not star else None),
                          act=act, part=part))
    return spine


SLUG_FIX = {}

def slugify(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.lower()).strip("-")
    return s[:60]


# ------------------------------------------------------------------ chrome

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="color-scheme" content="light dark">
<link rel="icon" href="{root}favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{root}book.css">
{extra}
</head>
<body class="{bodyclass}">
"""

KATEX = """<link rel="stylesheet" href="{root}katex/katex.min.css">
<script defer src="{root}katex/katex.min.js"></script>
<script defer src="{root}katex/auto-render.min.js"></script>
<script defer src="{root}macros.js"></script>
<script defer src="{root}reader.js"></script>"""


def page(title, bodyclass, content, root="", desc="Finding Mind", math=False):
    extra = KATEX.replace("{root}", root) if math else ""
    return (HEAD.format(title=html.escape(title), desc=html.escape(desc),
                        root=root, extra=extra, bodyclass=bodyclass)
            + content + "\n</body>\n</html>\n")


# ------------------------------------------------------------------ main

def main():
    os.makedirs(READ, exist_ok=True)
    parse_macros()          # populates the text-mode macro table first
    render_tikz()
    parse_bib()
    spine = build_spine()

    # part / act labels resolve to the contents page
    for e in spine:
        for k in e.get("keys", []) or []:
            anc = "part-" + re.sub(r"[^a-z0-9]+", "-", e["title"].lower())[:40]
            B.labels[k] = dict(num=("Part " + e["num"]) if e.get("num") else e["title"],
                               kind="Part", title=e["title"],
                               url="contents.html", anchor=anc)

    # ---- pass 1: convert every file, collecting labels
    items = []
    for e in spine:
        if e["t"] in ("act", "part"):
            items.append(e)
            continue
        num = e.get("num")
        path = e["path"]
        base = os.path.basename(path)[:-4]
        if e["t"] == "interlude":
            slug = base.replace("int_", "").replace("_", "-")
        else:
            ttl = re.search(r"\\chapter\*?\s*\{", open(os.path.join(ROOT, path)).read())
            _t = take_group(open(os.path.join(ROOT, path)).read(), ttl.end() - 1)[0] if ttl else base
            slug = ("%02d-" % num if num else "") + slugify(_t)[:46].strip("-")
        url = slug + ".html"
        r = convert_file(path, num or 0, url)
        if e["t"] == "interlude":
            m = re.search(r"\\interludehead\{([^}]*)\}\{([^}]*)\}",
                          open(os.path.join(ROOT, path)).read())
            if m:
                e["kicker"] = m.group(1)
                r["title"] = m.group(2)
            else:
                r["title"] = base.replace("int_", "").replace("_", " ").title()
        e.update(r); e["slug"] = slug; e["url"] = url
        items.append(e)

    # ---- resolve refs
    def resolve(h):
        def sub(m):
            key = m.group(1)
            d = B.labels.get(key)
            if not d:
                return '<span class="xref-dead" title="unresolved: %s">%s</span>' % (key, key)
            label = d["num"] if d["num"] else d["title"]
            return ('<a class="xref" href="%s#%s" data-ref="%s">%s</a>'
                    % (d["url"], d["anchor"], html.escape(key), html.escape(str(label))))
        h = re.sub(r'<a class="xref" data-ref="([^"]*)" href="#">[^<]*</a>', sub, h)

        def csub(m):
            key = m.group(1)
            if key not in B.bib:
                return '<span class="xref-dead">%s</span>' % key
            n = B.bib[key][0]
            return '<a class="cite" href="bibliography.html#bib-%s" data-cite="%s">%d</a>' % (key, key, n)
        h = re.sub(r'<a class="cite" data-cite="([^"]*)" href="#">[^<]*</a>', csub, h)
        return h

    for e in items:
        if "body" in e:
            e["body"] = resolve(e["body"])

    chapters = [e for e in items if e["t"] in ("chapter", "interlude")]

    # ---- nav data
    nav = []
    for e in items:
        if e["t"] == "act":
            nav.append(dict(t="act", title=e["title"]))
        elif e["t"] == "part":
            nav.append(dict(t="part", title=e["title"], num=e.get("num", "")))
        else:
            nav.append(dict(t="ch", title=e["title"], num=e.get("num"),
                            url=e["url"], kind=e["t"], words=e["words"]))
    json.dump(nav, open(os.path.join(READ, "nav.json"), "w"))

    # ---- ledger
    RESULTS = {"Definition", "Theorem", "Proposition", "Lemma", "Corollary",
               "Remark", "Observation", "Conjecture", "Question", "Principle",
               "Construction", "Condition", "Requirement", "Example", "Non-example"}
    OWED = {"Conjecture", "Question"}
    chap_of = {e["url"]: (e.get("num"), e["title"]) for e in items
               if e["t"] in ("chapter", "interlude")}
    ledger = []
    for k, d in B.labels.items():
        if d["kind"] not in RESULTS:
            continue
        cn, ct = chap_of.get(d["url"], (None, ""))
        ledger.append(dict(key=k, kind=d["kind"], num=d["num"],
                           title=re.sub(r"<[^>]+>", "", d["title"] or ""),
                           url=d["url"], anchor=d["anchor"],
                           ch=cn, cht=ct, owed=d["kind"] in OWED))
    json.dump(ledger, open(os.path.join(READ, "ledger.json"), "w"))

    # ---- emit chapter pages
    for i, e in enumerate(chapters):
        prev = chapters[i-1] if i else None
        nxt = chapters[i+1] if i + 1 < len(chapters) else None
        e["prev"], e["next"] = prev, nxt
    for e in chapters:
        write_chapter(e, nav)

    write_contents(items)
    write_ledger()
    write_bibliography()
    write_landing(items)
    write_assets()
    print("chapters: %d   labels: %d   bib: %d   results: %d"
          % (len(chapters), len(B.labels), len(B.bib), len(ledger)))
    dead = len(re.findall("xref-dead", "".join(e.get("body", "") for e in items)))
    print("unresolved refs:", dead)


def railnav(nav, current=None):
    out = ['<nav class="rail" aria-label="Contents"><div class="rail-in">']
    out.append('<a class="rail-home" href="../index.html">Finding Mind</a>')
    for n in nav:
        if n["t"] == "act":
            out.append('<h2 class="rail-act">%s</h2>' % html.escape(n["title"]))
        elif n["t"] == "part":
            out.append('<h3 class="rail-part">%s</h3>' % html.escape(n["title"]))
        else:
            cur = ' aria-current="page"' if current == n["url"] else ""
            num = ('<span class="rn">%d</span>' % n["num"]) if n["num"] else '<span class="rn rn-i">\u2042</span>'
            out.append('<a class="rail-ch"%s href="%s">%s<span class="rt">%s</span></a>'
                       % (cur, n["url"], num, html.escape(n["title"])))
    out.append("</div></nav>")
    return "".join(out)


def write_chapter(e, nav):
    num = e.get("num")
    kicker = ""
    if e["t"] == "interlude":
        kicker = '<p class="kicker">Interlude</p>'
    elif num:
        kicker = '<p class="kicker">Chapter %d</p>' % num
    foot = '<nav class="pager">'
    if e["prev"]:
        foot += '<a class="prev" href="%s"><span>Previous</span>%s</a>' % (
            e["prev"]["url"], html.escape(e["prev"]["title"]))
    if e["next"]:
        foot += '<a class="next" href="%s"><span>Next</span>%s</a>' % (
            e["next"]["url"], html.escape(e["next"]["title"]))
    foot += "</nav>"
    content = f"""
<a class="skip" href="#main">Skip to text</a>
<div class="reader">
{railnav(nav, e['url'])}
<main id="main" class="text {'interlude' if e['t']=='interlude' else ''}">
<header class="chead">{kicker}<h1>{html.escape(e['title'])}</h1></header>
{e['body']}
{foot}
</main>
<aside class="margin" id="margin" aria-live="polite"></aside>
</div>
<button class="railtoggle" id="railtoggle" aria-expanded="false">Contents</button>
"""
    open(os.path.join(READ, e["url"]), "w").write(
        page(e["title"] + " \u00b7 Finding Mind", "readpage", content,
             root="../", desc=e["title"], math=True))


def write_contents(items):
    rows = []
    for e in items:
        if e["t"] == "act":
            anc = "part-" + re.sub(r"[^a-z0-9]+", "-", e["title"].lower())[:40]
            rows.append('<h2 class="toc-act" id="%s">%s</h2>' % (anc, html.escape(e["title"])))
        elif e["t"] == "part":
            n = e.get("num")
            anc = "part-" + re.sub(r"[^a-z0-9]+", "-", e["title"].lower())[:40]
            rows.append('<h3 class="toc-part" id="%s">%s%s</h3>'
                        % (anc, ('<span class="pn">Part %s</span>' % n) if n else "",
                           html.escape(e["title"])))
        elif e["t"] == "interlude":
            rows.append('<a class="toc-ch toc-int" href="%s"><span class="cn">\u2042</span>'
                        '<span class="ct">%s</span><span class="cw">%s</span></a>'
                        % (e["url"], html.escape(e["title"]),
                           html.escape(e.get("kicker", "Interlude").lower())))
        else:
            rows.append('<a class="toc-ch" href="%s"><span class="cn">%s</span>'
                        '<span class="ct">%s</span><span class="cw">%s words</span></a>'
                        % (e["url"], e["num"] or "", html.escape(e["title"]),
                           "{:,}".format(e["words"])))
    content = f"""
<div class="page">
<header class="phead"><a class="back" href="../index.html">Finding Mind</a>
<h1>Contents</h1>
<p class="lede">Sixty-eight numbered chapters, five unnumbered ones and four interludes,
in three acts. Everything below is the current draft, generated from the book's own
source.</p></header>
<div class="toc">{''.join(rows)}</div>
</div>"""
    open(os.path.join(READ, "contents.html"), "w").write(
        page("Contents \u00b7 Finding Mind", "plainpage", content, root="../"))


def write_ledger():
    content = """
<div class="page">
<header class="phead"><a class="back" href="../index.html">Finding Mind</a>
<h1>The ledger</h1>
<p class="lede">Every numbered result in the book, in one place. The book's own front
matter promises that nothing is hiding. This is where you check.</p>
<div class="filters">
  <input type="search" id="q" placeholder="Search by name, number or label" aria-label="Search results">
  <p class="owedline"><button id="owed" aria-pressed="false">Show only what the book still owes</button>
     <span id="count"></span></p>
  <div class="chips" id="chips"></div>
</div></header>
<div id="ledger" class="ledger"></div>
</div>
<script>
fetch('ledger.json').then(r=>r.json()).then(function(rows){
  var kinds=[...new Set(rows.map(r=>r.kind))].sort(function(a,b){
    return rows.filter(r=>r.kind===b).length - rows.filter(r=>r.kind===a).length; });
  var active=new Set(), owedOnly=false;
  var chips=document.getElementById('chips');
  kinds.forEach(function(k){
    var b=document.createElement('button');
    b.textContent=k+' '+rows.filter(r=>r.kind===k).length;
    b.setAttribute('aria-pressed','false');
    if(k==='Conjecture'||k==='Question') b.className='owedchip';
    b.onclick=function(){ if(active.has(k)){active.delete(k);b.setAttribute('aria-pressed','false');}
      else {active.add(k);b.setAttribute('aria-pressed','true');} draw(); };
    chips.appendChild(b);
  });
  var ob=document.getElementById('owed');
  ob.onclick=function(){ owedOnly=!owedOnly; ob.setAttribute('aria-pressed',owedOnly?'true':'false');
    ob.textContent = owedOnly ? 'Show everything' : 'Show only what the book still owes'; draw(); };
  var q=document.getElementById('q'); q.oninput=draw;
  function draw(){
    var term=q.value.toLowerCase();
    var out=rows.filter(function(r){
      if(owedOnly && !r.owed) return false;
      if(active.size && !active.has(r.kind)) return false;
      if(!term) return true;
      return (r.kind+' '+r.num+' '+r.title+' '+r.key+' '+r.cht).toLowerCase().indexOf(term)>=0;
    });
    document.getElementById('count').textContent = out.length + ' of ' + rows.length;
    document.getElementById('ledger').innerHTML = out.map(function(r){
      return '<a class="lrow'+(r.owed?' owed':'')+'" href="'+r.url+'#'+r.anchor+'">'+
        '<span class="lk">'+r.kind+'</span>'+
        '<span class="ln">'+r.num+'</span>'+
        '<span class="lt">'+(r.title? r.title : '<span class="unnamed">'+r.cht+'</span>')+'</span></a>';
    }).join('') || '<p class="empty">Nothing matches. Clear the filters to see everything.</p>';
  }
  draw();
});
</script>"""
    open(os.path.join(READ, "ledger.html"), "w").write(
        page("The ledger \u00b7 Finding Mind", "plainpage", content, root="../"))


def write_bibliography():
    rows = []
    for k, (n, h) in B.bib.items():
        rows.append('<li id="bib-%s"><span class="bn">%d</span><div>%s</div></li>' % (k, n, h))
    content = """
<div class="page">
<header class="phead"><a class="back" href="../index.html">Finding Mind</a>
<h1>Bibliography</h1></header>
<ol class="bib">%s</ol>
</div>""" % "".join(rows)
    open(os.path.join(READ, "bibliography.html"), "w").write(
        page("Bibliography \u00b7 Finding Mind", "plainpage", content, root="../", math=True))


# ------------------------------------------------------------------ landing

def write_landing(items):
    chs = [e for e in items if e["t"] == "chapter"]
    words = sum(e["words"] for e in items if "words" in e)
    first = next(e for e in items if e["t"] in ("chapter", "interlude"))
    acts = []
    for a, blurb in [("The Pledge", "What the book is going to do, said plainly, before it is done."),
                     ("The Turn", "The construction. A calculus, an ecology, a physics, and a population of learners who are all mortal."),
                     ("The Prestige", "How the trick was done, and what had to be assumed to do it.")]:
        parts = [e["title"] for e in items if e["t"] == "part" and e.get("act") == a]
        acts.append(dict(a=a, blurb=blurb, parts=parts))
    actrows = "".join(
        '<li><h3><a href="read/contents.html">%s</a></h3><p>%s</p><p class="parts">%s</p></li>'
        % (html.escape(x["a"]), x["blurb"], " \u00b7 ".join(html.escape(p) for p in x["parts"]))
        for x in acts)

    content = f"""
<a class="skip" href="#argument">Skip to the argument</a>

<header class="hero">
  <div class="hero-art">
    <img src="hero.jpg" width="738" height="981"
         alt="A stained-glass panel: a great host of small winged figures massed together, all
              looking up at a single red apple hanging from a branch, with a green serpent
              stretched along the branch above them.">
  </div>
  <div class="hero-type">
    <h1>Finding&nbsp;Mind</h1>
    <p class="sub">The Mortal Scientist and the Ecology of Thought</p>
    <p class="byline">Lucius Gregory Meredith</p>
    <p class="actions">
      <a class="go" href="read/{first['url']}">Start reading</a>
      <a class="alt" href="read/contents.html">Contents</a>
    </p>
    <p class="meta">Working draft \u00b7 {len(chs)} chapters \u00b7 {words//1000}k words \u00b7 free to read</p>
  </div>
</header>

<section id="argument" class="argument">
  <div class="col">
    <p class="lede">There are two events in the geologic record that have no explanation.
    The first is the transition from an Earth without life to an Earth with life. The
    second is the transition from an Earth without mind to an Earth with mind.</p>
    <p class="turn">This book argues they are the same event.</p>
    <p>Not a miracle, and not an accident. A fixed point. In the space of all known models
    of computation there are places the system cannot help but arrive at, and life and mind
    are two of them. The mechanism is reflection: the moment a process can quote itself,
    become its own location, and read itself back.</p>
    <p class="notation"><b>@P</b><span>a process, quoted, becomes a name</span>
       <b>*x</b><span>a name, dereferenced, becomes a process again</span></p>
    <p>What follows is not a metaphor. In a reflective calculus the rule that steps a
    computation forward is already the rule that recombines genetic material. Two forms
    meet at a name, each reads what the other carries, and both continue changed.</p>
    <p>There is no fitness function in the sky. A better word than <em>fit</em> is
    <em>responsible</em>: what persists is whatever can keep showing up and answering. And
    because bisimulation is the finest classification of program behavior there is, it is
    also the ceiling on what any machine can learn about another mind.</p>
  </div>
</section>

<section class="acts">
  <div class="col"><h2>Three acts</h2>
  <p>The book takes its shape from a magic trick, because the claim is that there is no trick.</p></div>
  <ol>{actrows}</ol>
</section>

<section class="apparatus">
  <div class="col">
    <h2>Reading a book with 1,800 cross-references</h2>
    <p>The print draft carries seven hundred numbered definitions, propositions, remarks and
    conjectures, and refers back to them constantly. On paper that means keeping a finger in
    four places at once. Here it does not.</p>
  </div>
  <ul class="feat">
    <li><h3>References open where you are</h3><p>Every reference to a numbered result
      shows that result in the margin without moving you off the page.</p></li>
    <li><h3>Every result has an address</h3><p>Definitions, theorems and remarks each have
      a permanent link, so a claim can be cited and argued with directly.</p></li>
    <li><h3><a href="read/ledger.html">The ledger</a></h3><p>All seven hundred results in one
      searchable list, including the ones the book itself marks as unproved.</p></li>
  </ul>
</section>

<section class="elsewhere">
  <div class="col"><h2>Elsewhere</h2></div>
  <div class="cols">
    <div>
      <h3>Essays</h3>
      <ul class="links">
        <li><a href="https://f1r3fly.io/articles/finding-mind-update-computation.html">Why the origin of mind requires updating our definition of computation</a></li>
        <li><a href="https://f1r3fly.io/articles/pledge-part-i-compositionality-blind-spot.html">Compositionality as a blind spot</a></li>
        <li><a href="https://f1r3fly.io/articles/finding-mind-iii-interlude.html">An interlude to catch our breath</a></li>
      </ul>
    </div>
    <div>
      <h3>Talks</h3>
      <ul class="links">
        <li><a href="https://youtu.be/CtB5RRPFzZA">Part I: The Pledge</a></li>
        <li><a href="https://youtu.be/byUG2EVVFFI">Part II: The Turn</a></li>
        <li><a href="https://youtu.be/UjVuyRK7cG4">Part III: The Prestige</a></li>
      </ul>
    </div>
  </div>
</section>

<footer class="foot">
  <div class="col">
    <p>New chapters and essays appear as they are written.
       <a href="https://f1r3fly.substack.com/">Follow along</a>.</p>
  </div>
</footer>
"""
    open(os.path.join(OUT, "index.html"), "w").write(
        page("Finding Mind \u2014 Lucius Gregory Meredith", "home", content, root="",
             desc="Finding Mind, by Lucius Gregory Meredith. How the origin of mind "
                  "recapitulates the origin of life. The full draft, free to read."))


def write_assets():
    macros = parse_macros()
    open(os.path.join(OUT, "macros.js"), "w").write(
        "window.BOOK_MACROS = " + json.dumps(macros, indent=0) + ";\n")
    shutil.copy("/home/claude/assets/hero-full.jpg", os.path.join(OUT, "hero.jpg"))
    for name in ["book.css", "reader.js", "favicon.svg"]:
        shutil.copy(os.path.join("/home/claude/build/static", name),
                    os.path.join(OUT, name))
    kt = os.path.join(OUT, "katex")
    if os.path.exists(kt):
        shutil.rmtree(kt)
    shutil.copytree("/home/claude/build/static/katex", kt)


if __name__ == "__main__":
    main()
