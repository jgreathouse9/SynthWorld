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
- The author is comfortable with formal econometrics, but the dissertation
  chapters follow the JPAM applied style (below), not the econometrics-paper
  style, so the technical depth is deliberately limited. State and discuss the
  identification assumptions in plain terms (for SPSC: the relevance/proxy
  condition, the bridge condition, the treated-history-as-instrument and
  exclusion logic, and the factor-model reasoning behind the bounds), and keep
  the single optimization that produces the estimator's weights. Do not
  reproduce the estimator's inner machinery in the dissertation body: the GMM
  moment/de-trending formalism, the standard-error sandwich and its theorems,
  the conformal-band derivation, and the penalty-selection internals are cut
  and cited to the source paper (Park--Tchetgen 2025) and the mlsynth docs. The
  reference exemplar is Coupet (2024, JPAM), an SCM paper that carries one
  equation and does inference through placebos, not standard errors. The
  econometrics-journal version (`paper1_ectj.qmd`) keeps the method at the same
  applied altitude and cites the same machinery (see the applied-policy note
  below); the full derivations live in the source method papers (Park--Tchetgen
  2025, Shi et al. 2026), not in either of our versions.

## Applied-policy (JPAM) framing

The dissertation chapters, and any version aimed at a policy journal such as the
`Journal of Policy Analysis and Management` (JPAM), follow that outlet's
applied-economist house style, not the econometrics-paper style. Reference
exemplars: Fairlie (2023, racial inequality in pandemic business earnings),
Pathania & Netessine (2025, Amazon facilities and local economies), and
Churchill, Henkhaus & Lawler (2024, vaccine recommendations). The conventions
they share, to apply by default in the framing sections:

- **Lead with the policy stakes, not the method.** Open the abstract and the
  introduction with the real-world phenomenon and a motivating policy question
  ("were the losses felt disproportionately by people of color?", "how much
  growth do these facilities actually promote, if any?"). Quantify what is at
  stake (jobs, dollars, people, inequality) in the first paragraph. The estimator
  is a tool, named once and subordinated.
- **State the contribution plainly and early.** Within the first two or three
  paragraphs, say what the paper does in applied language ("This paper provides
  the first estimates of ...", "new evidence on ..."), foregrounding the policy
  question over the identification strategy.
- **Put headline numbers up front, with signs and economic magnitude.** Report
  effects in interpretable units (percentage points, dollars, "+1.46% at the
  mean", "$1 billion annually") in the abstract and intro, and speak to economic
  significance, not only statistical significance. State plainly what is and is
  not significant.
- **Frame the discussion as a policy ledger.** Weigh costs against benefits, say
  who bore them (distributional incidence across groups, regions, or tiers), and
  state what the estimate implies for the decision the policymaker faced.
  Churchill's "$1 billion ... with little to no observable health benefits" is the
  model: a cost-benefit sentence a policymaker can act on.
- **Organize the literature review around the gap, not paper-by-paper.** Motivate
  the contribution as filling a policy-relevant evidence gap; do not summarize
  each prior study in turn.
- **Keep the framing sections in plain prose.** Short sentences, minimal jargon in
  the intro, background, and discussion.

This scopes the formal-econometrics preference above. In the dissertation the
methods section discusses the identification assumptions and the estimator's
main optimization in applied terms and cites the source paper and mlsynth for
the inner machinery; the intro, background, and discussion carry the JPAM
applied framing. The econometrics-journal version (`paper1_ectj.qmd`) is an
*applied* econometrics-journal paper, not a method-proposing one, so it keeps
the method at applied altitude too: even in an econometrics journal, applied SCM
papers present the estimator briefly and cite the source (exemplars: Cho 2020
and Cerqueti et al. 2021, applied SCM COVID papers in *The Econometrics
Journal*), reserving long derivations for method-proposing papers (Goh & Yu
2022). Its proximal/methods section therefore mirrors the dissertation's
(concept, the good-proxy conditions, the single ridge-GMM optimization, then the
proxies), cites the GMM / standard-error / conformal / base-PI machinery to
Park--Tchetgen 2025, Shi et al. 2026, and mlsynth, and carries no derivation
appendix. What distinguishes it from the dissertation is framing, not math
depth: it folds the literature review into the intro and drops the JPAM
policy-ledger framing, rather than adding technical apparatus.

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
