import numpy as np
import matplotlib.pyplot as plt
import cvxpy as cp
import pandas as pd
from scipy.linalg import eigh
from concurrent.futures import ThreadPoolExecutor

# SHC Estimator
def shc_estimator(y, m, T0, bandwidth=0.8, varsigma=1e-6, tol=1e-8):
    T = len(y)
    n = T - T0
    N = T0 - m - n + 1
    if N <= 0:
        raise ValueError("Insufficient pre-treatment data to construct donor pool.")

    def smooth(y_pre, bw):
        T_pre = len(y_pre)
        smoothed = np.zeros(T_pre)
        for i in range(T_pre):
            w = np.exp(-0.5 * ((np.arange(T_pre) - i) / bw) ** 2)
            w /= w.sum()
            X = np.vstack([np.ones(T_pre), np.arange(T_pre) - i]).T
            W = np.diag(w)
            beta = np.linalg.pinv(X.T @ W @ X) @ X.T @ W @ y_pre
            smoothed[i] = beta[0]
        return smoothed

    ell_hat = smooth(y[:T0], bandwidth)
    L_pre = np.column_stack([ell_hat[i:i + m] for i in range(N)])
    L_post = np.column_stack([ell_hat[i + m:i + m + n] for i in range(N)])
    ell_eval = ell_hat[-m:]
    w = cp.Variable(N)
    G = L_pre.T @ L_pre
    eigvals, eigvecs = eigh(G)
    C2 = eigvecs[:, eigvals < tol]
    penalty = cp.norm(C2.T @ w, 2) ** 2 if C2.size > 0 else 0
    objective = cp.Minimize(cp.sum_squares(ell_eval - L_pre @ w) + varsigma * penalty)
    constraints = [w >= 0, cp.sum(w) == 1]
    cp.Problem(objective, constraints).solve()
    w_opt = w.value
    y_hat = np.concatenate([L_pre @ w_opt, L_post @ w_opt])
    return y_hat, w_opt

# Evaluate SHC with bandwidth
def evaluate_bandwidth(bw_val, y, m, T0):
    try:
        yhat, w_opt = shc_estimator(y, m, T0, bandwidth=bw_val)
        fit = np.mean((y[T0 - m:T0] - yhat[:m]) ** 2)
        return fit, yhat, w_opt
    except:
        return np.inf, None, None

# Bee Colony Optimization
def bee_colony_bandwidth(y, m, T0, n_bees=5, n_iter=5, bw_bounds=(0.1, 9.0), limit=5):
    np.random.seed(42)
    bw = np.random.uniform(bw_bounds[0], bw_bounds[1], size=n_bees)
    fitness = np.full(n_bees, np.inf)
    solutions = [None] * n_bees
    weights = [None] * n_bees
    scout_limit = np.zeros(n_bees)

    # Initial Evaluation
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(lambda b: evaluate_bandwidth(b, y, m, T0), bw))
    for i, (fit, yhat, w) in enumerate(results):
        fitness[i] = fit
        solutions[i] = yhat
        weights[i] = w

    for _ in range(n_iter):
        # Employed Bee Phase
        candidates = []
        indices = []
        for i in range(n_bees):
            phi = np.random.uniform(-1, 1)
            k = np.random.choice([j for j in range(n_bees) if j != i])
            v = np.clip(bw[i] + phi * (bw[i] - bw[k]), *bw_bounds)
            candidates.append(v)
            indices.append(i)

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda b: evaluate_bandwidth(b, y, m, T0), candidates))

        for idx, (fit_v, yhat_v, w_v) in zip(indices, results):
            if fit_v < fitness[idx]:
                bw[idx] = candidates[idx]
                fitness[idx] = fit_v
                solutions[idx] = yhat_v
                weights[idx] = w_v
                scout_limit[idx] = 0
            else:
                scout_limit[idx] += 1

        # Onlooker Bee Phase
        prob = 1 / (1 + fitness)
        prob /= prob.sum()
        candidates = []
        indices = []
        for _ in range(n_bees):
            i = np.random.choice(n_bees, p=prob)
            phi = np.random.uniform(-0.1, 0.1)
            v = np.clip(bw[i] + phi * bw[i], *bw_bounds)
            candidates.append(v)
            indices.append(i)

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda b: evaluate_bandwidth(b, y, m, T0), candidates))

        for idx, (fit_v, yhat_v, w_v) in zip(indices, results):
            if fit_v < fitness[idx]:
                bw[idx] = candidates[indices.index(idx)]
                fitness[idx] = fit_v
                solutions[idx] = yhat_v
                weights[idx] = w_v
                scout_limit[idx] = 0
            else:
                scout_limit[idx] += 1

        # Scout Bee Phase
        scout_candidates = []
        scout_indices = []
        for i in range(n_bees):
            if scout_limit[i] > limit:
                v = np.random.uniform(*bw_bounds)
                scout_candidates.append(v)
                scout_indices.append(i)

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(lambda b: evaluate_bandwidth(b, y, m, T0), scout_candidates))

        for idx, (fit_v, yhat_v, w_v) in zip(scout_indices, results):
            bw[idx] = scout_candidates[scout_indices.index(idx)]
            fitness[idx] = fit_v
            solutions[idx] = yhat_v
            weights[idx] = w_v
            scout_limit[idx] = 0

    best_idx = np.argmin(fitness)
    return bw[best_idx], solutions[best_idx], fitness[best_idx], weights[best_idx]

# Simulated data
T = (2020 - 1990 + 1) * 12
T0 = 350
np.random.seed(42)
t = np.arange(T)
y = np.sin(2 * np.pi * (t % 12) / 12) + 0.15 * np.random.randn(T)
y[T0:] += -3
m = 12*10

# Run Bee Colony Bandwidth Tuning
best_bw, best_yhat, best_mse, best_weights = bee_colony_bandwidth(y, m, T0)

# Plot
dates = pd.date_range(start='1990-01-01', periods=T, freq='MS')
plot_start = T0 - m
plot_end = T

plt.figure(figsize=(12, 5))
plt.plot(dates[plot_start:plot_end], y[plot_start:plot_end], label="Observed", color="black")
plt.plot(dates[plot_start:plot_end], best_yhat, label=f"SHC (Bee-opt bw={best_bw:.3f})", linestyle="--", color="red")
plt.axvline(dates[T0], color="gray", linestyle=":", label="Intervention (Apr 2020)")
plt.xlabel("Date")
plt.ylabel("Outcome")
plt.title("SHC with Bee Colony Optimized Bandwidth")
plt.legend()
plt.tight_layout()
plt.show()
