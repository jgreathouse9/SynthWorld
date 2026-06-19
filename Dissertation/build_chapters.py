#!/usr/bin/env python3
"""Assemble the dissertation chapters from the SOURCE paper qmds.

Single source of truth: edit ``Paper1/Paper/paper1.qmd``,
``Paper2/Paper/india.qmd``, or ``Paper3/Paper/paper3.qmd`` and re-run this
script (the CI workflow does it on push) to regenerate ``chapters/*.qmd`` and
patch the bibliographies. The dissertation never edits your papers in place; all
dissertation-specific assembly lives here.

Steps per chapter: strip the paper's YAML, demote every heading one level (paper
sections become chapter sections), add the chapter title, and namespace the raw
LaTeX ``\\label`` keys so the three papers don't collide. Paper 1 additionally
gets its plotting ported to the current mlsynth API and its data path rewritten;
the India chapter gets a Results section with live SHC figures; Paper 3 gets the
pooled SDID figure (pre-rendered by ``gen_ch3_threecity.py``).
"""
from __future__ import annotations

import re
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent  # the SynthWorld repo root

SRC = {
    "01-hawaii": (REPO / "Paper1/Paper/paper1.qmd", "p1",
        "Paradise Lost? Estimating the Economic Impact of Hawaii's Mandatory Quarantine using Synthetic Historical Controls"),
    "02-india": (REPO / "Paper2/Paper/india.qmd", "p2",
        "Clearing the Air: How India's 2020 Lockdown Impacted Air Quality"),
    "03-mandates": (REPO / "Paper3/Paper/paper3.qmd", "p3",
        "Locking Away Prosperity? Evaluating the Labor Impacts of Vaccine Mandates"),
}
BIBS = {  # source bib -> local copy name
    REPO / "Paper1/Paper/pl.bib": "pl.bib",
    REPO / "Paper2/Paper/delhi.bib": "delhi.bib",
    REPO / "Paper3/Paper/ktc.bib": "ktc.bib",
}


# --------------------------------------------------------------------------- #
# generic chapter transforms
# --------------------------------------------------------------------------- #
def strip_yaml(t: str) -> str:
    if t.lstrip().startswith("---"):
        p = t.split("---", 2)
        return p[2] if len(p) == 3 else t
    return t


def strip_bibcmds(t: str) -> str:
    return re.sub(r"^\\bibliography(style)?\{[^}]*\}\s*$", "", t, flags=re.M)


def demote_headings(t: str) -> str:
    out, in_code = [], False
    for line in t.split("\n"):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if not in_code and re.match(r"^#{1,6}\s", line):
            line = "#" + line
        out.append(line)
    return "\n".join(out)


def namespace_labels(t: str, tag: str) -> str:
    keys = set(re.findall(r"\\label\{([^}]+)\}", t))
    for k in sorted(keys, key=len, reverse=True):
        nk = f"{tag}-{k}"
        t = t.replace("{" + k + "}", "{" + nk + "}")
        t = t.replace("[" + k + "]", "[" + nk + "]")
    return t


# --------------------------------------------------------------------------- #
# chapter-specific patches
# --------------------------------------------------------------------------- #
def patch_paper1(t: str) -> str:
    """Port the SHC plotting to the current mlsynth API and fix the data path."""
    t = t.replace('pd.read_excel("Data/HawaiiData.xlsx")',
                  'pd.read_excel("../Paper1/Paper/Data/HawaiiData.xlsx")')
    t = t.replace('pd.read_excel("Data/HawaiiTaxData.xlsx")',
                  'pd.read_excel("../Paper1/Paper/Data/HawaiiTaxData.xlsx")')
    t = t.replace(
        '''    # Extract vectors
    vectors = result.raw_results["Vectors"]
    observed = vectors["Observed Unit"]
    counterfactual = vectors["Counterfactual"]
    gap = vectors["Gap"][:, 1]

    plot_data[outcome] = {
        "time": gap,
        "observed": observed,
        "counterfactual": counterfactual
    }''',
        '''    # Extract vectors (current mlsynth SHCResults API)
    observed = np.asarray(result.observed, dtype=float).ravel()
    counterfactual = np.asarray(result.counterfactual, dtype=float).ravel()
    tindex = result.inputs.m   # window = m pre + n post; post begins at index m

    plot_data[outcome] = {
        "tindex": tindex,
        "observed": observed,
        "counterfactual": counterfactual
    }''')
    t = t.replace(
        '''    time = np.arange(len(data_dict["observed"]))
    treatment_index = np.where(data_dict["time"] == 0)[0][0]''',
        '''    time = np.arange(len(data_dict["observed"]))
    treatment_index = data_dict["tindex"]''')
    t = t.replace(
        '''    # Add prediction interval if available
    inference = results[outcome].inference
    if inference and inference.details:
        interval = inference.details.get("full_interval")
        if interval is not None and interval.size > 0:
            lower, upper = interval[:, 0], interval[:, 1]
            valid = ~(np.isnan(lower) | np.isnan(upper))
            if np.any(valid):
                ax.fill_between(time[valid], lower[valid], upper[valid], color="gray", alpha=0.25,
                                label="Conformal 90% Interval")''',
        '''    # Add conformal prediction interval if available (post-period bands)
    inf = results[outcome].inference_detail
    if inf is not None and getattr(inf, "conformal_lower", None) is not None:
        lower = np.asarray(inf.conformal_lower, dtype=float).ravel()
        upper = np.asarray(inf.conformal_upper, dtype=float).ravel()
        xs = np.arange(treatment_index, treatment_index + len(lower))
        valid = ~(np.isnan(lower) | np.isnan(upper))
        if np.any(valid):
            ax.fill_between(xs[valid], lower[valid], upper[valid], color="gray", alpha=0.25,
                            label="Conformal 90% Interval")''')
    return t


INDIA_RESULTS = r'''

## Results
\label{p2-sec:results}

@fig-india-national presents the Synthetic Historical Control estimate for the
all-India population-weighted PM2.5 series, expressed as a year-over-year growth
rate. The observed series falls sharply below its synthetic-historical
counterfactual following the March 2020 lockdown, indicating a pronounced
short-run reduction in particulate pollution. @fig-india-cities repeats the
exercise for the four megacities (Delhi, Mumbai, Bangalore, and Kolkata).

```{python}
#| echo: false
#| label: fig-india-national
#| fig-cap: "Synthetic Historical Control: all-India year-over-year PM2.5 growth, observed versus counterfactual. The dashed line marks the March 2020 national lockdown."
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from mlsynth import SHC
import warnings; warnings.filterwarnings("ignore")

_PARQUET = "../Paper2/Paper/av_pm2.5_ind_blk_mth_1998_2023_wide.parquet"
_df = pd.read_parquet(_PARQUET)
_mcols = [c for c in _df.columns if c.startswith("avg_pm2.5_")]
_months = {m: i for i, m in enumerate(
    ["january","february","march","april","may","june","july","august",
     "september","october","november","december"], start=1)}
def _date(c):
    _, _, y, mo = c.split("_"); return pd.Timestamp(int(y), _months[mo], 1)
_mcols = sorted(_mcols, key=_date)
_dates = pd.DatetimeIndex([_date(c) for c in _mcols])

def _popwt(rows):
    pop = rows["subdistrict_population"].to_numpy(float)
    Y = rows[_mcols].to_numpy(float)
    w = np.where(np.isnan(pop), 0.0, pop)[:, None]
    return np.nansum(Y*w, axis=0) / np.where(np.isnan(Y), 0.0, w).sum(axis=0)

def _yoy(levels):
    return (levels[12:] - levels[:-12]) / levels[:-12]

LOCK, END = pd.Timestamp("2020-03-01"), pd.Timestamp("2020-12-01")
def _panel(rows, name):
    g = _yoy(_popwt(rows)); gd = _dates[12:]
    p = pd.DataFrame({"time": gd, "unit": name, "y": g})
    p = p[p["time"] <= END].reset_index(drop=True)
    p["treated"] = (p["time"] >= LOCK).astype(int)
    return p

def _fit_plot(ax, panel, title):
    res = SHC({"df": panel, "outcome": "y", "treat": "treated", "unitid": "unit",
               "time": "time", "m": 24, "use_augmented": False,
               "display_graphs": False}).fit()
    cf = np.asarray(res.counterfactual, float).ravel()
    t = panel["time"]; tcf = t.iloc[-len(cf):]
    ax.plot(t, panel["y"], color="black", lw=1.1, label="Observed")
    ax.plot(tcf, cf, color="C3", ls="--", lw=1.4, label="SHC counterfactual")
    ax.axvline(LOCK, color="grey", ls=":", lw=1); ax.axhline(0, color="grey", lw=0.5)
    ax.set_title(f"{title}: ATT = {100*res.effects.att:+.1f} pp", fontsize=10)
    ax.set_ylabel("YoY PM2.5 growth", fontsize=8); ax.legend(fontsize=7)

fig, ax = plt.subplots(figsize=(9, 3.6))
_fit_plot(ax, _panel(_df, "India"), "India (national)")
fig.tight_layout(); plt.show()
```

```{python}
#| echo: false
#| label: fig-india-cities
#| fig-cap: "Synthetic Historical Control for the four megacities: observed versus counterfactual year-over-year PM2.5 growth."
_CITY = {"Delhi": ["new delhi"], "Mumbai": ["mumbai", "mumbai suburban"],
         "Bangalore": ["bangalore"], "Kolkata": ["kolkata"]}
fig, axes = plt.subplots(2, 2, figsize=(10, 6.4)); axes = axes.flatten()
for ax, (city, dist) in zip(axes, _CITY.items()):
    rows = _df[_df["district_name"].astype(str).str.lower().isin(dist)]
    _fit_plot(ax, _panel(rows, city), city)
fig.tight_layout(); plt.show()
```
'''

PAPER3_FIGURE = (
    "\n@fig-threecity visualizes the pooled estimate in Table~\\ref{p3-tab:main}: "
    "the synthetic difference-in-differences fit across the three treated cities "
    "under staggered adoption (New York City and San Francisco from August 2021, "
    "Los Angeles from November 2021).\n\n"
    "![Pooled synthetic difference-in-differences fit across the three treated "
    "cities (New York City, San Francisco, Los Angeles) under staggered adoption. "
    "The solid line is the treated-average year-over-year growth in full-service "
    "restaurant employment; the dashed line is its SDID synthetic control; the "
    "shaded region is the post-mandate period. The pooled SDID ATT is $+5.8$ and "
    "the PPSCM ATT is $+3.7$ percentage points, both positive and in the range of "
    "the estimates in Table~\\ref{p3-tab:main}.]"
    "(ch3_threecity.png){#fig-threecity}\n\n"
)


def build_chapter(stem, path, tag, title):
    t = pathlib.Path(path).read_text()
    t = strip_yaml(t)
    t = strip_bibcmds(t)
    t = demote_headings(t)
    t = namespace_labels(t, tag)
    if tag == "p1":
        t = patch_paper1(t)
    if tag == "p2":
        t = t.rstrip() + "\n" + INDIA_RESULTS
    if tag == "p3":
        t = t.replace("uporigin.OKPANI20241065", "OKPANI20241065")
        t = t.replace("## Discussion", PAPER3_FIGURE + "## Discussion", 1)
    body = f"# {title}\n\n" + t.lstrip("\n")
    (HERE / "chapters" / f"{stem}.qmd").write_text(body)
    return stem


# --------------------------------------------------------------------------- #
# bibliography copy + repair
# --------------------------------------------------------------------------- #
def fix_braces(text: str) -> str:
    pos = [m.start() for m in re.finditer(r"@\w+\s*\{", text)] + [len(text)]
    out = [text[:pos[0]]]
    for i in range(len(pos) - 1):
        chunk = text[pos[i]:pos[i + 1]]
        depth, closed = 0, False
        for ch in chunk:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    closed = True
                    break
        if not closed:
            chunk = chunk.rstrip() + "\n}\n\n"
        out.append(chunk)
    return "".join(out)


MISSING_REFS = r"""

@article{Arkhangelsky2021,
  author  = {Arkhangelsky, Dmitry and Athey, Susan and Hirshberg, David A. and Imbens, Guido W. and Wager, Stefan},
  title   = {Synthetic Difference-in-Differences}, journal = {American Economic Review},
  volume  = {111}, number = {12}, pages = {4088--4118}, year = {2021}, doi = {10.1257/aer.20190159}
}
@article{BenMichael2022,
  author  = {Ben-Michael, Eli and Feller, Avi and Rothstein, Jesse},
  title   = {The Augmented Synthetic Control Method}, journal = {Journal of the American Statistical Association},
  volume  = {116}, number = {536}, pages = {1789--1803}, year = {2021}, doi = {10.1080/01621459.2021.1929245}
}
@article{Clarke2023,
  author  = {Clarke, Damian and Pailañir, Daniel and Athey, Susan and Imbens, Guido},
  title   = {Synthetic Difference in Differences Estimation}, journal = {arXiv preprint arXiv:2301.11859}, year = {2023}
}
@article{Ciccia2024,
  author  = {Ciccia, Diego},
  title   = {A Short Note on Event-Study Synthetic Difference-in-Differences Estimators},
  journal = {arXiv preprint arXiv:2407.09565}, year = {2024}
}
"""


def build_bibs():
    for src, name in BIBS.items():
        text = fix_braces(pathlib.Path(src).read_text())
        if name == "ktc.bib":
            for key in ("Arkhangelsky2021", "BenMichael2022", "Clarke2023", "Ciccia2024"):
                if f"{{{key}," not in text:
                    text += MISSING_REFS
                    break
        (HERE / name).write_text(text)


if __name__ == "__main__":
    (HERE / "chapters").mkdir(exist_ok=True)
    for stem, (path, tag, title) in SRC.items():
        print("chapter:", build_chapter(stem, path, tag, title))
    build_bibs()
    print("bibs:", ", ".join(BIBS.values()))
    print("done.")
