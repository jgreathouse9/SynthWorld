# SynthWorld — repository notes for Claude

## Writing style (stable author preferences)

These are durable preferences for the author's papers and dissertation. Apply
them by default; do not reintroduce the patterns they forbid.

- **No boldface for non-mathematical text.** The author does not write with
  `**bold**` emphasis in prose. Use italics (`*term*` / `\emph{}`) sparingly for
  a genuine first-use technical term, and otherwise let the sentence carry the
  emphasis. Boldface is reserved for mathematical objects (e.g. `\mathbf{}`
  vectors/matrices), never for ordinary words.
- **No em-dashes.** The author does not use em-dashes (`---` in Markdown/LaTeX,
  or the Unicode `—`) in prose. Recast with commas, colons, semicolons,
  parentheses, or separate sentences, whichever fits. En-dashes (`--`) for
  numeric ranges and compound names (`1991--2020`, `Newey--West`) are correct
  and must be preserved. Do not reintroduce em-dashes in new prose.
- **Report the pre-treatment RMSE, not RMSE/SD.** When summarizing synthetic-control
  pre-fit quality, report the raw pre-treatment RMSE. Do not report the RMSE/SD
  ratio. Ground identification claims in the estimator's formal relevance /
  identification conditions and the factor structure, not in a fit ratio.
- The author is comfortable with formal econometrics. In the dissertation,
  spell out identification conditions, moment/GMM optimization, and the factor-model
  reasoning behind bias claims, citing the source papers rather than gesturing at them.

## Structure

- Papers are the single source of truth: `Paper1/Paper/paper1.qmd` (Hawaii /
  SPSC), `Paper2/Paper/india.qmd`, `Paper3/Paper/paper3.qmd`.
- The dissertation (`Dissertation/`) assembles chapters from those papers via
  `Dissertation/build_chapters.py` (strips YAML, demotes headings, namespaces raw
  LaTeX `\label`/`\ref` keys per chapter, patches data paths). It renders on push
  through `.github/workflows/Dissertation.yml`, which installs mlsynth from GitHub.

## mlsynth

- Install mlsynth from GitHub, not PyPI: `git+https://github.com/jgreathouse9/mlsynth.git`
  (the SPSC / `PROXIMAL` estimator surface lives there). Both
  `Paper1/Paper/reqs/requirements.txt` and `Dissertation/build-requirements.txt`
  already pin it that way.
- SPSC is fit via `PROXIMAL({... "methods": ["SPSC"], "spsc_detrend": True ...}).fit()`.

## Rendering gotchas (Quarto -> LaTeX, learned the hard way)

- Emit tables as raw `booktabs` `\begin{table}` (see `latex_table` in
  `paper1.qmd`), not markdown pipe tables: pandoc renders pipe tables as
  `longtable`, whose row hooks are undefined against the CI TinyTeX kernel.
- In markdown prose, a `$...$` math span must not be immediately followed by a
  digit (pandoc won't parse it as math). Write `$\sim 65$`, not `$\sim$65`.
