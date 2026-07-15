# Dissertation (GSU format, Quarto)

A Georgia State University dissertation that wraps the three SynthWorld papers in
the official `gsudiss` LaTeX class. The papers stay the single source of truth:
edit `Paper1/Paper/paper1.qmd`, `Paper2/Paper/india.qmd`, or
`Paper3/Paper/paper3.qmd` and the dissertation rebuilds from them.

## Build

```bash
cd Dissertation
make            # build_chapters.py -> gen_ch3_threecity.py -> quarto render
```

Produces `dissertation.pdf`. On push, `.github/workflows/Dissertation.yml` does
the same and commits the PDF (mirrors the Paper2/Paper3 workflows).

Requirements: Quarto, a LaTeX engine (TinyTeX), and the Python stack in
`build-requirements.txt` (mlsynth + pandas/numpy/matplotlib/openpyxl/pyarrow/jupyter),
because Chapters 1 and 2 execute their SHC code to produce real figures.

## How it fits together

- `build_chapters.py` reads the three source paper qmds and writes
  `chapters/*.qmd`: it strips each paper's YAML, demotes every heading one level
  (paper sections become chapter sections), adds the chapter title, and
  namespaces the raw-LaTeX `\label` keys so the papers don't collide. It also
  patches Paper 1's plotting to the current mlsynth API + data paths, appends the
  India Results figures, fixes a Paper 3 citation typo, and copies + repairs the
  three bibliographies (missing `}` braces, four missing references).
- `gen_ch3_threecity.py` fits SDID and PPSCM once under staggered adoption
  (NYC + SF from Aug 2021, LA from Nov 2021; New Orleans dropped; donor pool
  excludes the treated cities and the duplicate New York-Newark CSA) and saves
  the pooled figure `ch3_threecity.png`.
- `dissertation.qmd` sets the GSU class options and `{{< include >}}`s the three
  generated chapters; `_tex/` holds the preamble and the GSU front matter;
  `Frontmatter/` holds the abstract / index words / dedication / acknowledgments;
  the `*.cls` / `*.sty` / `*.bst` are the GSU class and its bundled styles.

Generated files (`chapters/*.qmd`, `pl.bib`, `delhi.bib`, `ktc.bib`,
`ch3_threecity.png`, render artifacts) are git-ignored and rebuilt by `make`.

## Notes / things to verify (content, not formatting)

- Committee: Coupet (chair), Andrew Heiss, Lindsay Rose Bullinger.
  `Frontmatter/dedication.tex`, `acknowledgments.tex`, `index-words.tex` are
  placeholders.
- `Jones2021` is cited in Chapter 3 but is in no `.bib` — add the entry.
- The fixes `build_chapters.py` applies (the missing braces in `delhi.bib` /
  `ktc.bib`, the four added references, the `uporigin.OKPANI20241065` typo, the
  Paper 1 SHC API) are bugs in the source too: your standalone Paper 1 / Paper 2
  builds hit the same issues against current mlsynth. Worth fixing at the source
  so the per-paper CI is green as well.
- PPSCM needs an integer time index here because of an mlsynth bug
  (`ppscm_helpers/setup.py` runs `np.isfinite` on Timestamp adoption times).
