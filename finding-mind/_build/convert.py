#!/usr/bin/env python3
"""
finding-mind: LaTeX -> HTML

Purpose-built for FindingMind/finding_mind.tex and its 89 chapter files.
Two stages:
  1. convert each .tex to an HTML fragment, emitting <a data-ref="key"> stubs
     and recording label -> (number, kind, title, url)
  2. resolve every stub globally

Math is NOT expanded. It is passed through verbatim inside \( \) / \[ \] and
rendered client-side by KaTeX with the book's own 167 macros supplied as a
macro table. This is why the pipeline is robust: no macro reimplementation.
"""
import re, os, json, html, sys, hashlib, subprocess, shutil
from collections import OrderedDict

ROOT = "/home/claude/book"
OUT  = "/home/claude/site-out"
FIGDIR = os.path.join(OUT, "figures")

# ---------------------------------------------------------------- utilities

def strip_comments(t):
    out = []
    for line in t.split("\n"):
        i = 0; res = ""
        while i < len(line):
            c = line[i]
            if c == "\\" and i + 1 < len(line):
                res += line[i:i+2]; i += 2; continue
            if c == "%":
                break
            res += c; i += 1
        out.append(res)
    return "\n".join(out)


def match_brace(s, i):
    """s[i] must be '{'. return index just past matching '}'."""
    assert s[i] == "{"
    d = 0
    while i < len(s):
        if s[i] == "\\":
            i += 2; continue
        if s[i] == "{": d += 1
        elif s[i] == "}":
            d -= 1
            if d == 0:
                return i + 1
        i += 1
    return len(s)


def take_group(s, i):
    """read optional whitespace then a {..} group at i; return (content, next_i)"""
    j = i
    while j < len(s) and s[j] in " \n\t":
        j += 1
    if j < len(s) and s[j] == "{":
        e = match_brace(s, j)
        return s[j+1:e-1], e
    return "", i


def take_opt(s, i):
    j = i
    while j < len(s) and s[j] in " \t":
        j += 1
    if j < len(s) and s[j] == "[":
        d = 0
        k = j
        while k < len(s):
            if s[k] == "[": d += 1
            elif s[k] == "]":
                d -= 1
                if d == 0:
                    return s[j+1:k], k + 1
            k += 1
    return None, i


def find_env(t, name, start=0):
    b = "\\begin{%s}" % name
    e = "\\end{%s}" % name
    i = t.find(b, start)
    if i < 0:
        return None
    depth = 0
    k = i
    while k < len(t):
        nb = t.find(b, k); ne = t.find(e, k)
        if ne < 0:
            return (i, len(t), len(t))
        if nb >= 0 and nb < ne:
            depth += 1; k = nb + len(b)
        else:
            depth -= 1
            if depth == 0:
                return (i, ne, ne + len(e))
            k = ne + len(e)
    return (i, len(t), len(t))


# ---------------------------------------------------------------- state

class Book:
    def __init__(self):
        self.labels = OrderedDict()      # key -> dict(num, kind, title, page, anchor)
        self.parts = []
        self.chapters = []               # dicts
        self.bib = OrderedDict()         # key -> (index, html)
        self.figures = 0
        self.tikz = {}                   # hash -> svg filename

B = Book()
MATH_MACROS = set()

ROMAN = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI",
         "XII", "XIII", "XIV", "XV"]

THEOREMS = {
    "definition": "Definition", "theorem": "Theorem", "proposition": "Proposition",
    "remark": "Remark", "example": "Example", "construction": "Construction",
    "conjecture": "Conjecture", "condition": "Condition", "requirement": "Requirement",
    "nonexample": "Non-example", "lemma": "Lemma", "corollary": "Corollary",
    "observation": "Observation", "principle": "Principle", "question": "Question",
}
PLAIN_STYLE = {"definition", "theorem", "proposition", "lemma", "corollary",
               "principle", "construction", "conjecture", "condition",
               "requirement", "example", "nonexample", "question"}

LISTLIKE = ["itemize", "enumerate", "description"]


# ---------------------------------------------------------------- inline

INLINE_SIMPLE = [
    (r"\\emph\s*", "em"), (r"\\textit\s*", "em"), (r"\\textbf\s*", "strong"),
    (r"\\texttt\s*", "code"), (r"\\textsc\s*", "span class=\"sc\""),
    (r"\\underline\s*", "u"),
]


def inline(s, ctx):
    """convert inline LaTeX in a text run (math already extracted)."""
    # font/structure commands with one argument
    def repl_cmd(name, tag, cls=None):
        nonlocal s
        out = ""
        i = 0
        pat = "\\" + name
        while True:
            j = s.find(pat, i)
            if j < 0:
                out += s[i:]; break
            # must not be a longer command name
            k = j + len(pat)
            if k < len(s) and (s[k].isalpha()):
                out += s[i:k]; i = k; continue
            body, nx = take_group(s, k)
            if nx == k:
                out += s[i:k]; i = k; continue
            out += s[i:j] + "<%s%s>" % (tag, (' class="%s"' % cls) if cls else "") \
                   + body + "</%s>" % tag
            i = nx
        s = out

    for name, tag, cls in [("emph", "em", None), ("textit", "em", None),
                           ("textsl", "em", None),
                           ("textbf", "strong", None), ("texttt", "code", None),
                           ("textsc", "span", "sc"), ("underline", "u", None),
                           ("term", "em", None)]:
        repl_cmd(name, tag, cls)

    # cross references ------------------------------------------------------
    def ref_sub(m):
        keys = m.group(1)
        parts = []
        for k in keys.split(","):
            k = k.strip()
            parts.append('<a class="xref" data-ref="%s" href="#">%s</a>' % (html.escape(k), html.escape(k)))
        return ", ".join(parts)
    s = re.sub(r"\\(?:auto|eq|c)?ref\{([^}]*)\}", ref_sub, s)
    s = re.sub(r"\\pageref\{[^}]*\}", "", s)

    def cite_sub(m):
        keys = [k.strip() for k in m.group(2).split(",")]
        extra = m.group(1)
        out = []
        for k in keys:
            out.append('<a class="cite" data-cite="%s" href="#">%s</a>' % (html.escape(k), html.escape(k)))
        txt = ", ".join(out)
        if extra:
            txt += ", " + html.escape(extra)
        return "[" + txt + "]"
    s = re.sub(r"\\cite(?:\[([^\]]*)\])?\{([^}]*)\}", cite_sub, s)

    # footnotes -------------------------------------------------------------
    def fn_sub(m):
        i = m.start()
        body, nx = take_group(s, m.end() - 1) if False else (None, None)
        return m.group(0)
    out = ""
    i = 0
    while True:
        j = s.find("\\footnote", i)
        if j < 0:
            out += s[i:]; break
        body, nx = take_group(s, j + len("\\footnote"))
        if nx == j + len("\\footnote"):
            out += s[i:j+9]; i = j + 9; continue
        ctx["fn"].append(body)
        n = len(ctx["fn"])
        out += s[i:j] + ('<sup class="fn"><a href="#fn%d" id="fnr%d">%d</a></sup>' % (n, n, n))
        i = nx
    s = out

    # spacing / misc --------------------------------------------------------
    s = re.sub(r"\\(?:label)\{[^}]*\}", "", s)
    s = re.sub(r"\\index\{[^}]*\}", "", s)
    s = re.sub(r"\\(?:qquad|quad)\b", " ", s)
    s = re.sub(r"\\(?:hspace|vspace)\*?\{[^}]*\}", " ", s)
    s = s.replace("\\\\", "<br>")
    s = re.sub(r"\\newline\b", "<br>", s)
    s = re.sub(r"~", "\u00a0", s)
    s = re.sub(r"\\,|\\;|\\!|\\:", " ", s)
    s = re.sub(r"\\@", "", s)
    s = re.sub(r"\\xspace\b", "", s)
    # dashes and quotes
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = re.sub(r"``", "\u201c", s)
    s = re.sub(r"''", "\u201d", s)
    s = re.sub(r"(?<![\w\u201c])`", "\u2018", s)
    s = re.sub(r"'", "\u2019", s)
    # escapes
    s = re.sub(r"\\([&%$#_{}])", r"\1", s)
    s = re.sub(r"\\ldots\b|\\dots\b", "\u2026", s)
    s = re.sub(r"\\S\b", "\u00a7", s)
    s = re.sub(r"\\textrightarrow\b", "\u2192", s)
    s = re.sub(r"\\LaTeX\b", "LaTeX", s)
    s = re.sub(r"\\TeX\b", "TeX", s)
    s = re.sub(r"\\(?=\s)", " ", s)
    # book macros used in text mode: hand them to KaTeX rather than drop them
    if MATH_MACROS and ctx is not None and "math" in ctx:
        def mm(m):
            arg = m.group(2) or ""
            ctx["math"].append(("\\" + m.group(1) + arg, False))
            return "\x00M%d\x00" % (len(ctx["math"]) - 1)
        s = re.sub(r"\\(" + "|".join(sorted(MATH_MACROS, key=len, reverse=True)) +
                   r")(?![a-zA-Z])(\{[^{}]*\})?", mm, s)
    # leftover unknown one-arg commands: keep the argument
    s = re.sub(r"\\[a-zA-Z]+\*?\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\*?\b", "", s)
    return s


# ---------------------------------------------------------------- blocks

class Ctx(dict):
    pass


def new_ctx(chapnum, url):
    c = Ctx()
    c["chap"] = chapnum
    c["url"] = url
    c["fn"] = []
    c["counters"] = {k: 0 for k in THEOREMS}
    c["sec"] = [0, 0, 0]
    c["fig"] = 0
    c["tab"] = 0
    c["current"] = None      # (number, kind, title) for \label
    c["math"] = []
    c["verb"] = []
    c["anchor_seq"] = 0
    return c


def stash_math(t, ctx):
    """replace math with placeholders; returns text"""
    out = []
    i = 0
    n = len(t)
    def push(tex, display):
        ctx["math"].append((tex, display))
        return "\x00M%d\x00" % (len(ctx["math"]) - 1)
    while i < n:
        c = t[i]
        if c == "\\" and i + 1 < n:
            nxt = t[i+1]
            if nxt == "[":
                j = t.find("\\]", i)
                if j < 0:
                    j = n
                out.append(push(t[i+2:j], True)); i = j + 2; continue
            if nxt == "(":
                j = t.find("\\)", i)
                if j < 0:
                    j = n
                out.append(push(t[i+2:j], False)); i = j + 2; continue
            out.append(t[i:i+2]); i += 2; continue
        if c == "$":
            if t.startswith("$$", i):
                j = t.find("$$", i + 2)
                if j < 0:
                    j = n
                out.append(push(t[i+2:j], True)); i = j + 2; continue
            j = i + 1
            while j < n:
                if t[j] == "\\":
                    j += 2; continue
                if t[j] == "$":
                    break
                j += 1
            out.append(push(t[i+1:j], False)); i = j + 1; continue
        out.append(c); i += 1
    t = "".join(out)
    # amsmath display environments
    for env in ["align*", "align", "gather*", "gather", "equation*", "equation",
                "multline*", "multline", "aligned", "array", "cases", "mathpar"]:
        while True:
            f = find_env(t, env)
            if not f:
                break
            a, b, c2 = f
            body = t[a:c2]
            if env == "mathpar":
                inner = t[a + len("\\begin{mathpar}"):b]
                inner = inner.replace("\\and", "\\\\[1ex]")
                inner = re.sub(r"\\inferrule\*?\s*\{(.*?)\}\s*\{(.*?)\}",
                               lambda m: "\\dfrac{%s}{%s}" % (m.group(1).replace("\\\\", "\\quad "), m.group(2)),
                               inner, flags=re.S)
                t = t[:a] + push("\\begin{array}{c}" + inner + "\\end{array}", True) + t[c2:]
            else:
                t = t[:a] + push(body, True) + t[c2:]
    return t


def scan_math_labels(ctx, register):
    """\label inside a display carries the \tag or an equation number."""
    for idx, (tex, disp) in enumerate(ctx["math"]):
        for m in re.finditer(r"\\label\{([^}]*)\}", tex):
            key = m.group(1).strip()
            before = tex[:m.start()]
            tg = None
            for t2 in re.finditer(r"\\tag\*?\{([^}]*)\}", before):
                tg = t2.group(1)
            if tg is None:
                ctx["eqn"] = ctx.get("eqn", 0) + 1
                tg = "%d.%d" % (ctx["chap"], ctx["eqn"])
            anc = "eq-" + re.sub(r"[^A-Za-z0-9]+", "-", key)
            register(key, "(%s)" % tg, "Equation", "", anc)
            ctx["math"][idx] = (tex, disp)


def restore_math(s, ctx):
    def sub(m):
        tex, disp = ctx["math"][int(m.group(1))]
        tex = tex.strip()
        if disp:
            return '<span class="math-d">\\[' + tex + '\\]</span>'
        return '\\(' + tex + '\\)'
    return re.sub("\x00M(\\d+)\x00", sub, s)


def stash_verb(t, ctx):
    for env in ["lstlisting", "verbatim", "tikzpicture", "prooftree"]:
        while True:
            f = find_env(t, env)
            if not f:
                break
            a, b, c2 = f
            head = t[a:b]
            body = head.split("}", 1)[1]
            if body.startswith("["):
                k = body.find("]")
                body = body[k+1:]
            ctx["verb"].append((env, body, t[a:c2]))
            t = t[:a] + ("\x00V%d\x00" % (len(ctx["verb"]) - 1)) + t[c2:]
    return t


def restore_verb(s, ctx):
    def sub(m):
        env, body, whole = ctx["verb"][int(m.group(1))]
        if env in ("lstlisting", "verbatim"):
            return '<pre class="code"><code>%s</code></pre>' % html.escape(body.strip("\n"))
        if env == "tikzpicture":
            h = hashlib.sha1(whole.encode()).hexdigest()[:12]
            fn = B.tikz.get(h)
            if fn:
                return '<figure class="tikz"><img src="../figures/%s" alt="Diagram"></figure>' % fn
            return '<div class="tikz-missing">[diagram]</div>'
        return '<pre class="code"><code>%s</code></pre>' % html.escape(body)
    return re.sub("\x00V(\\d+)\x00", sub, s)


def anchor_for(ctx, kind, num):
    return "%s-%s" % (kind, str(num).replace(".", "-"))


def register_label(ctx, key, num, kind, title, anchor):
    B.labels[key] = dict(num=num, kind=kind, title=title,
                         url=ctx["url"], anchor=anchor)


def take_labels(seg, ctx, num, kind, title, anchor):
    """record every \\label in seg as pointing at (num, kind)"""
    for m in re.finditer(r"\\label\{([^}]*)\}", seg):
        register_label(ctx, m.group(1).strip(), num, kind, title, anchor)


def convert_body(t, ctx):
    """t has math + verbatim stashed. Return HTML."""
    out = []
    i = 0
    n = len(t)

    def flush_text(seg):
        for m in re.finditer(r"\\label\{([^}]*)\}", seg):
            k = m.group(1).strip()
            if k not in B.labels and ctx.get("current"):
                num, kind, ttl = ctx["current"]
                register_label(ctx, k, num, kind, ttl,
                               "sec-" + str(num).replace(".", "-"))
        seg = seg.strip("\n")
        if not seg.strip():
            return
        for para in re.split(r"\n\s*\n", seg):
            p = para.strip()
            if not p:
                continue
            p = inline(p, ctx)
            if p.strip():
                out.append("<p>" + p + "</p>")

    buf = ""
    while i < n:
        m = re.compile(r"\\(section|subsection|subsubsection|paragraph|subparagraph)\*?\s*\{|"
                       r"\\begin\{([a-zA-Z*]+)\}|"
                       r"\\epigraph\s*\{|\\asterism\b|\\qline\s*\{").search(t, i)
        if not m:
            buf += t[i:]
            break
        buf += t[i:m.start()]
        flush_text(buf); buf = ""
        i = m.start()

        if m.group(1):
            level = m.group(1)
            title, nx = take_group(t, m.end() - 1)
            star = "*" in t[m.start():m.end()]
            # trailing label
            keys = []
            while True:
                lm = re.match(r"\s*\\label\{([^}]*)\}", t[nx:nx+400])
                if not lm:
                    break
                keys.append(lm.group(1).strip()); nx += lm.end()
            key = keys[0] if keys else None
            if level == "section":
                if not star:
                    ctx["sec"][0] += 1; ctx["sec"][1] = 0; ctx["sec"][2] = 0
                num = "%d.%d" % (ctx["chap"], ctx["sec"][0])
                tag = "h2"
            elif level == "subsection":
                if not star:
                    ctx["sec"][1] += 1; ctx["sec"][2] = 0
                num = "%d.%d.%d" % (ctx["chap"], ctx["sec"][0], ctx["sec"][1])
                tag = "h3"
            elif level == "subsubsection":
                if not star:
                    ctx["sec"][2] += 1
                num = "%d.%d.%d.%d" % (ctx["chap"], ctx["sec"][0], ctx["sec"][1], ctx["sec"][2])
                tag = "h4"
            else:
                num = ""
                tag = "h5"
            anc = "sec-" + num.replace(".", "-") if num else "p-%d" % ctx["anchor_seq"]
            ctx["anchor_seq"] += 1
            for key in keys:
                register_label(ctx, key, num, "Section", title, anc)
            ctx["current"] = (num, "Section", title)
            ttl = inline(title, ctx)
            nums = '<span class="secnum">%s</span> ' % num if (num and not star) else ""
            out.append('<%s id="%s">%s%s</%s>' % (tag, anc, nums, ttl, tag))
            i = nx
            continue

        if m.group(2):
            env = m.group(2)
            f = find_env(t, env, m.start())
            a, b, c2 = f
            head_end = t.find("}", a) + 1
            body = t[head_end:b]
            opt, after = take_opt(t, head_end)
            if opt is not None:
                body = t[after:b]
            i = c2

            if env in THEOREMS:
                ctx["counters"][env] += 1
                num = "%d.%d" % (ctx["chap"], ctx["counters"][env])
                anc = anchor_for(ctx, env, num)
                take_labels(body, ctx, num, THEOREMS[env], opt or "", anc)
                ctx["current"] = (num, THEOREMS[env], opt or "")
                cls = "plain" if env in PLAIN_STYLE else "remarkish"
                head = '<span class="thm-kind">%s %s</span>' % (THEOREMS[env], num)
                if opt:
                    head += ' <span class="thm-name">%s</span>' % inline(opt, ctx)
                inner = convert_body(body, ctx)
                out.append('<section class="thm %s thm-%s" id="%s" data-kind="%s" data-num="%s">'
                           '<header>%s<a class="permalink" href="#%s" aria-label="Link to %s %s">\u00b6</a></header>%s</section>'
                           % (cls, env, anc, THEOREMS[env], num, head, anc, THEOREMS[env], num, inner))
                continue

            if env == "proof":
                inner = convert_body(body, ctx)
                out.append('<section class="proof"><header>Proof</header>%s</section>' % inner)
                continue

            if env in LISTLIKE:
                out.append(convert_list(body, env, ctx))
                continue

            if env in ("figure", "figure*", "table", "table*"):
                out.append(convert_float(body, env, ctx))
                continue

            if env == "tabular":
                out.append(convert_tabular(t[a:c2], ctx))
                continue

            if env in ("center", "mdframed", "quote", "quotation", "adjustwidth",
                       "spacing", "flushleft", "flushright", "small", "footnotesize"):
                inner = convert_body(body, ctx)
                cls = {"quote": "pullquote", "quotation": "pullquote",
                       "mdframed": "frame", "center": "centered"}.get(env, "plainblock")
                out.append('<div class="%s">%s</div>' % (cls, inner))
                continue

            if env == "thebibliography":
                continue

            inner = convert_body(body, ctx)
            out.append('<div class="env-%s">%s</div>' % (env, inner))
            continue

        if t.startswith("\\epigraph", i):
            a1, nx = take_group(t, i + len("\\epigraph"))
            a2, nx2 = take_group(t, nx)
            out.append('<blockquote class="epigraph"><p>%s</p><cite>%s</cite></blockquote>'
                       % (inline(a1, ctx), inline(a2, ctx)))
            i = nx2
            continue

        if t.startswith("\\asterism", i):
            out.append('<p class="asterism" aria-hidden="true">\u2042</p>')
            i += len("\\asterism")
            continue

        if t.startswith("\\qline", i):
            a1, nx = take_group(t, i + len("\\qline"))
            out.append('<p class="qline">%s</p>' % inline(a1, ctx))
            i = nx
            continue

        buf += t[i]
        i += 1

    flush_text(buf)
    return "\n".join(out)


def convert_list(body, env, ctx):
    body = re.sub(r"^\s*\[[^\]]*\]", "", body)
    items = re.split(r"\\item\b", body)
    lead = items[0]
    items = items[1:]
    tag = "ol" if env == "enumerate" else "ul"
    if env == "description":
        rows = []
        for it in items:
            lab, nx = take_opt(it, 0)
            rows.append("<dt>%s</dt><dd>%s</dd>" % (inline(lab or "", ctx),
                                                    convert_body(it[nx:], ctx)))
        return "<dl>" + "".join(rows) + "</dl>"
    rows = []
    for n_, it in enumerate(items, 1):
        lab, nx = take_opt(it, 0)
        if env == "enumerate":
            anc = "item-%d-%d" % (ctx["anchor_seq"], n_)
            for m in re.finditer(r"\\label\{([^}]*)\}", it[:400]):
                register_label(ctx, m.group(1).strip(), str(n_), "Item", "", anc)
            rows.append('<li id="%s">%s</li>' % (anc, convert_body(it[nx:], ctx)))
        else:
            rows.append("<li>%s</li>" % convert_body(it[nx:], ctx))
    ctx["anchor_seq"] += 1
    pre = convert_body(lead, ctx) if lead.strip() else ""
    return pre + "<%s>%s</%s>" % (tag, "".join(rows), tag)


def convert_tabular(chunk, ctx):
    f = find_env(chunk, "tabular")
    if not f:
        return ""
    a, b, c2 = f
    head_end = chunk.find("}", a) + 1
    spec, nx = take_group(chunk, head_end)
    body = chunk[nx:b]
    body = re.sub(r"\\(?:toprule|midrule|bottomrule|hline)\b", "\x01", body)
    rows = []
    for raw in body.split("\\\\"):
        raw = raw.replace("\x01", "").strip()
        if not raw:
            continue
        cells = []
        depth = 0; cur = ""
        k = 0
        while k < len(raw):
            ch = raw[k]
            if ch == "\\" and k + 1 < len(raw):
                cur += raw[k:k+2]; k += 2; continue
            if ch == "{": depth += 1
            elif ch == "}": depth -= 1
            if ch == "&" and depth == 0:
                cells.append(cur); cur = ""; k += 1; continue
            cur += ch; k += 1
        cells.append(cur)
        clean = []
        for c in cells:
            c = re.sub(r"\\multicolumn\{\d+\}\{[^}]*\}", "", c)
            clean.append(inline(c.strip(), ctx))
        rows.append(clean)
    if not rows:
        return ""
    head = rows[0]
    rest = rows[1:]
    h = "<thead><tr>" + "".join("<th>%s</th>" % c for c in head) + "</tr></thead>"
    bdy = "<tbody>" + "".join("<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>"
                              for r in rest) + "</tbody>"
    return '<div class="tablewrap"><table>%s%s</table></div>' % (h, bdy)


def convert_float(body, env, ctx):
    is_tab = env.startswith("table")
    cap = ""
    cm = re.search(r"\\caption\s*\{", body)
    capnum = ""
    if cm:
        cap, nx = take_group(body, cm.end() - 1)
        if is_tab:
            ctx["tab"] += 1
            capnum = "%d.%d" % (ctx["chap"], ctx["tab"])
            kind = "Table"
        else:
            ctx["fig"] += 1
            capnum = "%d.%d" % (ctx["chap"], ctx["fig"])
            kind = "Figure"
        anc = ("tab-" if is_tab else "fig-") + capnum.replace(".", "-")
        tail = body[nx:nx+300]
        take_labels(tail, ctx, capnum, kind, smart(cap)[:120], anc)
        body = body[:cm.start()] + body[nx:]
    else:
        anc = "float-%d" % ctx["anchor_seq"]; ctx["anchor_seq"] += 1
        kind = "Table" if is_tab else "Figure"
    body = re.sub(r"\\label\{[^}]*\}", "", body)
    body = re.sub(r"\\(?:centering|small|footnotesize|scriptsize)\b", "", body)
    inner = convert_body(body, ctx)
    caphtml = ""
    if cap:
        caphtml = '<figcaption><span class="fignum">%s %s</span> %s</figcaption>' % (
            kind, capnum, inline(cap, ctx))
    return '<figure class="float %s" id="%s">%s%s</figure>' % (
        "tabfloat" if is_tab else "figfloat", anc, inner, capham(caphtml))


def capham(x):
    return x


# ---------------------------------------------------------------- driver

def convert_file(path, chapnum, url, is_front=False):
    raw = open(os.path.join(ROOT, path)).read()
    t = strip_comments(raw)
    ctx = new_ctx(chapnum, url)

    m = re.search(r"\\chapter\*?\s*\{", t)
    title = ""
    star = False
    if m:
        star = t[m.start():m.end()].find("*") >= 0
        title, nx = take_group(t, m.end() - 1)
        chkeys = []
        while True:
            lm = re.match(r"\s*\\label\{([^}]*)\}", t[nx:nx+400])
            if not lm:
                break
            chkeys.append(lm.group(1).strip()); nx += lm.end()
        t = t[nx:]
        for chkey in chkeys:
            register_label(ctx, chkey, str(chapnum) if not star else "", "Chapter",
                           title, "top")
        ctx["current"] = (str(chapnum) if not star else "", "Chapter", title)
    t = re.sub(r"\\addcontentsline\{[^}]*\}\{[^}]*\}\{[^}]*\}", "", t)
    t = re.sub(r"\\interludehead\{[^}]*\}\{[^}]*\}", "", t)
    t = stash_verb(t, ctx)
    t = stash_math(t, ctx)
    scan_math_labels(ctx, lambda k, n, kk, ti, a:
                     register_label(ctx, k, n, kk, ti, a))
    body = convert_body(t, ctx)
    body = restore_math(body, ctx)
    body = restore_verb(body, ctx)
    fns = ""
    if ctx["fn"]:
        items = []
        for k, f in enumerate(ctx["fn"], 1):
            c2 = new_ctx(chapnum, url)
            f2 = stash_math(f, c2)
            f2 = inline(f2, c2)
            f2 = restore_math(f2, c2)
            items.append('<li id="fn%d">%s <a class="fnback" href="#fnr%d">\u21a9</a></li>' % (k, f2, k))
        fns = '<section class="footnotes"><h2>Notes</h2><ol>%s</ol></section>' % "".join(items)
    title = smart(title)
    return dict(title=title, body=body + fns, star=star,
                words=len(re.findall(r"\w+", raw)))


def smart(s):
    s = s.replace("---", "\u2014").replace("--", "\u2013")
    s = s.replace("``", "\u201c").replace("''", "\u201d")
    s = re.sub(r"'", "\u2019", s)
    s = re.sub(r"\\[a-zA-Z]+\s*\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"~", "\u00a0", s)
    return s


def parse_macros():
    global MATH_MACROS
    src = open(os.path.join(ROOT, "finding_mind.tex")).read()
    pre = src[:src.index("\\begin{document}")]
    macros = {}
    for m in re.finditer(r"\\(?:re)?newcommand\{?\\([a-zA-Z]+)\}?(?:\[(\d)\])?(?:\[[^\]]*\])?\s*\{", pre):
        name = m.group(1)
        nargs = int(m.group(2) or 0)
        body, _ = take_group(pre, m.end() - 1)
        if any(x in body for x in ["\\fontfamily", "\\selectfont", "\\makebox",
                                   "\\item", "\\par", "\\vspace", "\\noindent",
                                   "\\begin", "\\headrulewidth", "\\centering"]):
            continue
        macros["\\" + name] = body
    for m in re.finditer(r"\\DeclareMathOperator\*?\{\\([a-zA-Z]+)\}\{([^}]*)\}", pre):
        macros["\\" + m.group(1)] = "\\operatorname{%s}" % m.group(2)
    MATH_MACROS = set(k[1:] for k in macros)
    return macros


def parse_bib():
    t = strip_comments(open(os.path.join(ROOT, "bibliography.tex")).read())
    f = find_env(t, "thebibliography")
    a, b, c2 = f
    body = t[t.find("}", t.find("}", a) + 1) + 1:b]
    chunks = re.split(r"\\bibitem\{", body)[1:]
    ctx = new_ctx(0, "bibliography.html")
    for k, ch in enumerate(chunks, 1):
        key, rest = ch.split("}", 1)
        rest = rest.replace("\\newblock", " ").strip()
        c2x = new_ctx(0, "bibliography.html")
        rest = stash_math(rest, c2x)
        h = inline(rest, c2x)
        h = restore_math(h, c2x)
        B.bib[key.strip()] = (k, h)


def render_tikz():
    """compile each tikzpicture standalone and convert to SVG"""
    src = open(os.path.join(ROOT, "finding_mind.tex")).read()
    head = src[:src.index("\\begin{document}")]
    libs = "\n".join(re.findall(r"\\usetikzlibrary\{[^}]*\}", head))
    defs = "\n".join(re.findall(r"\\definecolor\{[^}]*\}\{[^}]*\}\{[^}]*\}", head))
    mac = []
    for m in re.finditer(r"\\(?:re)?newcommand\{?\\([a-zA-Z]+)\}?(?:\[(\d)\])?\s*\{", head):
        body, _ = take_group(head, m.end() - 1)
        if any(x in body for x in ["\\fontfamily", "\\selectfont", "\\makebox",
                                   "\\item", "\\par", "\\vspace", "\\noindent",
                                   "\\begin", "\\headrulewidth", "\\centering",
                                   "\\fancy"]):
            continue
        n = ("[%s]" % m.group(2)) if m.group(2) else ""
        mac.append("\\providecommand{\\%s}%s{%s}" % (m.group(1), n, body))
    pre = ("\\usepackage{amsmath,amssymb,amsthm,mathtools,stmaryrd}\n"
           "\\usepackage{mathpazo}\n\\usepackage{xcolor}\n\\usepackage{tikz}\n"
           "\\usepackage{bussproofs}\\usepackage{mathpartir}\n"
           + libs + "\n" + defs + "\n" + "\n".join(mac) + "\n")
    os.makedirs(FIGDIR, exist_ok=True)
    work = "/home/claude/tikzwork"
    os.makedirs(work, exist_ok=True)
    found = []
    for dirp in ["ThePledge", "TheTurn", "ThePrestige", "Interludes"]:
        d = os.path.join(ROOT, dirp)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".tex"):
                continue
            t = strip_comments(open(os.path.join(d, fn)).read())
            pos = 0
            while True:
                f = find_env(t, "tikzpicture", pos)
                if not f:
                    break
                a, b, c2 = f
                found.append(t[a:c2])
                pos = c2
    # also the master file's part-map figure
    t = strip_comments(src)
    pos = src.index("\\begin{document}")
    while True:
        f = find_env(t, "tikzpicture", pos)
        if not f:
            break
        a, b, c2 = f
        found.append(t[a:c2])
        pos = c2
    ok = 0
    for chunk in found:
        h = hashlib.sha1(chunk.encode()).hexdigest()[:12]
        outsvg = os.path.join(FIGDIR, h + ".svg")
        if os.path.exists(outsvg):
            B.tikz[h] = h + ".svg"; ok += 1; continue
        doc = ("\\documentclass[border=6pt]{standalone}\n" + pre +
               "\n\\begin{document}\n" + chunk + "\n\\end{document}\n")
        p = os.path.join(work, h + ".tex")
        open(p, "w").write(doc)
        r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error",
                            "-output-directory", work, p],
                           capture_output=True, timeout=120)
        pdf = os.path.join(work, h + ".pdf")
        if os.path.exists(pdf):
            subprocess.run(["pdftocairo", "-svg", pdf, outsvg], capture_output=True)
            if os.path.exists(outsvg):
                B.tikz[h] = h + ".svg"; ok += 1
    print("tikz rendered %d/%d" % (ok, len(found)))


if __name__ == "__main__":
    render_tikz()
    print("macros:", len(parse_macros()))
