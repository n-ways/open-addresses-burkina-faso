#!/bin/sh
# Builds the paper's PDFs from docs/paper.md and its translations (docs/paper.<lang>.md) with pandoc and LaTeX (tectonic).
#   sh docs/paper/build.sh            # every language
# Needs pandoc 3, tectonic and pdftocairo; figures are compiled from docs/figures/*.tex (to PDF for the
# report, SVG for the Markdown) whenever a source or its data changed.
set -e
here=$(cd "$(dirname "$0")" && pwd)
docs=$(dirname "$here")
for f in "$docs"/figures/*.tex; do
  [ -e "$f" ] || continue
  b=${f%.tex}
  # a language variant (fig-x.fr.tex) inputs fig-x.tex and its data: rebuild when any of them is newer
  main=$(echo "$f" | sed 's/\.[a-z][a-z]\.tex$/.tex/')
  if [ ! -e "$b.pdf" ] || [ "$f" -nt "$b.pdf" ] || [ "$main" -nt "$b.pdf" ] || [ -n "$(find "$docs/figures" -name '*.dat' -newer "$b.pdf")" ]; then
    tectonic -X compile --outdir "$docs/figures" "$f" 2>&1 | grep -v "^note:" || true
    pdftocairo -svg "$b.pdf" "$b.svg"
  fi
done
build() { # $1 source, $2 output
  pandoc "$docs/$1" --from markdown+tex_math_dollars+raw_tex --template "$here/template.tex" \
    --lua-filter "$here/figures.lua" --citeproc --bibliography "$here/references.bib" --csl "$here/ieee.csl" --lua-filter "$here/bib-lang.lua" \
    -H "$here/style.tex" -H "$here/colours.tex" --resource-path "$docs:$here" --number-sections --toc --pdf-engine=tectonic -o "$docs/$2"
}
base=n-ways-addressing-burkina-faso
for src in "$docs"/paper.md "$docs"/paper.*.md; do
  [ -e "$src" ] || continue
  name=$(basename "$src")
  case $name in paper.md) lang=en ;; *) lang=${name#paper.}; lang=${lang%.md} ;; esac
  build "$name" "$base-$lang.pdf"
done
