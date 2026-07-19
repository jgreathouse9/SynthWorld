"""One-draw Monte Carlo: a common factor 'wakes up' in the post period.

A minimal illustration of the identification problem in the Hawaii paper. We
simulate a clean factor model in which the treated unit's loadings lie in the
donor span, so synthetic control fits the pre-period well and would be unbiased
for the ATT. Then, at the treatment date, a brand-new common factor switches on.
It loads on EVERYONE (donors included), so it is a genuine common factor, not a
treated-only shock. The bias arises anyway: the SCM weights are learned on the
pre-period, where this factor is absent, so they reproduce the treated unit's
loadings on the OLD factors but cannot be chosen to reproduce its loading on the
NEW one. What survives is the loading mismatch on the new factor,
(mu_1,new - sum_j w_j mu_j,new) * lambda_new, i.e. the factor-mismatch term of
eq:scm-bias. We cannot match to the factor because it was never in the pre-period.

Run:  pip install numpy cvxpy   then   python factor_wakes_up.py
"""
import numpy as np
import cvxpy as cp

rng = np.random.default_rng(0)          # one draw, fixed seed

# ---- dimensions ----
N0, T0, n, r = 5, 60, 10, 3             # donors, pre months, post months, factors
T = T0 + n

# ---- pre-existing factor model (present in both pre and post) ----
Lam = rng.normal(size=(T, r))                     # lambda_t: common factors
mu0 = rng.uniform(0.5, 1.5, size=(N0, r))         # mu_j: donor loadings
a   = rng.dirichlet(np.ones(N0))                  # convex weights...
mu1 = a @ mu0                                      # ...so treated loadings lie IN the donor span

e0  = rng.normal(scale=0.3, size=(T, N0))
e1  = rng.normal(scale=0.3, size=T)

# ---- the NEW common factor that wakes up at treatment ----
g = np.zeros(T)
g[T0:] = rng.normal(loc=-1.0, scale=0.2, size=n)   # active only in the post period
FS = 40.0                                          # its scale
b0 = rng.uniform(0.4, 1.0, size=N0)                # donor loadings on the new factor (all > 0)
b1 = 1.3                                           # treated loads on it too, more heavily

# ---- the true policy effect ----
tau = -20.0
d = (np.arange(T) >= T0).astype(float)

# ---- observed outcomes: base factors + new common factor (on everyone) + policy ----
Y0 = Lam @ mu0.T + FS * np.outer(g, b0)                 + e0        # donors DO move with it
y1 = Lam @ mu1   + FS * g * b1        + tau * d         + e1        # treated: + new factor + policy

# ---- synthetic control: fit weights on the PRE-period only (cvxpy) ----
w = cp.Variable(N0, nonneg=True)
cp.Problem(cp.Minimize(cp.sum_squares(y1[:T0] - Y0[:T0] @ w)), [cp.sum(w) == 1]).solve()
w_hat = w.value

# ---- counterfactual, fit quality, estimated ATT ----
cf       = Y0 @ w_hat
pre_rmse = np.sqrt(np.mean((y1[:T0] - cf[:T0]) ** 2))
att_hat  = np.mean(y1[T0:] - cf[T0:])

# ---- decompose the new factor's effect through the LOADINGS ----
gbar          = g[T0:].mean()
on_treated    = FS * gbar * b1                 # new factor as it hits the treated unit
on_wtd_donors = FS * gbar * (w_hat @ b0)       # ...as the weighted donor pool reproduces it
loading_gap   = b1 - w_hat @ b0                # mu_1,new - sum_j w_j mu_j,new  (nonzero: fit pre-period)

print(f"pre-treatment RMSE            : {pre_rmse:7.3f}   (small: the counterfactual looks credible)")
print(f"true policy effect (ATT)      : {tau:7.2f}")
print(f"new factor loads on donors too: b0 = {np.round(b0,2)}   (all > 0)")
print(f"  new factor on treated       : {on_treated:7.2f}")
print(f"  captured by weighted donors : {on_wtd_donors:7.2f}   (donors DO carry part of it)")
print(f"  loading mismatch (b1 - w.b0): {loading_gap:7.3f}   (pre-period weights can't match the new loading)")
print(f"SCM estimated ATT             : {att_hat:7.2f}")
print(f"bias  (estimated - true)      : {att_hat - tau:7.2f}   = mismatch x factor, not a donor-only shock")
