#!/usr/bin/env python3
"""Assemble the canonical RAW-level long panel for the Hawaii (SPSC) chapter.

One output, ``Data/hawaii_raw_long.csv``, with columns

    unit, time, value, role, group, units

holding *raw levels* (not growth rates): the paper differences to year-over-year
growth at runtime so the repository retains the underlying values. Sources, all
public and stored alongside this script in ``Data/``:

* ``DBEDT_visitor.xlsx`` -- DBEDT visitor arrivals and visitor days (SA).
* ``DBEDT_hotel.xlsx``   -- DBEDT hotel occupancy, average daily rate, and RevPAR
  (SA where applicable), statewide and by island and hotel class.
* ``LFR_CES_SADJ.xls``   -- State CES seasonally-adjusted job counts, the five
  insulated-sector negative-control donors.
* ``open_destinations.csv`` -- BTS-derived open-destination air-travel donors,
  already expressed as YoY growth (units == 'pct_yoy', passed through as-is).

Units drive the runtime transform: level units (percent/dollar/days/persons/jobs)
are differenced to YoY growth; 'pct_yoy' passes through.
"""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "Data"
OUT = DATA / "hawaii_raw_long.csv"


def _dbedt_reader(path: Path):
    """Return row(r) -> monthly Series for a DBEDT wide sheet (row 1 = YYYY-MM)."""
    raw = pd.read_excel(path, header=None)
    mcols = [(c, str(raw.iloc[1, c])) for c in range(3, raw.shape[1])
             if re.match(r"\d{4}-\d{2}$", str(raw.iloc[1, c]))]
    idx = pd.to_datetime([m + "-01" for _, m in mcols])

    def row(r: int) -> pd.Series:
        v = pd.to_numeric(pd.Series([raw.iloc[r, c] for c, _ in mcols]), errors="coerce")
        return pd.Series(v.values, index=idx)
    return row


def _ces_reader(path: Path):
    """Return col(i) -> monthly Series for the CES 'SA STATE series' sheet.

    The sheet labels months inconsistently ("Jun."/"Jun"/"June"), so months are
    matched on the first three letters rather than an exact table.
    """
    ce = pd.read_excel(path, sheet_name="SA STATE series", header=None)
    mon = {m: i for i, m in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

    def col(c: int) -> pd.Series:
        idx = []; val = []; cur = None
        for r in range(7, ce.shape[0]):
            a = str(ce.iloc[r, 0]).strip()
            ay = a.replace('.0', '')
            if ay.isdigit() and len(ay) == 4:
                cur = int(ay)
            else:
                mi = mon.get(a.rstrip('.').lower()[:3])
                if mi is not None and cur is not None:
                    idx.append(pd.Timestamp(cur, mi, 1))
                    val.append(pd.to_numeric(ce.iloc[r, c], errors="coerce"))
        return pd.Series(val, index=idx)
    return col


def build() -> pd.DataFrame:
    d5 = _dbedt_reader(DATA / "DBEDT_visitor.xlsx")   # visitor days / arrivals (SA)
    dn = _dbedt_reader(DATA / "DBEDT_hotel.xlsx")     # occ / adr / revpar (+ islands, tiers)
    ce = _ces_reader(DATA / "LFR_CES_SADJ.xls")       # insulated-sector job counts (SA)

    # variable -> (raw Series, role, group, units)
    spec = {
        # statewide tourism outcomes (SA)
        "Visitor Days":               (d5(18), "outcome", "tourism", "days"),
        "Visitor Arrivals":           (d5(7),  "outcome", "tourism", "persons"),
        "Occupancy":                  (dn(25), "outcome", "tourism", "percent"),
        "Mean Daily Rate":            (dn(53), "outcome", "tourism", "dollar"),
        "Revenue per Available Room": (dn(58), "outcome", "tourism", "dollar"),
        # island incidence
        "Occupancy_Oahu": (dn(26), "outcome", "island", "percent"),
        "Occupancy_Maui": (dn(27), "outcome", "island", "percent"),
        "Occupancy_HawaiiIsl": (dn(28), "outcome", "island", "percent"),
        "Occupancy_Kauai": (dn(29), "outcome", "island", "percent"),
        "ADR_Oahu": (dn(54), "outcome", "island", "dollar"),
        "ADR_Maui": (dn(55), "outcome", "island", "dollar"),
        "ADR_HawaiiIsl": (dn(56), "outcome", "island", "dollar"),
        "ADR_Kauai": (dn(57), "outcome", "island", "dollar"),
        "RevPAR_Oahu": (dn(59), "outcome", "island", "dollar"),
        "RevPAR_Maui": (dn(60), "outcome", "island", "dollar"),
        "RevPAR_HawaiiIsl": (dn(61), "outcome", "island", "dollar"),
        "RevPAR_Kauai": (dn(62), "outcome", "island", "dollar"),
        # hotel-class incidence (RevPAR)
        "RevPAR_Luxury": (dn(63), "outcome", "class", "dollar"),
        "RevPAR_UpperUpscale": (dn(67), "outcome", "class", "dollar"),
        "RevPAR_Upscale": (dn(70), "outcome", "class", "dollar"),
        "RevPAR_UpperMidscale": (dn(73), "outcome", "class", "dollar"),
        "RevPAR_MidscaleEconomy": (dn(76), "outcome", "class", "dollar"),
        # insulated-sector donors (CES SA job counts)
        "Financial_Emp": (ce(15), "donor", "insulated", "jobs"),
        "Government_Emp": (ce(29), "donor", "insulated", "jobs"),
        "HealthCare_Emp": (ce(24), "donor", "insulated", "jobs"),
        "NatRes_Constr_Emp": (ce(6), "donor", "insulated", "jobs"),
        "Wholesale_Emp": (ce(11), "donor", "insulated", "jobs"),
    }

    rows = []
    for unit, (s, role, grp, units) in spec.items():
        for t, v in s.dropna().items():
            rows.append((unit, t, float(v), role, grp, units))

    # open-destination donors: already YoY growth -> passthrough
    od = pd.read_csv(DATA / "open_destinations.csv", parse_dates=["Date"])
    for u in ["Florida", "Tampa", "Orlando", "Phoenix"]:
        for t, v in od.set_index("Date")[u].dropna().items():
            rows.append((u, t, float(v), "donor", "travel-demand", "pct_yoy"))

    panel = (pd.DataFrame(rows, columns=["unit", "time", "value", "role", "group", "units"])
             .sort_values(["group", "unit", "time"]))
    return panel


if __name__ == "__main__":
    panel = build()
    panel.to_csv(OUT, index=False)
    print(f"wrote {OUT}  ({panel.unit.nunique()} units, {len(panel)} rows, "
          f"{panel.time.min().date()}..{panel.time.max().date()})")
