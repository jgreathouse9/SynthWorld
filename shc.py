import numpy as np
import matplotlib.pyplot as plt
import cvxpy as cp
from scipy.linalg import eigh


# Existing shc_estimator function (unchanged)
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
    donor_indices = [(i, i + m - 1) for i in range(N)]

    w = cp.Variable(N)
    G = L_pre.T @ L_pre
    eigvals, eigvecs = eigh(G)
    C2 = eigvecs[:, eigvals < tol]
    penalty = cp.norm(C2.T @ w, 2) ** 2 if C2.size > 0 else 0
    objective = cp.Minimize(cp.sum_squares(ell_eval - L_pre @ w) + varsigma * penalty)
    constraints = [w >= 0, cp.sum(w) == 1]
    cp.Problem(objective, constraints).solve(solver=cp.CLARABEL)

    w_opt = w.value
    y_hat = np.concatenate([L_pre @ w_opt, L_post @ w_opt])

    return y_hat, w_opt, donor_indices


def tune_bandwidth_adaptive(y, m, T0, bw_min=0.5, bw_max=3.0, max_iter=10, tol=1e-2, varsigma=1e-6, verbose=True):
    """
    Adaptively tune bandwidth using a golden-section-inspired search.

    Parameters:
    - y: Time series data
    - m: Length of evaluation window
    - T0: Intervention time index
    - bw_min, bw_max: Initial bandwidth range
    - max_iter: Max iterations to run
    - tol: Tolerance for convergence of interval
    - varsigma: Regularization parameter
    - verbose: Print progress

    Returns:
    - best_bw: Optimal bandwidth found
    - best_yhat: Counterfactual prediction for best bandwidth
    - best_weights: Optimal weights
    """
    phi = (1 + np.sqrt(5)) / 2  # golden ratio
    best_bw = None
    best_mse = np.inf
    best_yhat = None
    best_weights = None

    a, b = bw_min, bw_max
    for iteration in range(max_iter):
        c = b - (b - a) / phi
        d = a + (b - a) / phi

        try:
            yhat_c, weights_c, _ = shc_estimator(y, m, T0, bandwidth=c, varsigma=varsigma)
            mse_c = np.mean((y[T0 - m:T0] - yhat_c[:m]) ** 2)
            if verbose:
                print(f"Iter {iteration+1}, BW {c:.4f} => MSE: {mse_c:.6f}")
        except Exception as e:
            mse_c = np.inf
            yhat_c, weights_c = None, None
            if verbose:
                print(f"Iter {iteration+1}, BW {c:.4f} failed: {e}")

        try:
            yhat_d, weights_d, _ = shc_estimator(y, m, T0, bandwidth=d, varsigma=varsigma)
            mse_d = np.mean((y[T0 - m:T0] - yhat_d[:m]) ** 2)
            if verbose:
                print(f"Iter {iteration+1}, BW {d:.4f} => MSE: {mse_d:.6f}")
        except Exception as e:
            mse_d = np.inf
            yhat_d, weights_d = None, None
            if verbose:
                print(f"Iter {iteration+1}, BW {d:.4f} failed: {e}")

        # Update best
        if mse_c < best_mse:
            best_mse = mse_c
            best_bw = c
            best_yhat = yhat_c
            best_weights = weights_c
        if mse_d < best_mse:
            best_mse = mse_d
            best_bw = d
            best_yhat = yhat_d
            best_weights = weights_d

        # Shrink interval
        if mse_c < mse_d:
            b = d
        else:
            a = c

        if (b - a) < tol:
            if verbose:
                print(f"Converged after {iteration+1} iterations.")
            break

    if best_bw is None:
        raise ValueError("No valid bandwidth found in range.")

    if verbose:
        print(f"Best bandwidth: {best_bw:.4f}, MSE: {best_mse:.6f}")
    return best_bw, best_yhat, best_weights



# --- Simulation ---

T = (2020 - 1990 + 1) * 12  # 372 months
T0 = (2020 - 1990) * 12 + 4  # April 2020 cutoff

np.random.seed(42)
t = np.arange(T)
y = np.sin(2 * np.pi * (t % 12) / 12) + 0.1 * np.random.randn(T)
y[T0:] += -1  # Treatment effect

m = 48  # evaluation window length (4 years pre-treatment)

# Tune bandwidth adaptively
best_bw, best_yhat, best_weights = tune_bandwidth_adaptive(y, m, T0, bw_min=0.2, bw_max=6.0, max_iter=10,verbose=False)

# Plot results
plt.figure(figsize=(12, 5))
plt.plot(t, y, label="Observed", color="black")
plt.plot(np.arange(T0 - m, T), best_yhat, label="SHC Counterfactual (best bw)", linestyle="--", color="red")
plt.axvline(T0, color="gray", linestyle=":", label="Intervention (Apr 2020)")
plt.xlabel("Months since Jan 1990")
plt.ylabel("Outcome")
plt.title("SHC with Adaptive Bandwidth Tuning on Simulated Sine Wave")
plt.legend()
plt.show()
