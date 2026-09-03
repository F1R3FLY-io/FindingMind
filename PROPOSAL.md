# Finding Mind — proposed web edition

A design proposal, with a working build attached. Everything described below has been
built and is in the `finding-mind/` directory; nothing here is a mock-up.

---

## 1. What the ask turned into

The brief was to replace Hannah's filler content with the current book and to swap the
landing-page image. Reviewing the two repositories changed the shape of the job.

Hannah's page is a single 139 KB `index.html`, almost all of which is a generated inline
SVG rose window (~950 panes, produced by `_src/gen.py`). Around it sit eight paragraphs of
placeholder argument, three essay links and three talk links. Her own README describes it
as a design comp and flags the open questions.

The book, rebuilt by overlaying `draft2`…`draft23` onto the base tree, is:

| | |
|---|---|
| Chapters | 68 numbered, 5 unnumbered (the map, related work, three conclusion chapters), 4 interludes |
| Words | ~237,000 |
| Cross-references | 1,887 |
| Labels | 1,108 |
| Numbered results | 573 (97 definitions, 132 propositions, 212 remarks, 32 corollaries, 16 theorems, 12 conjectures, 13 questions, and the rest) |
| Bibliography | 242 entries |
| Inline math | ~5,100 expressions |
| Macros | 167 |
| TikZ figures | 17 |
| Code listings | 15 rholang blocks |
| Raster images | 0 |

That is not a landing page with a book behind it. It is a reading instrument, and the
apparatus turns out to be where the design opportunity is. No print edition can make 1,887
references clickable. The front matter already promises a map, six reading routes, and a
gathered list of load-bearing unproved claims closing "Nothing else is hiding." A website
can make that promise literally checkable, and that is the one thing this site does that
no other book site does.

---

## 2. The pipeline

The hard part is not the visual design; it is getting 237,000 words of dense LaTeX into
HTML without the maths degrading and without the 1,887 references going dead. Four
approaches were considered — Pandoc, LaTeXML, tex4ht, and a purpose-built converter. A
purpose-built converter won, for one reason: **the maths is never expanded.**

- Math is extracted verbatim, passed through as `\(…\)` / `\[…\]`, and rendered
  client-side by KaTeX **with the book's own 167 macros supplied as a macro table**
  (`macros.js`, generated from the preamble). There is no macro reimplementation to drift
  out of sync with the source. If a macro changes in `finding_mind.tex`, the site picks it
  up on the next build.
- Numbering replicates LaTeX exactly — each theorem environment keeps its own counter,
  reset per chapter — so Definition 24.2 on the site is Definition 24.2 in the PDF.
- Two passes: convert, then resolve. **All 1,887 cross-references resolve. Zero dead.**
- The 17 TikZ figures compile standalone against a reduced preamble and convert to SVG.
  **15 of 17 render**; one is still failing and one lives in a file nothing inputs.
- KaTeX is vendored locally (604 KB), not loaded from a CDN. The site has no third-party
  runtime dependency except Google Fonts.

Build cost is about ninety seconds end to end. `_build/gen.py` regenerates everything from
a `draft2`…`draftN` overlay, so a new draft is a re-run, not a re-edit.

---

## 3. The design

### The image

Your panel replaces the roundel at full size, uncropped except for the phone chrome (the
artwork occupies rows 174–1154 of the screenshot; that band is the hero).

It earns the position on the argument, not just on looks. It is a crowd of hundreds of
small, individually simple agents, none of them in charge, all oriented on one object,
with a serpent along the branch above them taking the shape of the thing that reaches back
on itself. The book's central move is that the answer is always a *population* — coherence
clusters, the compactness argument, the whole ecology. Hannah's roundel made that claim
through a diagram. This makes it through a scene, which is better on a page where the
first thing a reader wants is to be interested rather than instructed.

Consequently Hannah's three ring-buttons and their rollover captions are cut. They were
explaining a diagram that stood in for content the site did not yet have. It has the
content now.

### Colour

Sampled from the artwork by k-means rather than invented:

| | | |
|---|---|---|
| `#14100a` | lead | the near-black between panes; the hero ground |
| `#f3ecd8` | vellum | the robes; the reading ground |
| `#241c11` | ink | body text |
| `#8a6516` / `#b98d2f` | halo | gold; definitions, cross-references, part headings |
| `#3d6b4a` | serpent | green; proved results, code rules, citations |
| `#9c130e` | apple | the one red, and it does exactly one job — see below |

The dark hero against vellum reading pages keeps Hannah's "a lit window in an unlit room"
idea, which is a good idea and hers.

### Type

One family: **Source Serif 4**, using its optical-size axis (8–60) for display, text and
margin sizes rather than pairing two faces. You chose Minion in June 2025 and Hannah
substituted EB Garamond because Minion is not web-licensed there. Source Serif 4 is the
better screen substitute: it was drawn for text at screen sizes and has genuine optical
sizes, so the 60pt cut on the title and the 8pt cut in the margin rail come from one
design rather than a compromise. **IBM Plex Mono** is kept from Hannah's page and appears
only where the book itself is monospaced — rholang listings, `\texttt` runs, and the
`@P` / `*x` notation. It is not used as decoration on small labels.

### The reading page

```
┌────────────┬──────────────────────────────┬─────────────┐
│  contents  │   text, ~66 characters       │   margin    │
│  rail      │                              │   rail      │
│            │   result cards, flush left,  │             │
│  parts and │   with a coloured rule that  │  a hovered  │
│  chapters, │   says what kind of claim    │  reference  │
│  sticky,   │   it is                      │  opens here │
│  scrolled  │                              │             │
│  to where  │                              │             │
│  you are   │                              │             │
└────────────┴──────────────────────────────┴─────────────┘
```

Left-aligned, ragged right — justification without proper hyphenation is bad on the web
and this text has long technical words. Below 1180 px the margin rail retires and
references navigate normally; below 900 px the contents rail becomes a drawer.

### Three things the apparatus does

1. **References open where you are.** Hovering or focusing a reference to a numbered result
   fetches it and renders it in the margin rail, maths and all, without moving you off the
   page. Section and part references show a title card. On narrow screens the same link
   simply navigates.
2. **Every result has an address.** `…/24-enzymes-and-individuals.html#remark-24-7` is a
   permanent link to Remark 24.7, with a paragraph mark on hover. A claim can be cited and
   argued with directly, which matters for a book that is being reviewed in public.
3. **The ledger.** All 573 results in one searchable, filterable list. The colour key is
   semantic and consistent between the ledger and the body: **gold** for definitions and
   constructions, **green** for proved results, **grey** for remarks and observations, and
   **red for conjectures and questions** — that is, for what the book has not established.
   There is a single button, *Show only what the book still owes*, which reduces 573 rows
   to the 25 conjectures and questions. That is the front matter's promise made operable,
   and it maintains itself: the categories are the book's own, so a conjecture promoted to
   a proposition leaves the list on the next build without anyone curating it.

Point 3 is where the boldness is spent. Everything else stays quiet.

---

## 4. What is in the directory

```
finding-mind/
  index.html              landing page, your image
  book.css                the whole design, one file
  reader.js               maths, margin previews, contents drawer
  macros.js               the book's 167 macros, generated from the preamble
  hero.jpg                the panel, cropped out of the screenshot
  favicon.svg
  katex/                  vendored, 604 KB
  figures/                15 TikZ figures as SVG
  read/
    contents.html         full table of contents
    ledger.html           the 573 results
    bibliography.html     242 entries
    nav.json, ledger.json
    01-prolegomena-to-finding-mind.html … 68-any-future-metaphysics.html
    how-to-read-this-book.html, related-work-and-where-this-differs.html, …
    permitted-say.html, foam-born.html, begotten.html, right-sizing.html
  _build/
    convert.py, gen.py, static/    the generator, for the next draft
```

It drops into `f1r3lang-io.github.io/finding-mind/` as a replacement and needs no build
step on GitHub's side — everything is static. Total 8.6 MB, of which 4.3 MB is the SVG
figures (pdftocairo writes glyphs as outlines; they compress to about a fifth over the
wire, and could be cut further by re-rendering with a font-preserving converter).

---

## 5. Open questions

Six, roughly in order of how much they change the work.

1. **Whose typography?** The sibling pages under this repo are F1R3FLY-branded — Josefin
   Sans headings, Source Sans 3 body, per the brand portal. Hannah deliberately did not
   use them here, and this proposal follows her in treating the book as having its own
   typography descended from your Minion choice. If the book site should instead read as a
   F1R3FLY property, that is a one-file change to `book.css`.

2. **How much goes up?** This build publishes all 749 pages. That is a real decision, not a
   default — the alternative is to publish The Pledge and the interludes in full and gate
   the Turn and the Prestige behind a signup or a sample.

3. **The publisher line.** Hannah left it out because Pomera Press was an unconfirmed
   verbal assurance from January 2025. This build also leaves it out. Still right?

4. **The draft's own honesty, in public.** The ledger surfaces `thm:compact-consensus` and
   the other load-bearing gaps by construction. Your front matter already names them, so
   this is consistent rather than new — but it is considerably more prominent on a web page
   than on page 57 of a PDF, and it is worth deciding deliberately rather than inheriting.

5. **Two chapter titles are truncated in URLs** at 46 characters
   (`16-the-labeled-transition-system-and-context-deco`). Easy to hand-override for the
   ones that read badly.

6. **The repository shortfall.** Building the overlay confirms what your notes have been
   tracking: `draft18` declared 49 files and committed 5, `draft20` declared 51 and
   committed 21, `draft23` is intact. The site is generated from the overlay, so it is
   currently *ahead of* what a clean clone of the repo would produce. If the site is to be
   the canonical public text, the missing commits stop being a bookkeeping annoyance and
   become the thing that decides what the public sees.

---

## 6. Smaller things noticed while building

- One TikZ figure fails to compile standalone; a second lives in `turn_hypercomp_ch02.tex`,
  which nothing inputs any more.
- `\rhoc` and a handful of other macros are used in text mode as well as maths. The
  converter hands them to KaTeX rather than dropping them, which is why "rho calculus"
  still reads correctly.
- Two labels sit loose in running prose (`sci:sec:transport`) and two sit on `\item`s
  inside enumerates. LaTeX resolves these to whatever the current counter is; the converter
  now does the same, but they are worth tidying in the source.
- `pledge_map` and `pledge_related` are `\chapter*`, so they are unnumbered here as they
  are in print, and their figure and table numbers come out as 0.1. Harmless, and only
  visible if you go looking.
