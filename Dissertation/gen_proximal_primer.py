"""Pre-render the "Gentle Introduction to Proximal Inference" simulation figure.

A dissertation-only teaching device (Chapter 1). It stages a synthetic
Hawaii-like world where the *true* border-closure policy effect is known
(-15 points), lets a coincident pandemic ride along, and races four estimators
so a reader can *see* which one recovers the policy:

  * SHC (own history)               -- blind to the pandemic, overstates.
  * SCM on contaminated donors       -- donors also shut down, understates to ~0.
  * SPSC with internal proxies only  -- nets the macro recession, misses travel.
  * SPSC + Florida (external proxy)  -- exposed to the pandemic but never closed;
                                        recovers the true effect.

Run in CI (Dissertation.yml) exactly like ``gen_ch3_threecity.py``: it writes
``proximal_primer.png`` into the Dissertation render root and prints the Monte
Carlo means to the build log. The figure is embedded by ``build_chapters.py``.

Requires: mlsynth, numpy, pandas, matplotlib.
"""
import warnings
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mlsynth import VanillaSC, PROXIMAL, SHC

warnings.filterwarnings("ignore")

# mlsynth house plotting style: black observed, the red/blue/green/... cycle, a
# faint Samsung-blue grid, no spines -- the same look as the Chapter 1 figures.
CF = ("red", "blue", "green", "purple", "orange", "brown")
MLSYNTH_RC = {
    "figure.dpi": 100, "savefig.dpi": 130, "figure.facecolor": "white",
    "axes.grid": True, "grid.linestyle": "-", "grid.alpha": 0.40, "grid.color": "#1428A0",
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Arial", "Helvetica", "DejaVu Sans"],
    "font.weight": "medium",
    "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.labelsize": 13, "axes.labelweight": "medium",
    "xtick.labelsize": 11, "ytick.labelsize": 11,
    "legend.frameon": True, "legend.framealpha": 1, "legend.facecolor": "white",
    "legend.edgecolor": "#DDDDDD", "legend.fontsize": 11,
    "lines.linewidth": 1, "lines.antialiased": True,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
}
try:
    from mlsynth.utils.plotting import apply_mlsynth_style
    apply_mlsynth_style()
except Exception:
    plt.rcParams.update(MLSYNTH_RC)

TRUE_POLICY = -15.0


def simulate(seed, T0=60, T1=12, tau=TRUE_POLICY):
    """One draw of the two-factor (macro + travel) world.

    Returns observed Hawaii, its true (pandemic-only) counterfactual, the donor
    blocks, and the split point.
    """
    rng = np.random.default_rng(seed)
    T = T0 + T1

    def factor(post_lo, post_hi):
        f = np.zeros(T)
        for k in range(1, T):
            f[k] = 0.6 * f[k - 1] + rng.normal(0, 1.0)     # AR(1): active pre-period
        f[T0:] += -np.linspace(post_lo, post_hi, T1)       # extreme post draw = the pandemic
        return f

    Lmac = factor(3.5, 2.5)    # macro-recession coordinate
    Ltrv = factor(5.5, 3.5)    # travel-demand coordinate

    def unit(a, b, pol=0.0, sd=1.0):
        return 100 + a * Lmac + b * Ltrv + pol * (np.arange(T) >= T0) + rng.normal(0, sd, T)

    Y0 = 100 + 3 * Lmac + 6 * Ltrv                         # Hawaii WITHOUT the closure (pandemic only)
    Y = Y0 + tau * (np.arange(T) >= T0) + rng.normal(0, 0.8, T)

    internal = [unit(rng.uniform(2, 4), 0.0) for _ in range(5)]       # valid: macro only, no travel, no policy
    florida = unit(3.0, 5.0)                                          # valid EXTERNAL: macro+travel, NO closure
    invalid = [unit(3.0, 5.0, pol=rng.uniform(-14, -11)) for _ in range(4)]  # contaminated: also shut down
    return Y, Y0, internal, florida, invalid, T0, T1


def _df(Y, donors, names, T):
    rows = [{"unit": "Hawaii", "t": k, "y": Y[k], "closure": int(k >= T - 12)} for k in range(T)]
    for nm, s in zip(names, donors):
        rows += [{"unit": nm, "t": k, "y": s[k], "closure": 0} for k in range(T)]
    return pd.DataFrame(rows)


def att_shc(Y, T):
    df = pd.DataFrame({"unit": "Hawaii", "t": np.arange(T), "y": Y,
                       "closure": (np.arange(T) >= T - 12).astype(int)})
    r = SHC({"df": df, "outcome": "y", "treat": "closure", "unitid": "unit",
             "time": "t", "display_graphs": False}).fit()
    return r.effects.att, r


def att_scm(df):
    r = VanillaSC({"df": df, "outcome": "y", "treat": "closure", "unitid": "unit",
                   "time": "t", "display_graphs": False}).fit()
    return r.effects.att, r


def att_spsc(df, donors):
    r = PROXIMAL({"df": df, "outcome": "y", "treat": "closure", "unitid": "unit",
                  "time": "t", "donors": donors, "methods": ["SPSC"],
                  "display_graphs": False}).fit().methods["SPSC"]
    return r.att, r


def run_monte_carlo(n=15):
    intn = [f"job{j}" for j in range(5)]
    rows = []
    for s in range(n):
        Y, Y0, internal, florida, invalid, T0, T1 = simulate(s)
        T = T0 + T1
        a_shc, _ = att_shc(Y, T)
        a_scm, _ = att_scm(_df(Y, invalid, [f"state{j}" for j in range(4)], T))
        a_spn, _ = att_spsc(_df(Y, internal, intn, T), intn)
        a_sp, _ = att_spsc(_df(Y, internal + [florida], intn + ["Florida"], T), intn + ["Florida"])
        rows.append((a_shc, a_scm, a_spn, a_sp))
    r = np.array(rows)
    print(f"Monte Carlo means over {n} draws (true policy = {TRUE_POLICY:+.0f}):", flush=True)
    print(f"  SHC (own history)          {r[:, 0].mean():+.1f}   [overstates -- blind to pandemic]", flush=True)
    print(f"  SCM (contaminated donors)  {r[:, 1].mean():+.1f}   [understates -> ~0]", flush=True)
    print(f"  SPSC (internal only)       {r[:, 2].mean():+.1f}   [under-corrects -- misses travel]", flush=True)
    print(f"  SPSC (internal + Florida)  {r[:, 3].mean():+.1f}   [recovers]", flush=True)
    return r.mean(axis=0)


def make_figure(seed=3, path="proximal_primer.png"):
    Y, Y0, internal, florida, invalid, T0, T1 = simulate(seed)
    T = T0 + T1
    t = np.arange(T)
    intn = [f"job{j}" for j in range(5)]

    a_shc, shc = att_shc(Y, T)
    a_scm, scm = att_scm(_df(Y, invalid, [f"state{j}" for j in range(4)], T))
    a_spn, _ = att_spsc(_df(Y, internal, intn, T), intn)
    a_sp, sp = att_spsc(_df(Y, internal + [florida], intn + ["Florida"], T), intn + ["Florida"])

    def tail(cf):
        cf = np.asarray(cf, dtype=float).ravel()
        return t[T - len(cf):], cf

    fig, (ax, axb) = plt.subplots(1, 2, figsize=(14, 5.4),
                                  gridspec_kw={"width_ratios": [2.1, 1]})
    # donor clouds: contaminated (that also shut down) vs valid internal proxies
    for j, s in enumerate(invalid):
        ax.plot(t, s, color="#d98b7a", lw=0.7, alpha=0.7,
                label="contaminated donors\n(also shut down)" if j == 0 else None)
    for j, s in enumerate(internal):
        ax.plot(t, s, color="#b8c4b8", lw=0.7, alpha=0.8,
                label="internal proxies\n(insulated sectors)" if j == 0 else None)
    ax.plot(t, florida, color="grey", lw=1.1, ls=":", label="Florida (external proxy)")
    ax.axvline(T0 - .5, color="grey", ls=":", lw=1.2)
    ax.plot(t, Y, color="black", lw=2.4, label="Hawaii (observed)")
    ax.plot(t, Y0, color=CF[2], lw=2.4, ls="--", label="true counterfactual")
    ax.plot(*tail(shc.time_series.counterfactual_outcome), color=CF[0], lw=1.9,
            label=f"SHC own-history (ATT {a_shc:+.0f})")
    ax.plot(*tail(scm.time_series.counterfactual_outcome), color=CF[4], lw=1.7,
            label=f"SCM contaminated (ATT {a_scm:+.0f})")
    ax.plot(*tail(sp.counterfactual), color=CF[1], lw=2.0,
            label=f"SPSC + Florida (ATT {a_sp:+.0f})")
    ax.set_title("Separating the border-closure policy from the pandemic", loc="left")
    ax.set_xlabel("month"); ax.set_ylabel("tourism index")
    ax.legend(fontsize=8, loc="lower left", ncol=2)

    labs = ["SHC\n(own hist.)", "SCM\n(contam.)", "SPSC\n(internal)", "SPSC\n+ Florida"]
    vals = [a_shc, a_scm, a_spn, a_sp]
    cols = [CF[0], CF[4], CF[3], CF[1]]
    axb.bar(labs, vals, color=cols)
    axb.axhline(TRUE_POLICY, color=CF[2], ls="--", lw=2, label=f"true policy = {TRUE_POLICY:+.0f}")
    axb.axhline(0, color="black", lw=0.8)
    for i, v in enumerate(vals):
        axb.text(i, v - 2.4, f"{v:+.0f}", ha="center", va="top", fontsize=9)
    axb.set_title("Estimated policy effect", loc="left")
    axb.set_ylabel("ATT"); axb.legend(fontsize=9, loc="lower center")
    plt.tight_layout()
    plt.savefig(path)
    plt.close(fig)
    print(f"\nSAVED {path}", flush=True)
    print(f"single draw (seed {seed}): SHC {a_shc:+.0f} | SCM {a_scm:+.0f} | "
          f"SPSC(int) {a_spn:+.0f} | SPSC+FL {a_sp:+.0f}", flush=True)
    return dict(shc=a_shc, scm=a_scm, spsc_int=a_spn, spsc_fl=a_sp)


if __name__ == "__main__":
    # The embedded figure needs only make_figure(); the Monte Carlo (~60 fits)
    # merely reprints the averages quoted in the chapter, so it is opt-in to keep
    # the CI render fast. Set PRIMER_MONTE_CARLO=1 to reproduce the means.
    import os
    if os.environ.get("PRIMER_MONTE_CARLO"):
        run_monte_carlo(n=15)
    make_figure(seed=3)
