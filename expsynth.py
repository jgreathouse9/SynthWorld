import numpy as np
from scexphelp import SCMEXP, inference_scm, simulate_linear_factor_model, plot_scm_inference
import cvxpy as cp

df = simulate_linear_factor_model()
Y = df.to_numpy()
clusters = np.repeat(np.arange(1), Y.shape[0])

N_units = Y.shape[0]
precard = 104-12

result = SCMEXP(
    Y_full=Y,
    T0=precard,
    clusters=clusters,
    blank_periods=Y.shape[1]-precard,
    m_min=2,
    m_max=4,
    solver=cp.ECOS_BB,
    verbose=False,
    design="eq11",
    lambda1=.02,
    lambda2=.02
)




# Grab treated unit indices
treated_units = np.where(result['w_opt'] > 1e-4)[0]
print(len(treated_units))
# Make a copy of Y to represent outcomes under treatment
Y_treat = Y.copy()

# Apply treatment effects (after the pretreatment cutoff)
treatment_effects = [12, 11, 16, 15]

for idx, unit in enumerate(treated_units):
    eff = treatment_effects[idx % len(treatment_effects)]  # cycle if fewer effects than units
    Y_treat[unit, precard:] += eff


infres = inference_scm(result,Y_treat,12,alpha=0.05,method='placebo')

plot_scm_inference(infres, overlay_clusters=False)
