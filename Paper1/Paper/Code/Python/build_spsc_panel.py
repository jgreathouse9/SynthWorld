"""Assemble the canonical long-form SPSC panel for the Hawaii chapter.

One tidy file, one modeling variable (year-over-year % growth), every series in
one place, so the paper never re-pivots, re-sums, or re-merges: it loads the
long panel and fits. Re-run this script to regenerate the panel from source.

Sources
-------
1. ``hawaii_proximal_panel.csv`` -- the Hawaii treated outcomes and the five
   insulated-sector negative controls, already as YoY growth (built earlier
   from DBEDT tourism/labor series and the DBEDT seasonally-adjusted CES job
   count by industry).
2. Open-destination inbound air travel -- the no-lockdown travel-demand donors
   (Florida statewide plus the Tampa, Orlando, and Phoenix leisure metros, all
   in states that imposed no traveler quarantine). Monthly arriving-flight counts
   from the BTS Airline On-Time Performance table, scraped to
   ``jgreathouse9/ScrapersData`` (``On Time Performance/.../final_combined_data.csv``),
   aggregated (statewide or by airport) and converted to YoY growth here.

Output
------
``hawaii_spsc_long.csv`` with columns ``unit, time, y, role, group``:

- ``role``  in {outcome, donor}
- ``group`` in {tourism, econ-labor, insulated, travel-demand}

The treatment date (March 2020) is a documented constant, applied at fit time to
whichever outcome is treated -- it is not stored per row, because which series is
"treated" depends on the fit.
"""
from __future__ import annotations

import io
import os

import numpy as np
import pandas as pd

try:  # only needed when regenerating the Florida series from source
    import requests
except Exception:  # pragma: no cover
    requests = None

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "Data"))
WIDE_CSV = os.path.join(DATA, "hawaii_proximal_panel.csv")
OUT_CSV = os.path.join(DATA, "hawaii_spsc_long.csv")

BTS_URL = (
    "https://raw.githubusercontent.com/jgreathouse9/ScrapersData/refs/heads/main/"
    "On%20Time%20Performance/Python/final_combined_data.csv"
)
OPEN_CACHE = os.path.join(DATA, "open_destinations.csv")  # small derived cache

TREAT_FLAG = "Mandatory Quarantine"

# The external travel-demand donors: exposed-but-open destinations that felt the
# pandemic travel collapse but imposed no traveler quarantine. Florida is the
# statewide anchor; the three leisure metros (in open states) diversify and,
# unlike Florida-statewide, reach Hawaii's price/occupancy outcomes. Each is
# a separate donor unit so the paper can fit them one at a time (an ensemble
# added en masse is near-collinear and hurts the fit).
OPEN_DEST = {"Florida": ("state", "FL"), "Tampa": ("airport", "TPA"),
             "Orlando": ("airport", "MCO"), "Phoenix": ("airport", "PHX")}

TOURISM = ["Visitor Arrivals", "Visitor Days", "Occupancy", "Mean Daily Rate",
           "Revenue per Available Room", "Accommodation Emp"]
ECON = ["Total Leisure Emp", "Unemp Rate", "LFP"]
INSULATED = ["NatRes_Constr_Emp", "Wholesale_Emp", "Financial_Emp",
             "HealthCare_Emp", "Government_Emp"]


def open_destinations_yoy() -> pd.DataFrame:
    """Return monthly YoY arriving-flights growth for the open-destination donors.

    Columns: ``Date`` plus one per key of ``OPEN_DEST``. Uses the small vendored
    cache if present; otherwise pulls the BTS scrape once and builds every donor
    (statewide sums by the two-letter state in ``airport_name``; metros by
    airport code), then writes the cache.
    """
    if os.path.exists(OPEN_CACHE):
        return pd.read_csv(OPEN_CACHE, parse_dates=["Date"])
    if requests is None:
        raise RuntimeError("requests is unavailable and no open_destinations.csv cache exists")
    raw = pd.read_csv(io.StringIO(requests.get(BTS_URL, timeout=120).text))
    raw["state"] = raw["airport_name"].str.extract(r",\s*([A-Z]{2}):")
    raw["Date"] = pd.to_datetime(dict(year=raw.year, month=raw.month, day=1))
    lvl = pd.DataFrame({"Date": sorted(raw["Date"].unique())}).set_index("Date")
    for name, (kind, key) in OPEN_DEST.items():
        sub = raw[raw.state == key] if kind == "state" else raw[raw.airport == key]
        lvl[name] = sub.groupby("Date")["arr_flights"].sum()
    yoy = (lvl - lvl.shift(12)) / lvl.shift(12) * 100
    out = yoy.dropna(how="all").reset_index()
    out.to_csv(OPEN_CACHE, index=False)
    return out


def build() -> pd.DataFrame:
    wide = pd.read_csv(WIDE_CSV, parse_dates=["Date"])
    opendf = open_destinations_yoy()

    frames = []

    def add(series, role, group, src=wide, col=None):
        col = col or series
        s = src[["Date", col]].dropna().rename(columns={col: "y"})
        s["unit"], s["role"], s["group"] = series, role, group
        frames.append(s[["unit", "Date", "y", "role", "group"]])

    for oc in TOURISM:
        add(oc, "outcome", "tourism")
    for oc in ECON:
        add(oc, "outcome", "econ-labor")
    for d in INSULATED:
        add(d, "donor", "insulated")
    for name in OPEN_DEST:
        add(name, "donor", "travel-demand", src=opendf, col=name)

    long = (pd.concat(frames, ignore_index=True)
            .rename(columns={"Date": "time"})
            .sort_values(["role", "group", "unit", "time"])
            .reset_index(drop=True))
    return long


if __name__ == "__main__":
    long = build()
    long.to_csv(OUT_CSV, index=False)
    n_units = long.groupby(["role", "group"])["unit"].nunique()
    print(long.head().to_string(index=False))
    print("\nunits by role/group:\n", n_units.to_string())
    print(f"\nrows={len(long)}  span={long.time.min().date()}..{long.time.max().date()}")
    print(f"wrote {OUT_CSV}")
