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
2. Florida inbound air travel -- the no-lockdown travel-demand donor. Monthly
   arriving-flight counts across Florida airports from the BTS Airline On-Time
   Performance table, scraped to
   ``jgreathouse9/ScrapersData`` (``On Time Performance/.../final_combined_data.csv``),
   aggregated statewide and converted to YoY growth here.

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
FLORIDA_CACHE = os.path.join(DATA, "florida_arrivals.csv")  # small derived cache

TREAT_FLAG = "Mandatory Quarantine"

TOURISM = ["Visitor Arrivals", "Visitor Days", "Occupancy", "Mean Daily Rate",
           "Revenue per Available Room", "Accommodation Emp"]
ECON = ["Total Leisure Emp", "Unemp Rate", "LFP", "Econ Activity Index"]
INSULATED = ["NatRes_Constr_Emp", "Wholesale_Emp", "Financial_Emp",
             "HealthCare_Emp", "Government_Emp"]


def florida_yoy() -> pd.DataFrame:
    """Return monthly Florida arriving-flights YoY growth (Date, Florida).

    Uses the small vendored cache if present; otherwise pulls the BTS scrape,
    sums arriving flights across Florida airports, and writes the cache.
    """
    if os.path.exists(FLORIDA_CACHE):
        return pd.read_csv(FLORIDA_CACHE, parse_dates=["Date"])
    if requests is None:
        raise RuntimeError("requests is unavailable and no florida_arrivals.csv cache exists")
    raw = pd.read_csv(io.StringIO(requests.get(BTS_URL, timeout=120).text))
    raw["state"] = raw["airport_name"].str.extract(r",\s*([A-Z]{2}):")
    fl = (raw[raw.state == "FL"]
          .groupby(["year", "month"])["arr_flights"].sum().reset_index())
    fl["Date"] = pd.to_datetime(dict(year=fl.year, month=fl.month, day=1))
    fl = fl.sort_values("Date").reset_index(drop=True)
    fl["Florida"] = (fl["arr_flights"] - fl["arr_flights"].shift(12)) / fl["arr_flights"].shift(12) * 100
    out = fl[["Date", "Florida"]].dropna().reset_index(drop=True)
    out.to_csv(FLORIDA_CACHE, index=False)
    return out


def build() -> pd.DataFrame:
    wide = pd.read_csv(WIDE_CSV, parse_dates=["Date"])
    fl = florida_yoy()

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
    add("Florida", "donor", "travel-demand", src=fl, col="Florida")

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
