"""Assemble the subgroup (distributional) panel for the Hawaii chapter.

The headline analysis treats statewide tourism outcomes. This panel disaggregates
those same hotel-performance outcomes -- Occupancy, average daily rate (ADR), and
revenue per available room (RevPAR) -- along two distributional axes so the
border-closure cost can be read by *who bore it*:

- ``island``  : the four counties (Oahu, Maui, Hawaii Island, Kauai), which differ
                sharply in how tourism-dependent their local economies are.
- ``class``   : hotel market segment (Luxury .. Midscale & Economy), available for
                RevPAR only, a proxy for which tier of the lodging market -- and the
                establishments and workers tied to it -- absorbed the shock.

Every treated series is the year-over-year % growth of the DBEDT Data Warehouse
hotel series, computed exactly as the statewide outcomes are (validated: the
Statewide-All Occupancy YoY reproduces the paper's ``Occupancy`` series to within
rounding). The donors are reused verbatim from ``hawaii_spsc_long.csv`` -- the same
five insulated-sector negative controls and the same open-destination travel-demand
donors -- so each subgroup is fit against an identical control set by the identical
proximal machinery. The treatment date (March 2020) is applied at fit time.

Output ``robustness.csv`` with columns ``unit, time, y, role, group``:
- ``role``  in {outcome, donor}
- ``group`` in {island, class, insulated, travel-demand}
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "Data"))
XLSX = os.path.join(DATA, "Hawaii_DBEDT_hotel_by_segment.xlsx")
LONG = os.path.join(DATA, "hawaii_spsc_long.csv")
OUT = os.path.join(DATA, "robustness.csv")

METRIC = {"Occupancy (SA)": "Occupancy", "Avg daily rate (SA)": "ADR", "RevPAR": "RevPAR"}
ISLAND = {"Oahu- All": "Oahu", "Maui CTY- All": "Maui",
          "Hawaii ISL- All": "HawaiiIsl", "Kauai- All": "Kauai"}
KLASS = {"Statewide- Luxury": "Luxury", "Statewide- Upper Upscale": "UpperUpscale",
         "Statewide- Upscale": "Upscale", "Statewide- Upper Midscale": "UpperMidscale",
         "Statewide- Midscale & Economy": "MidscaleEconomy"}


def _yoy(row: pd.Series) -> pd.Series:
    """Year-over-year % growth of one wide monthly level series."""
    s = pd.to_numeric(row.iloc[3:], errors="coerce")
    s.index = pd.to_datetime(s.index, format="%Y-%m", errors="coerce")
    s = s[s.index.notna()].sort_index()
    return (s / s.shift(12) - 1.0) * 100.0


def build() -> pd.DataFrame:
    raw = pd.read_excel(XLSX, sheet_name="Sheet1", header=1)
    raw = raw[raw["Indicator"].isin(METRIC)]

    rows = []
    for _, r in raw.iterrows():
        metric = METRIC[r["Indicator"]]
        cat = r["Category"]
        if cat in ISLAND:
            grp, sub = "island", ISLAND[cat]
        elif metric == "RevPAR" and cat in KLASS:
            grp, sub = "class", KLASS[cat]
        else:
            continue  # skip Statewide-All (the headline series) and unused submarkets
        y = _yoy(r).dropna()
        unit = f"{metric}_{sub}"
        rows.append(pd.DataFrame({"unit": unit, "time": y.index, "y": y.to_numpy(),
                                  "role": "outcome", "group": grp}))
    treated = pd.concat(rows, ignore_index=True)

    # Reuse the exact donor set from the headline panel (insulated + travel-demand).
    donors = pd.read_csv(LONG, parse_dates=["time"])
    donors = donors[donors["role"] == "donor"].copy()

    # The insulated donors end at the close of the analysis window (Dec 2020), as
    # the paper's statewide outcomes do; cap the treated subgroups there so every
    # fit frame is strongly balanced (the DBEDT workbook itself runs past 2024).
    lo = donors["time"].min()
    hi = donors.loc[donors["group"] == "insulated", "time"].max()
    treated = treated[(treated["time"] >= lo) & (treated["time"] <= hi)]

    panel = pd.concat([treated, donors], ignore_index=True)
    panel = panel.sort_values(["role", "group", "unit", "time"]).reset_index(drop=True)
    return panel


if __name__ == "__main__":
    panel = build()
    panel.to_csv(OUT, index=False)
    n_treat = panel[panel.role == "outcome"].unit.nunique()
    n_don = panel[panel.role == "donor"].unit.nunique()
    print(f"wrote {OUT}: {len(panel):,} rows, {n_treat} subgroup outcomes, {n_don} donors")
    print("subgroups:", sorted(panel[panel.role == "outcome"].unit.unique()))
