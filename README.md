# Finding Mind — findingmind.io

*The Mortal Scientist and the Ecology of Thought.* A magic trick in three acts.

This repository is the web edition of the book, generated from its LaTeX source in
[`F1R3FLY-io/publications`](https://github.com/F1R3FLY-io/publications) (`FindingMind/`)
and served by GitHub Pages at <https://findingmind.io>.

- `index.html`, `read/`, `figures/`, `macros.js` — generated; do not edit by hand
- `_build/` — the generator (`build.sh`, `gen.py`, `convert.py`, `contact.py`, `static/`)
- `deploy/` — canonical-domain finalizer and redirector helpers
- `HOSTING.md` — domains, DNS, and how to rebuild when a new draft lands
- `PROPOSAL.md` — the original design proposal for the web edition

To regenerate after a new draft: assemble the book (baseline + `draftN/` deltas, see
`HOSTING.md`), then `_build/build.sh /path/to/assembled/FindingMind`.
