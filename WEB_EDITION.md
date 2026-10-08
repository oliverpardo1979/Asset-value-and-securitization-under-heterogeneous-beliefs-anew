# Digital edition

Read the complete paper and explore its verified examples at
<https://oliverpardo1979.github.io/Asset-value-and-securitization-under-heterogeneous-beliefs-anew/>.

The edition follows the reading and exploration format of Oliver Pardo's
[The Upside of Being Replaceable](https://oliverpardo1979.github.io/ai-growth-and-labor/).
The converter helpers and base styling are adapted from that project's own source.

## One manuscript, two reading formats

`main.tex` is authoritative. The web implementation does not edit it.
`scripts/build_web_manuscript.py` generates the complete reader, including the
appendices, proofs, acknowledgments, AI declaration, and bibliography.
It uses the compiled AUX file to check equation, section, proposition, table,
and figure numbering. References link to their targets. Proofs can be expanded
individually or together, and a link into a proof opens it automatically.

The five TikZ figures are extracted from the approved PDF as vector images.
The author acknowledgment is a separate disclosure, preserving the numbering
of the manuscript's body footnotes. The converter stops on unsupported raw TeX,
Pandoc warnings, missing labels, lost display equations, or broken internal links.
It checks the inventory of visible text through the Pandoc-to-HTML conversion.
Browser QA separately checks MathJax rendering and figure crops.

`docs/paper/asset-value-and-securitization.pdf` is the approved manuscript PDF,
copied byte-for-byte. It is not the journal's combined editorial submission file.
Neither response letters nor editorial reports are included in the site.
The initial edition uses manuscript commit `569840397ac65ab5e8bede250cf86e1ae1d45b8a`.
The PDF is the reference if a browser renders an equation differently.

The reader loads MathJax 3.2.2 from jsDelivr. The reader and explorer require
JavaScript. The PDF and plain generated HTML remain downloadable without it.
No analytics, forms, accounts, browser storage, or server-side calculation are used.

## What the explorer computes

The browser computes no equilibria. `scripts/build_web_data.py` uses the existing
companion to export seven stored cases and both monotone iteration histories.
Each output is checked against the known price vectors in `paper_examples.py`.
Every saved step uses the companion's own `price_operator`.

The main panel presents the three known fixed points from Example 1. The middle
one is checked by direct substitution separately from the extreme-equilibrium
solver. The panel does not assert that the algorithm enumerates all equilibria.
The three payment patterns and the price identities are checked during export.
No interpolation between parameter combinations or arbitrary-input solver is offered.

The motivating illustration uses the epsilon-zero limit with dividends (0, 2, 3),
gross return 2, and junior attachment point 2.25. The slider illustrates the
payoff rule at hypothetical resale prices. It does not change the economy or
find a new equilibrium. Example 1 instead has strictly positive transitions.

Iteration lines connect successive stored iterates. Their scales change with
the selected example and iteration window. After one sequence stops, its last
value is held fixed for display. The stopping rule controls the step and
fixed-point residual, not the distance to the exact equilibrium. Source JSON
retains full floating-point precision. Tables round only for display.
Coinciding numerical extremes are not, by themselves, a proof of uniqueness.

## Build and check

Requires Python 3.10+ and a current compiled `main.aux`, alongside the approved PDF.
The Python dependencies include Pandoc. A LaTeX compiler is needed only when
refreshing the AUX after an approved manuscript update.

```sh
python -m pip install -r requirements-web.txt
# Compile the unchanged main.tex, retaining its AUX, into tmp/web-latex.
# For example, with Tectonic:
tectonic -k --outdir tmp/web-latex main.tex
python scripts/build_web_manuscript.py --build-dir tmp/web-latex --pdf path/to/approved/main.pdf
python scripts/build_web_data.py
python scripts/build_web_data.py --check
python -m unittest computational_companion.test_waterfall_equilibria
python -m unittest discover -s tests
node --check docs/web.js
python -m http.server 8767 --bind 127.0.0.1 --directory docs
```

Review the reader, equations, figure crops, proofs, explorer selections, keyboard
controls, and mobile layout before committing a refreshed `docs/` snapshot.
Source hashes normalize text line endings to LF so Windows and Linux agree.
The PDF hash is a hash of the original bytes.

## Publication

GitHub Pages is deployed by `.github/workflows/web-edition.yml` from
`codex/jme-major-revision`, the repository's existing default branch. The branch
name is historical. This web addition does not change `main`, the manuscript,
the response letter, the companion, or Overleaf.

The workflow tests the numerical code and the committed site snapshot before
deploying only `docs/`. It does not rewrite the manuscript or silently rebuild
HTML on the server. A changed manuscript source or stale example export fails
the checks rather than publishing a mixed edition. For an approved paper update,
refresh the approved PDF, compile fresh labels, rebuild and visually review the
reader, then commit the synchronized snapshot. Do not manually edit generated HTML.
