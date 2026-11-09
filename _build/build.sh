#!/usr/bin/env bash
# Regenerate findingmind.io from the book's LaTeX source.
#
#   _build/build.sh [BOOK_DIR] [DOMAIN]
#
# BOOK_DIR  directory holding finding_mind.tex (default: ../publications/FindingMind,
#           i.e. a sibling checkout of F1R3FLY-io/publications). Point it at an
#           assembled overlay of the latest draft deltas, not at the bare baseline.
# DOMAIN    canonical hostname for CNAME/sitemap/canonical links (default: findingmind.io)
#
# Writes into the repository root (index.html, read/, figures/, macros.js, ...).
# Needs: python3, pdflatex with tikz/standalone, pdftocairo.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
BOOK="${1:-$(dirname "$REPO")/publications/FindingMind}"
DOMAIN="${2:-findingmind.io}"
[ -f "$BOOK/finding_mind.tex" ] || { echo "no finding_mind.tex in $BOOK" >&2; exit 1; }
export FM_BOOK="$BOOK" FM_OUT="$REPO" FM_WORK="${FM_WORK:-$HERE/tikzwork}"
python3 "$HERE/gen.py"
cd "$(dirname "$REPO")" && python3 "$REPO/deploy/finalize.py" "$DOMAIN" --site "$(basename "$REPO")"
