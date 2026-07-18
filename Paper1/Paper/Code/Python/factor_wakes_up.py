"""One-draw Monte Carlo: a common factor 'wakes up' in the post period.

A minimal illustration of the identification problem in the Hawaii paper. We
simulate a clean factor model in which the treated unit's loadings lie in the
donor span, so synthetic control fits the pre-period well and would be unbiased
for the ATT. Then, at the treatment date, a brand-new common factor switches on,
loading heavily on the treated unit but ~zero on the donors (the travel-demand
collapse). Because that factor never appears in the pre-period, the SCM weights
cannot anticipate it, and the estimated ATT absorbs the new factor on top of the
true policy effect. The gap is the factor-mismatch bias of eq:scm-bias.

Run:  pip install numpy cvxpy   then   python factor_wakes_up.py
"""
import numpy as np
import cvxpy as cp

rng = np.random.default_rng(0)          # one draw, fixed seed

# ---- dimensions ----
N0, T0, n, r = 5, 60, 10, 3             # donors, pre months, post months, factors
T = T0 + n

# ---- pre-existing factor model (both pre and post) ----
Lam = rng.normal(size=(T, r))                     # lambda_t: common factors
mu0 = rng.uniform(0.5, 1.5, size=(N0, r))         # mu_j: donor loadings
a   = rng.dirichlet(np.ones(N0))                  # convex weights...
mu1 = a @ mu0                                      # ...so treated loadings lie IN the donor span

e0  = rng.normal(scale=0.3, size=(T, N0))
e1  = rng.normal(scale=0.3, size=T)
Y0_clean = Lam @ mu0.T + e0                        # T x N0 donors
y1_clean = Lam @ mu1   + e1                        # treated untreated outcome y_1t^0

# ---- the NEW factor that wakes up at treatment ----
g = np.zeros(T)
g[T0:] = rng.normal(loc=-1.0, scale=0.3, size=n)   # active only in the post period
load_treated, load_donor = 50.0, 0.0               # heavy on treated, ~0 on donors

# ---- the true policy effect ----
tau = -20.0
d = (np.arange(T) >= T0).astype(float)

# ---- observed outcomes ----
Y0 = Y0_clean + np.outer(g, np.full(N0, load_donor))     # donors barely move
y1 = y1_clean + g * load_treated + tau * d               # treated: base + new factor + policy

# ---- synthetic control: fit weights on the PRE-period only (cvxpy) ----
w = cp.Variable(N0, nonneg=True)
cp.Problem(cp.Minimize(cp.sum_squares(y1[:T0] - Y0[:T0] @ w)), [cp.sum(w) == 1]).solve()
w_hat = w.value

# ---- counterfactual, fit quality, and estimated ATT ----
cf       = Y0 @ w_hat
pre_rmse = np.sqrt(np.mean((y1[:T0] - cf[:T0]) ** 2))
att_hat  = np.mean(y1[T0:] - cf[T0:])
newfac   = np.mean(g[T0:]) * load_treated                 # new factor's mean post contribution

print(f"pre-treatment RMSE          : {pre_rmse:7.3f}   (small: the counterfactual looks credible)")
print(f"true policy effect (ATT)    : {tau:7.2f}")
print(f"new post-period factor       : {newfac:7.2f}   (on treated; ~0 on donors)")
print(f"SCM estimated ATT           : {att_hat:7.2f}")
print(f"bias  (estimated - true)    : {att_hat - tau:7.2f}   ~= the new factor SCM could not match")
print(f"donor weights w_hat         : {np.round(w_hat, 3)}")
