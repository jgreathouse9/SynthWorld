import pickle, warnings, time, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from mlsynth import SDID, PPSCM

csa = pickle.load(open("../Paper3/Data/employment_growth_data.pkl", "rb"))["CSA"].copy()
dates = sorted(csa["Date"].unique()); dmap = {d: i for i, d in enumerate(dates)}
csa["t"] = csa["Date"].map(dmap).astype(int)
NYC = "NYC Area"; SF = "San Jose-San Francisco-Oakland, CA CSA"
NOLA = "New Orleans-Metairie-Slidell, LA-MS CSA"; LA = "Los Angeles-Long Beach, CA CSA"
NYNK = "New York-Newark, NY-NJ-CT-PA CSA"

# Staggered treatment: NYC & SF from Aug 2021, LA from Nov 2021. Drop NOLA (data
# availability, per the paper) and the duplicate New York-Newark CSA from donors.
mandate = {NYC: "2021-08-01", SF: "2021-08-01", LA: "2021-11-01"}
df = csa[~csa["CSA"].isin([NOLA, NYNK])].copy()
df["treated"] = 0
for u, m in mandate.items():
    df.loc[(df["CSA"] == u) & (df["Date"] >= pd.Timestamp(m)), "treated"] = 1
print("treated unit-periods:", int(df["treated"].sum()),
      "| treated units:", df[df.treated == 1]["CSA"].nunique(), flush=True)

# One staggered-adoption fit per estimator -> aggregate (pooled) ATT.
t0 = time.time()
rs = SDID(dict(df=df, outcome="YoY_Emp", treat="treated", unitid="CSA", time="Date",
               display_graphs=False, save=False, B=1)).fit()
rp = PPSCM(dict(df=df, outcome="YoY_Emp", treat="treated", unitid="CSA", time="t",
                display_graphs=False, save=False, run_inference=False)).fit()
print(f"SDID ATT={rs.effects.att:+.2f}pp  PPSCM ATT={rp.effects.att:+.2f}pp  ({time.time()-t0:.0f}s)", flush=True)

obs = np.asarray(rs.time_series.observed_outcome, float).ravel()
sd_cf = np.asarray(rs.time_series.counterfactual_outcome, float).ravel()
T = min(len(obs), len(sd_cf)); x = pd.to_datetime(dates[:T])

fig, ax = plt.subplots(figsize=(9.5, 4.4))
ax.plot(x, obs[:T], color="black", lw=1.5, label="Observed (treated average)")
ax.plot(x, sd_cf[:T], color="C0", ls="--", lw=1.6, label="SDID synthetic control")
ax.axvspan(pd.Timestamp("2021-08-01"), x.max(), color="grey", alpha=0.08)
ax.axvline(pd.Timestamp("2021-08-01"), color="grey", ls=":", lw=1)
ax.axhline(0, color="grey", lw=0.5)
ax.set_xlim(pd.Timestamp("2017-01-01"), x.max())
ax.set_ylabel("YoY full-service restaurant employment growth", fontsize=9)
ax.set_title(f"Pooled vaccine-mandate effect (NYC, SF, LA): "
             f"SDID ATT = {rs.effects.att:+.1f} pp, PPSCM ATT = {rp.effects.att:+.1f} pp",
             fontsize=10)
ax.legend(fontsize=8, loc="lower left")
fig.tight_layout()
fig.savefig("ch3_threecity.png", dpi=140)
print("SAVED ch3_threecity.png", flush=True)
