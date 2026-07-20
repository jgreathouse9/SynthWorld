#!/usr/bin/env python3
"""Assemble the canonical panel for the Texas / early-reopener Synthetic Interventions
chapter. One long CSV [unit, time, cases, deaths, temp, mob]:

* cases  -- RAW cumulative confirmed cases (NYT); the paper puts these in per-100k terms
  at runtime, so the repo keeps raw counts.
* deaths -- RAW cumulative deaths (NYT); the second outcome, run through the identical SI
  design in per-100k terms to price the reopening toll in lives, not just cases.
* temp   -- state-daily mean temperature (deg F), Bayat et al. county series averaged to
  state; an EXOGENOUS confounder (weather is not caused by reopening).
* mob    -- Apple driving-mobility index (Jan 13 2020 = 100), Bayat et al. mirror; a
  MEDIATOR of the reopening effect (reopening -> mobility -> cases), used to show the
  mechanism, never as an adjustment. Apple series ends 2020-06-14; carried forward.

States span the early reopeners (treated) and the shelter-in-place donor pool. Reopening
dates and 2019 populations (unit-level metadata) live in the paper harness, not this file.
"""
import io, os, urllib.request, pandas as pd, numpy as np

NYT   = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
TEMP  = "https://raw.githubusercontent.com/niloofarbayat/COVID19-synthetic-control-analysis/master/data/temperature/temp_data.csv"
APPLE = "https://raw.githubusercontent.com/niloofarbayat/COVID19-synthetic-control-analysis/master/data/mobility/applemobilitytrends-2020-05-30.csv"
START, END = "2020-02-15", "2020-06-30"
EARLY = ["Texas","Georgia","Florida","Arizona","South Carolina","Tennessee","Mississippi",
         "Alabama","Oklahoma","Colorado","Missouri"]
DONORS = ["California","Illinois","Kansas","Louisiana","Maryland","Michigan","Wisconsin",
          "New York","New Jersey","Pennsylvania","Massachusetts","Washington","Virginia",
          "Minnesota","Connecticut","New Mexico","Oregon"]      # SIP pool + proximal instruments
STATES = EARLY + DONORS

def _read(url, localname):
    local = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "scratchpad", localname)
    if os.path.exists(local): return pd.read_csv(local)
    with urllib.request.urlopen(url, timeout=180) as r: return pd.read_csv(io.BytesIO(r.read()))

def main():
    grid = pd.date_range(START, END, freq="D")
    # cases and deaths (raw cumulative, same NYT us-states file)
    c = _read(NYT, "nyt_us_states.csv"); c["date"] = pd.to_datetime(c["date"])
    cw = (c[c.state.isin(STATES)].pivot(index="date", columns="state", values="cases")
            .reindex(grid).ffill().fillna(0.0)[STATES])
    dw = (c[c.state.isin(STATES)].pivot(index="date", columns="state", values="deaths")
            .reindex(grid).ffill().fillna(0.0)[STATES])
    # temperature (county -> state-daily mean deg F)
    t = _read(TEMP, "bayat_temp.csv"); t["date"] = pd.to_datetime(t["date"])
    tw = (t[t.state.isin(STATES)].groupby(["state","date"])["avg_temperature"].mean().reset_index()
            .pivot(index="date", columns="state", values="avg_temperature")
            .reindex(grid).interpolate(limit=5).ffill().bfill()[STATES])
    # apple driving mobility (wide; sub-region rows; ends Jun-14 -> carry forward)
    a = _read(APPLE, "apple_mob.csv")
    a = a[(a.geo_type=="sub-region") & (a.transportation_type=="driving") & (a.region.isin(STATES))]
    dc = [x for x in a.columns if str(x).startswith("2020")]
    mw = a.set_index("region")[dc].T; mw.index = pd.to_datetime(mw.index)
    mw = mw.reindex(grid).interpolate(limit=5).ffill().bfill()[STATES]

    long = (cw.reset_index().rename(columns={"index":"time"}).melt(id_vars="time", var_name="unit", value_name="cases")
            .merge(dw.reset_index().rename(columns={"index":"time"}).melt(id_vars="time", var_name="unit", value_name="deaths"), on=["time","unit"])
            .merge(tw.reset_index().rename(columns={"index":"time"}).melt(id_vars="time", var_name="unit", value_name="temp"), on=["time","unit"])
            .merge(mw.reset_index().rename(columns={"index":"time"}).melt(id_vars="time", var_name="unit", value_name="mob"), on=["time","unit"]))
    long = long.sort_values(["unit","time"]).reset_index(drop=True)
    out = os.path.join(os.path.dirname(__file__), "..", "..", "Data", "si_panel.csv")
    long.to_csv(os.path.abspath(out), index=False)
    print(f"wrote {os.path.abspath(out)}: {long.shape[0]} rows, {long.unit.nunique()} states "
          f"({long.time.min().date()}..{long.time.max().date()}); "
          f"cases/deaths/temp/mob non-null: {long[['cases','deaths','temp','mob']].notna().all(axis=1).mean():.0%}")

if __name__ == "__main__":
    main()
