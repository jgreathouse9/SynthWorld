def shc_estimator(y, m, T0, bandwidth=3, varsigma=1e-6, tol=1e-8):
    """
    Synthetic Historical Control (SHC) estimator.

    Parameters
    ----------
    y : np.ndarray
        (T,) array of outcome values.
    m : int
        Evaluation window length (number of pre-treatment periods to match).
    T0 : int
        End of pre-treatment period (y[0] to y[T0-1] are pre-treatment).
    bandwidth : float
        Bandwidth for local linear smoothing.
    varsigma : float
        Regularization penalty for null-space projection.
    tol : float
        Tolerance for defining the null space.

    Returns
    -------
    y_hat : np.ndarray
        SHC counterfactual over [T0 - m, T).
    weights : np.ndarray
        Optimal donor weights (length = N).
    donor_indices : list of tuples
        List of (start_idx, end_idx) for each donor window used.
    """
    T = len(y)
    n = T - T0  # post-treatment horizon
    N = T0 - m - n + 1
    if N <= 0:
        raise ValueError("Insufficient pre-treatment data to construct donor pool.")

    # Local linear smoother (only for y[:T0])
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

    # Build donor pool: N donors, each with m pre + n post
    L_pre = np.column_stack([ell_hat[i:i + m] for i in range(N)])
    L_post = np.column_stack([ell_hat[i + m:i + m + n] for i in range(N)])
    ell_eval = ell_hat[-m:]
    donor_indices = [(i, i + m - 1) for i in range(N)]

    # QP: minimize ||ell_eval - L_pre @ w||^2 + varsigma * ||C2.T @ w||^2
    w = cp.Variable(N)
    G = L_pre.T @ L_pre
    eigvals, eigvecs = eigh(G)
    C2 = eigvecs[:, eigvals < tol]
    penalty = cp.norm(C2.T @ w, 2)**2 if C2.size > 0 else 0
    objective = cp.Minimize(cp.sum_squares(ell_eval - L_pre @ w) + varsigma)
    constraints = [w >= 0, cp.sum(w)==1]
    cp.Problem(objective, constraints).solve()

    w_opt = w.value
    y_hat = np.concatenate([L_pre @ w_opt, L_post @ w_opt])  # shape: (m + n,)

    return y_hat, w_opt, donor_indices
