import numpy as np
import cvxpy as cp
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib

# matplotlib theme
jared_theme = {'axes.grid': True,
              'grid.linestyle': '--',
              'legend.framealpha': 1,
              'legend.facecolor': 'white',
              'legend.shadow': True,
              'legend.fontsize': 14,
              'legend.title_fontsize': 16,
              'xtick.labelsize': 14,
              'ytick.labelsize': 14,
              'axes.labelsize': 16,
              'axes.titlesize': 20,
              'figure.dpi': 100}

matplotlib.rcParams.update(jared_theme)

def generate_data(
        N_clusters=1,
        N_per_cluster=18,
        T_total=104,
        T_naught=90,
        r_ob_covariates_dim=7,
        F_unob_covariates_dim=10,
        noise_variance=1,
        seasonal_strength=2.0,
        trend_strength=0.6,
        rho=0.8,                # AR(1) smoothing for noise
        treatment_effect=5.0,
        random_seed=1234
    ):
    """
    Generate clustered synthetic hotel data with seasonality, trends, and a universal treatment effect applied
    to all units post-intervention.
    """
    np.random.seed(random_seed)
    N_units = N_clusters * N_per_cluster

    # Assign clusters
    clusters = np.repeat(np.arange(N_clusters), N_per_cluster)

    # Observable & latent covariates
    Z_ob = np.random.uniform(0, 1, (r_ob_covariates_dim, N_units))
    mu_unob = np.random.uniform(0, 1, (F_unob_covariates_dim, N_units))
    Z_df = pd.DataFrame(Z_ob, columns=[f"Unit {j+1}" for j in range(N_units)])
    mu_df = pd.DataFrame(mu_unob, columns=[f"Unit {j+1}" for j in range(N_units)])

    # Smooth time-varying coefficients
    theta_ob = np.cumsum(np.random.normal(0, 0.05, (r_ob_covariates_dim, T_total)), axis=1)
    lambda_unob = np.cumsum(np.random.normal(0, 0.05, (F_unob_covariates_dim, T_total)), axis=1)

    # Seasonal + trend components
    weeks = np.arange(T_total)
    seasonality = seasonal_strength * np.sin(2 * np.pi * weeks / 52)
    biannual = 2.0 * np.sin(2 * np.pi * weeks / 26)
    trend = trend_strength * weeks

    cluster_shifts = np.linspace(0, 15, N_clusters)
    cluster_phase = np.linspace(0, np.pi/4, N_clusters)

    # Generate outcomes
    Y = np.zeros((N_units, T_total))
    for j in range(N_units):
        cluster_id = clusters[j]

        # AR(1) noise
        eps = np.zeros(T_total)
        for t_idx in range(1, T_total):
            eps[t_idx] = rho * eps[t_idx-1] + np.random.normal(0, noise_variance)

        for t_idx in range(T_total):
            deterministic = (
                cluster_shifts[cluster_id]
                + seasonality[t_idx] * (1 + 0.1 * cluster_id)
                + biannual[t_idx] + cluster_phase[cluster_id]
                + trend[t_idx]
            )
            structural = np.dot(theta_ob[:, t_idx], Z_ob[:, j]) + np.dot(lambda_unob[:, t_idx], mu_unob[:, j])

            Y[j, t_idx] = deterministic + structural + eps[t_idx]

            # Apply universal treatment effect for post-intervention
            if t_idx >= T_naught:
                Y[j, t_idx] += treatment_effect

    Y_df = pd.DataFrame(Y, columns=[f"Week {t+1}" for t in range(T_total)])

    return (
        {"data": Y_df, "clusters": clusters, "pre_periods": T_naught, "post_periods": T_total - T_naught},
        Z_df,
        mu_df
    )


def _get_per_cluster_param(param, klabel, default=None):
    """Helper: param may be None, scalar, or dict {klabel: val}."""
    if param is None:
        return default
    if isinstance(param, dict):
        return param.get(klabel, default)
    return param  # scalar

def SCMEXP(
    Y_full,
    T0,
    clusters,
    blank_periods=0,
    m_eq=None,
    m_min=None,
    m_max=None,
    exclusive=True,
    # design selector (mutually exclusive modes): 'base', 'weak', 'eq11', 'unit'
    design="base",
    # weak-targeted param (only used when design == "weak")
    beta=1e-6,
    # eq11 params (only used when design == "eq11")
    lambda1=0.0,
    lambda2=0.0,
    # unit-level params (only used when design == "unit")
    xi=0.0,        # OA.1
    lambda1_unit=0.0,  # OA.2 (treated side)
    lambda2_unit=0.0,  # OA.3 pairwise (treated-control pairwise term)
    solver=cp.ECOS_BB,
    verbose=False
):
    """
    Clustered Synthetic Control for Experimental Design (SCMEXP).

    Constructs synthetic treated and control units within clusters to approximate
    pre-treatment trajectories, enabling targeted experimental design when full
    randomization is infeasible or unethical.

    Parameters
    ----------
    Y_full : ndarray, shape (N_units, T_total)
        Outcome matrix with units as rows and time periods as columns.
    T0 : int
        Number of pre-treatment periods used for fitting synthetic controls. Must
        satisfy 1 <= T0 < T_total.
    clusters : array-like, shape (N_units,)
        Cluster labels for each unit. Units within the same cluster are used
        together in the synthetic control construction.
    blank_periods : int, default=0
        Number of initial periods within T0 to ignore in fitting.
    m_eq : int, dict, or None
        Exact cardinality of selected units per cluster. Can be scalar or dict
        mapping cluster label to value.
    m_min : int, dict, or None
        Minimum number of units to select per cluster. Can be scalar or dict.
    m_max : int, dict, or None
        Maximum number of units to select per cluster. Can be scalar or dict.
    exclusive : bool, default=False
        If True, ensures each unit is assigned to at most one cluster's synthetic control.
    design : {'base', 'weak', 'eq11', 'unit'}, default='base'
        Type of synthetic control design:
            - 'base' : cluster-targeted fit to cluster mean.
            - 'weak' : weakly-targeted; adds penalty (beta) to align control with treated.
            - 'eq11' : penalized design with lambda1/lambda2 weighting distances from cluster means.
            - 'unit' : unit-level penalized design (xi, lambda1_unit, lambda2_unit).
    beta : float, default=1e-6
        Weak-targeting penalty (used only if design='weak').
    lambda1 : float, default=0.0
        Penalization of treated units’ distance from cluster mean (used if design='eq11').
    lambda2 : float, default=0.0
        Penalization of control units’ distance from cluster mean (used if design='eq11').
    xi : float, default=0.0
        Unit-level OA.1 penalty (used if design='unit'), penalizes treated deviation from synthetic control.
    lambda1_unit : float, default=0.0
        Unit-level OA.2 penalty, penalizes treated deviation from cluster mean (used if design='unit').
    lambda2_unit : float, default=0.0
        Unit-level OA.3 penalty, penalizes pairwise differences between treated and control (used if design='unit').
    solver : cvxpy Solver, default=cp.ECOS_BB
        Solver used for the optimization problem.
    verbose : bool, default=False
        If True, prints solver progress.

    Returns
    -------
    result : dict
        Dictionary containing synthetic control solution and diagnostics:
            w_opt : ndarray, shape (N_units, K_clusters)
                Optimized weights for synthetic treated units per cluster.
            v_opt : ndarray, shape (N_units, K_clusters)
                Optimized weights for synthetic control units per cluster.
            z_opt : ndarray, shape (N_units, K_clusters)
                Binary selection indicators for units in each cluster.
            y_syn_treated_clusters : list of ndarray
                Synthetic treated trajectories for each cluster.
            y_syn_control_clusters : list of ndarray
                Synthetic control trajectories for each cluster.
            Xbar_clusters : list of ndarray
                Cluster-level mean trajectories (pre-treatment).
            cluster_labels : list
                Unique cluster labels.
            cluster_members : list of ndarray
                Indices of units in each cluster.
            w_agg, v_agg : ndarray
                Aggregated weights across clusters.
            rmse_cluster : list of float
                RMSE between synthetic treated and control fit to cluster mean (pre-treatment).
            design-specific parameters (lambda1, lambda2, beta, xi) returned as applicable.

    Notes
    -----
    - This function allows experimenters to select treated units in a way that mimics
      randomization by ensuring pre-treatment similarity between treated and control.
    - The optimization enforces similarity while allowing cardinality constraints
      and penalized deviations.
    - Realized post-treatment differences between synthetic treated and control
      units provide an estimate of the ATT.

    References
    ----------
    Abadie, A., & Zhao, J. (2025). Synthetic Controls for Experimental Design.
    arXiv:2108.02196. https://arxiv.org/abs/2108.02196
    """
    # --- validation of mutually exclusive design selection ---
    valid_designs = {"base", "weak", "eq11", "unit"}
    if design not in valid_designs:
        raise ValueError(f"design must be one of {valid_designs}; got '{design}'")

    # --- basic shape checks ---
    if T0 <= 0 or T0 >= Y_full.shape[1]:
        raise ValueError("T0 must be 1 <= T0 < Y_full.shape[1]")
    if blank_periods < 0 or blank_periods >= T0:
        raise ValueError("blank_periods must be 0 <= blank_periods < T0 (need at least 1 fit period)")

    # check incompatible parameter usage (help the user avoid accidental mixes)
    if design != "weak" and beta != 1e-6:
        raise ValueError("beta is only valid when design == 'weak'")
    if design != "eq11" and (lambda1 != 0.0 or lambda2 != 0.0):
        raise ValueError("lambda1/lambda2 are only valid when design == 'eq11'")
    if design != "unit" and (xi != 0.0 or lambda1_unit != 0.0 or lambda2_unit != 0.0):
        raise ValueError("xi/lambda1_unit/lambda2_unit are only valid when design == 'unit'")

    # --- prepare data slices ---
    T_fit = T0 - blank_periods
    Y_fit = Y_full[:, :T_fit]  # shape (N, T_fit)
    Y_blank = Y_full[:, T_fit:T0] if blank_periods > 0 else None

    N, T_fit_actual = Y_fit.shape
    clusters = np.asarray(clusters)
    if clusters.shape[0] != N:
        raise ValueError("clusters must have length N (rows of Y).")

    cluster_labels = np.unique(clusters)
    K = len(cluster_labels)
    label_to_k = {lab: i for i, lab in enumerate(cluster_labels)}

    # membership mask M: shape (N, K)
    M = np.zeros((N, K), dtype=bool)
    for j in range(N):
        M[j, label_to_k[clusters[j]]] = True

    # cluster-level means and membership lists
    Xbar_clusters = []
    cluster_members = []
    for k_idx, lab in enumerate(cluster_labels):
        members = np.where(M[:, k_idx])[0]
        if members.size == 0:
            raise ValueError(f"Cluster '{lab}' has no members.")
        cluster_members.append(members)
        Xbar_clusters.append(Y_fit[members, :].mean(axis=0))  # shape (T_fit,)

    # Precompute D1 = || Xbar_k - X_j ||^2 (N x K) if needed for eq11 or unit
    D1 = np.zeros((N, K))
    for k_idx in range(K):
        diffs = Y_fit - Xbar_clusters[k_idx][None, :]  # (N, T_fit)
        D1[:, k_idx] = np.sum(diffs**2, axis=1)

    # Precompute D2 per cluster (pairwise squared distances among members) used by 'unit' design
    D2_list = []
    for k_idx in range(K):
        members = cluster_members[k_idx]
        Xm = Y_fit[members, :]  # (m, T_fit)
        diff = Xm[:, None, :] - Xm[None, :, :]  # (m, m, T_fit)
        D2 = np.sum(diff**2, axis=2)  # (m, m)
        D2_list.append(D2)

    # CVXPY variables
    w = cp.Variable((N, K), nonneg=True)
    v = cp.Variable((N, K), nonneg=True)
    z = cp.Variable((N, K), boolean=True)

    constraints = []
    # enforce membership zeros
    for k in range(K):
        for j in range(N):
            if not M[j, k]:
                constraints += [w[j, k] == 0, v[j, k] == 0, z[j, k] == 0]

    # per-cluster normalization + cardinality + linking constraints
    for k_idx, lab in enumerate(cluster_labels):
        members = cluster_members[k_idx]
        constraints += [cp.sum(w[members, k_idx]) == 1]
        constraints += [cp.sum(v[members, k_idx]) == 1]

        m_eq_k = _get_per_cluster_param(m_eq, lab, default=None)
        m_min_k = _get_per_cluster_param(m_min, lab, default=None)
        m_max_k = _get_per_cluster_param(m_max, lab, default=None)

        if m_eq_k is not None:
            constraints += [cp.sum(z[members, k_idx]) == int(m_eq_k)]
        if m_min_k is not None:
            constraints += [cp.sum(z[members, k_idx]) >= int(m_min_k)]
        if m_max_k is not None:
            constraints += [cp.sum(z[members, k_idx]) <= int(m_max_k)]

        for j in members:
            constraints += [w[j, k_idx] <= z[j, k_idx]]
            constraints += [v[j, k_idx] <= 1 - z[j, k_idx]]

    if exclusive:
        for j in range(N):
            constraints += [cp.sum(z[j, :]) <= 1]

    # Build objective depending on design
    Y_T = Y_fit.T  # (T_fit, N)
    obj_terms = []

    if design == "base":
        # Plain cluster-targeted: both treated & control fit to cluster mean
        for k_idx in range(K):
            Xbar_k = Xbar_clusters[k_idx]
            syn_treated_k = Y_T @ w[:, k_idx]
            syn_control_k = Y_T @ v[:, k_idx]
            obj_terms.append(cp.sum_squares(Xbar_k - syn_treated_k))
            obj_terms.append(cp.sum_squares(Xbar_k - syn_control_k))

    elif design == "weak":
        # Weakly targeted: control is fit to treated (beta * ||treated - control||^2)
        for k_idx in range(K):
            Xbar_k = Xbar_clusters[k_idx]
            syn_treated_k = Y_T @ w[:, k_idx]
            syn_control_k = Y_T @ v[:, k_idx]
            obj_terms.append(cp.sum_squares(Xbar_k - syn_treated_k))
            obj_terms.append(beta * cp.sum_squares(syn_treated_k - syn_control_k))

    elif design == "eq11":
        # Equation (11) style penalized: base fits + lambda1 on w distances, lambda2 on v distances
        for k_idx in range(K):
            Xbar_k = Xbar_clusters[k_idx]
            syn_treated_k = Y_T @ w[:, k_idx]
            syn_control_k = Y_T @ v[:, k_idx]
            obj_terms.append(cp.sum_squares(Xbar_k - syn_treated_k))
            obj_terms.append(cp.sum_squares(Xbar_k - syn_control_k))
            if lambda1 > 0:
                obj_terms.append(lambda1 * cp.sum(cp.multiply(w[:, k_idx], D1[:, k_idx])))
            if lambda2 > 0:
                obj_terms.append(lambda2 * cp.sum(cp.multiply(v[:, k_idx], D1[:, k_idx])))

    elif design == "unit":
        # Unit-level penalized design (OA.1 + OA.2 + OA.3)
        # OA.1 (xi): sum_j w_j * || X_j - (Y_fit^T v) ||^2
        # OA.2 (lambda1_unit): sum_j w_j ||Xbar - X_j||^2
        # OA.3 (lambda2_unit): sum_j w_j * sum_i v_i ||X_j - X_i||^2  (pairwise inside cluster)
        for k_idx in range(K):
            members = cluster_members[k_idx]
            Xbar_k = Xbar_clusters[k_idx]
            syn_treated_k = Y_T @ w[:, k_idx]    # (T_fit,)
            syn_control_k = Y_T @ v[:, k_idx]    # (T_fit,)

            # cluster-level fits
            obj_terms.append(cp.sum_squares(Xbar_k - syn_treated_k))
            obj_terms.append(cp.sum_squares(Xbar_k - syn_control_k))

            # OA.1: xi * sum_{j in members} w_jk * || X_j - syn_control_k ||^2
            if xi > 0:
                for local_idx, j in enumerate(members):
                    X_j = Y_fit[j, :]  # numpy (T_fit,)
                    # cp expression: xi * w[j,k] * || X_j - syn_control_k ||^2
                    obj_terms.append(xi * w[j, k_idx] * cp.sum_squares(X_j - syn_control_k))

            # OA.2: lambda1_unit * sum_j w_jk * || Xbar_k - X_j ||^2
            if lambda1_unit > 0:
                obj_terms.append(lambda1_unit * cp.sum(cp.multiply(w[:, k_idx], D1[:, k_idx])))

            # OA.3: lambda2_unit * sum_j w_jk * ( Dmat @ v_m )_j
            if lambda2_unit > 0:
                # D2_list[k_idx] is (m,m) for members
                if len(members) > 0:
                    Dmat = D2_list[k_idx]               # numpy (m, m)
                    v_m = v[members, k_idx]            # cp (m,)
                    inner_vec = Dmat.dot(v_m)          # yields cp expression (m,)
                    w_m = w[members, k_idx]            # cp (m,)
                    obj_terms.append(lambda2_unit * cp.sum(cp.multiply(w_m, inner_vec)))

    else:
        raise RuntimeError("unhandled design branch (this should not happen)")

    objective = cp.Minimize(cp.sum(obj_terms))
    prob = cp.Problem(objective, constraints)
    prob.solve(solver=solver, verbose=verbose)

    # extract
    w_opt = w.value
    v_opt = v.value
    z_opt = z.value

    # full predictions on Y_full
    Y_full_T = Y_full.T
    y_syn_treated_clusters = []
    y_syn_control_clusters = []
    for k_idx in range(K):
        w_k = w_opt[:, k_idx]
        v_k = v_opt[:, k_idx]
        y_syn_treated_clusters.append(Y_full_T @ w_k)
        y_syn_control_clusters.append(Y_full_T @ v_k)

    # cluster rmse on fit period (treated vs control)
    rmse_cluster = []
    for k_idx in range(K):
        treated_idx = np.where(w_opt[:, k_idx] > 1e-8)[0]
        if len(treated_idx) > 0:
            y_treated = (Y_fit[treated_idx, :].T @ w_opt[treated_idx, k_idx]) / np.sum(w_opt[treated_idx, k_idx])
        else:
            y_treated = np.zeros(T_fit)
        y_control = Y_fit.T @ v_opt[:, k_idx]
        rmse_cluster.append(np.sqrt(np.mean((y_treated - y_control) ** 2)))

    # aggregate weights
    cluster_sizes = [len(m) for m in cluster_members]
    total_size = sum(cluster_sizes)
    agg_weights = np.array(cluster_sizes) / total_size
    w_agg = np.zeros(N)
    v_agg = np.zeros(N)
    for k_idx in range(K):
        w_agg += agg_weights[k_idx] * w_opt[:, k_idx]
        v_agg += agg_weights[k_idx] * v_opt[:, k_idx]

    result = {
        "Y_Full": Y_full,
        "w_opt": w_opt,
        "v_opt": v_opt,
        "z_opt": z_opt,
        "y_syn_treated_clusters": y_syn_treated_clusters,
        "y_syn_control_clusters": y_syn_control_clusters,
        "Xbar_clusters": Xbar_clusters,
        "cluster_labels": list(cluster_labels),
        "cluster_members": cluster_members,
        "w_agg": w_agg,
        "v_agg": v_agg,
        "cluster_sizes": cluster_sizes,
        "T0": T0,
        "blank_periods": blank_periods,
        "T_fit": T_fit,
        "Y_fit": Y_fit,
        "Y_blank": Y_blank,
        "rmse_cluster": rmse_cluster,
        "design": design,
        "beta": beta if design == "weak" else None,
        "lambda1": (lambda1 if design == "eq11" else (lambda1_unit if design == "unit" else None)),
        "lambda2": (lambda2 if design == "eq11" else (lambda2_unit if design == "unit" else None)),
        "xi": (xi if design == "unit" else None)
    }
    return result



def inference_scm(result, Y_full, T_post, alpha=0.05, method='placebo'):
    """
    Perform inference for synthetic control estimates with cluster-specific and global effects.

    This function computes the realized treatment effects and their inference
    using a placebo-based approach, following the methodology in:

        Abadie, A., & Zhao, J. (2025). Synthetic Controls for Experimental Design.
        arXiv:2108.02196. https://arxiv.org/abs/2108.02196

    The method produces per-period treatment effects, averages, confidence intervals,
    and p-values both at the global and cluster-specific levels, using pre-treatment
    (and optionally blank) periods to calibrate the placebo distribution.

    Parameters
    ----------
    result : dict
        Output dictionary from `SCMEXP` containing:
        'w_opt', 'v_opt', 'w_agg', 'v_agg', 'rmse_cluster', 'Y_fit', 'Y_blank', etc.
    Y_full : ndarray, shape (N_units, T0 + T_post)
        Full observed outcome matrix, including pre-treatment (T0) and post-treatment (T_post) periods.
    T_post : int
        Number of post-treatment periods to compute inference for.
    alpha : float, default=0.05
        Significance level for confidence intervals.
    method : {'placebo'}, default='placebo'
        Inference method. Only 'placebo' is currently supported, as advocated in the reference.

    Returns
    -------
    result_inference : dict
        Dictionary containing inference results:
            tau_hat : ndarray, shape (T_post,)
                Global per-period treatment effects.
            avg_tau_hat : float
                Global average treatment effect over post-treatment periods.
            tau_hat_cluster : ndarray, shape (K_clusters, T_post)
                Cluster-specific per-period treatment effects.
            avg_tau_cluster : ndarray, shape (K_clusters,)
                Cluster-specific average treatment effects.
            p_values : ndarray, shape (T_post,)
                Global p-values per post-treatment period.
            ci_lower : ndarray, shape (T_post,)
                Global lower confidence interval bounds.
            ci_upper : ndarray, shape (T_post,)
                Global upper confidence interval bounds.
            p_values_cluster : ndarray, shape (K_clusters, T_post)
                Cluster-specific p-values.
            ci_lower_cluster : ndarray, shape (K_clusters, T_post)
                Cluster-specific lower confidence interval bounds.
            ci_upper_cluster : ndarray, shape (K_clusters, T_post)
                Cluster-specific upper confidence interval bounds.
            rmspe_pre : float
                Global root mean squared prediction error in pre-treatment periods.
            rmse_cluster : list of float
                Cluster-specific RMSEs from the design phase.

    Notes
    -----
    - This function uses a placebo-based inference procedure, where gaps in pre-treatment
      (or blank) periods are used to construct empirical null distributions.
    - Confidence intervals and p-values are scaled relative to RMSPE to account for
      pre-treatment fit quality.
    - Cluster-specific inference allows for testing heterogeneous effects across clusters,
      using the synthetic control weights specific to each cluster.

    References
    ----------
    Abadie, A., & Zhao, J. (2025). Synthetic Controls for Experimental Design.
    arXiv:2108.02196. https://arxiv.org/abs/2108.02196
    """
    if method != 'placebo':
        raise ValueError("Only 'placebo' method is supported, as advocated in the paper.")

    T0 = result["T0"]
    Y_fit = result["Y_fit"]
    Y_blank = result["Y_blank"]
    w_opt = result["w_opt"]  # Shape (N, K)
    v_opt = result["v_opt"]  # Shape (N, K)
    w_agg = result["w_agg"]
    v_agg = result["v_agg"]
    rmse_cluster = result["rmse_cluster"]
    N, T_total = Y_full.shape
    T_fit = result["T_fit"]
    blank_periods = result["blank_periods"]
    K = w_opt.shape[1]  # Number of clusters
    cluster_members = result["cluster_members"]
    cluster_labels = result["cluster_labels"]

    # Global effects
    Y_post = Y_full[:, T0:T0 + T_post]
    Y_post_T = Y_post.T
    tau_hat = Y_post_T @ w_agg - Y_post_T @ v_agg
    avg_tau_hat = np.mean(tau_hat) if T_post > 0 else 0.0

    # Cluster-specific effects
    tau_hat_cluster = np.zeros((K, T_post))
    for k in range(K):
        w_k = w_opt[:, k]
        v_k = v_opt[:, k]
        tau_hat_cluster[k, :] = Y_post_T @ w_k - Y_post_T @ v_k
    avg_tau_cluster = np.mean(tau_hat_cluster, axis=1) if T_post > 0 else np.zeros(K)

    # Pre-fit RMSPE (global)
    Y_fit_T = Y_fit.T
    syn_fit_treated = Y_fit_T @ w_agg
    syn_fit_control = Y_fit_T @ v_agg
    rmspe_pre = np.sqrt(np.mean((syn_fit_treated - syn_fit_control) ** 2))

    # Use blank periods for inference as per the paper
    if Y_blank is None:
        raise ValueError("Blank periods are required for placebo inference.")
    blank_periods = Y_blank.shape[1]
    Y_blank_T = Y_blank.T

    # Global inference using aggregate gaps in blank periods
    u_blank = Y_blank_T @ w_agg - Y_blank_T @ v_agg  # gaps in blank (blank_periods,)
    abs_u_blank = np.abs(u_blank)
    q_global = np.quantile(abs_u_blank, 1 - alpha)
    rmspe_blank_global = np.sqrt(np.mean(u_blank**2))
    scale_global = rmspe_blank_global / rmspe_pre if rmspe_pre > 0 else 1
    ci_lower = tau_hat - q_global * scale_global
    ci_upper = tau_hat + q_global * scale_global

    p_values = np.zeros(T_post)
    for t in range(T_post):
        p_values[t] = np.mean(abs_u_blank >= np.abs(tau_hat[t]))

    # Cluster-specific inference
    ci_lower_cluster = np.zeros((K, T_post))
    ci_upper_cluster = np.zeros((K, T_post))
    p_values_cluster = np.zeros((K, T_post))
    rmse_blank_cluster = np.zeros(K)
    for k in range(K):
        w_k = w_opt[:, k]
        v_k = v_opt[:, k]
        u_blank_k = Y_blank_T @ w_k - Y_blank_T @ v_k
        abs_u_blank_k = np.abs(u_blank_k)
        q_k = np.quantile(abs_u_blank_k, 1 - alpha)
        rmse_blank_cluster[k] = np.sqrt(np.mean(u_blank_k**2))
        scale_k = rmse_blank_cluster[k] / rmse_cluster[k] if rmse_cluster[k] > 0 else 1
        ci_lower_cluster[k, :] = tau_hat_cluster[k, :] - q_k * scale_k
        ci_upper_cluster[k, :] = tau_hat_cluster[k, :] + q_k * scale_k
        for t in range(T_post):
            p_values_cluster[k, t] = np.mean(abs_u_blank_k >= np.abs(tau_hat_cluster[k, t]))

    return {
        "tau_hat": tau_hat,              # Global per-period effects
        "avg_tau_hat": avg_tau_hat,      # Global average effect
        "tau_hat_cluster": tau_hat_cluster,  # Cluster-specific per-period effects
        "avg_tau_cluster": avg_tau_cluster,  # Cluster-specific average effects
        "p_values": p_values,            # Global p-values
        "ci_lower": ci_lower,            # Global CI lower bounds
        "ci_upper": ci_upper,            # Global CI upper bounds
        "p_values_cluster": p_values_cluster,  # Cluster-specific p-values
        "ci_lower_cluster": ci_lower_cluster,  # Cluster-specific CI lower bounds
        "ci_upper_cluster": ci_upper_cluster,  # Cluster-specific CI upper bounds
        "rmspe_pre": rmspe_pre,          # Global pre-fit RMSPE
        "rmse_cluster": rmse_cluster,    # Cluster-specific RMSEs from design phase
        "original_result": result
    }


def simulate_linear_factor_model(
        n_units: int = 21,
        n_periods: int = 104,
        k: int = 3,
        seed: int = 2025,
        loading_loc: float = 0.8,
        loading_scale: float = 0.6,
        sparsity_prob: float = 0.15,
        intercept_loc: float = 50,
        intercept_scale: float = 6,
        sigma_eps: float = 1.5,
        factor_funcs: list = None,
        ar_noise: float = 0.6   # persistence of idiosyncratic noise
) -> pd.DataFrame:
    """
    Simulate a dataset using a linear factor model with smoother, seasonal dynamics.
    """

    np.random.seed(seed)

    # 1. Factor loadings
    L = np.random.normal(loc=loading_loc, scale=loading_scale, size=(n_units, k))
    mask = np.random.rand(n_units, k) < sparsity_prob
    L[mask] *= 0.3

    # 2. Common factors
    t = np.arange(n_periods)
    if factor_funcs is None:
        f1 = 4.0 * np.sin(2 * np.pi * t / 52) + 2.0 * np.cos(4 * np.pi * t / 52)
        f2 = 5.0 * np.cos(2 * np.pi * t / 26)  # bi-annual seasonality
        f3 = 0.03 * t + 1.5 * np.sin(2 * np.pi * t / 13)  # slow trend + quarterly cycle
        factors = [f1, f2, f3]
    else:
        factors = [func(t) for func in factor_funcs]
    F = np.vstack(factors)

    # 3. Intercepts
    alpha = np.random.normal(loc=intercept_loc, scale=intercept_scale, size=(n_units, 1))

    # 4. Idiosyncratic noise with AR(1) smoothing
    eps = np.zeros((n_units, n_periods))
    for i in range(n_units):
        noise = np.random.normal(scale=sigma_eps, size=n_periods)
        for t_idx in range(1, n_periods):
            eps[i, t_idx] = ar_noise * eps[i, t_idx-1] + noise[t_idx]

    # 5. Construct data
    X = L @ F + alpha + eps
    X = np.maximum(X, 0.5)

    # 6. To DataFrame
    unit_names = [f"Unit_{i + 1:02d}" for i in range(n_units)]
    period_names = [f"Period_{i + 1:02d}" for i in range(n_periods)]
    df = pd.DataFrame(X, index=unit_names, columns=period_names)

    return df


import matplotlib.cm as cm

def plot_scm_inference(inference_results, overlay_clusters=True, alpha_cluster=0.5):
    """
    Plot the full synthetic control gap: pre-treatment residuals + post-treatment effect,
    with confidence intervals only for the post-treatment period. Optionally overlays cluster-specific
    gaps on top of the global effect with semi-transparent lines.

    Parameters
    ----------
    inference_results : dict
        Dictionary returned from `inference_scm`, which must include:
        - 'original_result': original SCMEXP result dictionary containing 'Y_Full', 'w_agg', 'v_agg', 'T0'
        - 'tau_hat', 'ci_lower', 'ci_upper' (global)
        - 'tau_hat_cluster', 'ci_lower_cluster', 'ci_upper_cluster' (cluster-specific)
        - 'rmspe_pre'
    overlay_clusters : bool, default=True
        If True, overlay cluster-specific gaps on top of the global gap.
    alpha_cluster : float, default=0.5
        Transparency level for cluster lines (0=transparent, 1=opaque).

    Returns
    -------
    fig : matplotlib.figure.Figure
        Matplotlib figure object.
    ax : matplotlib.axes.Axes
        Matplotlib axes object.
    """
    scm_res = inference_results['original_result']
    Y_full = scm_res['Y_Full']
    w_agg = scm_res['w_agg']
    v_agg = scm_res['v_agg']
    T0 = scm_res['T0']
    T_fit = scm_res['T_fit']
    rmspe_pre = inference_results['rmspe_pre']

    # Pre-treatment residuals
    tau_pre = Y_full[:, :T0].T @ w_agg - Y_full[:, :T0].T @ v_agg

    # Post-treatment global gap
    tau_post_global = inference_results['tau_hat']
    ci_lower_post = inference_results['ci_lower']
    ci_upper_post = inference_results['ci_upper']

    # Full global vector
    tau_full_global = np.concatenate([tau_pre, tau_post_global])
    ci_lower_full = np.concatenate([np.full(T0, np.nan), ci_lower_post])
    ci_upper_full = np.concatenate([np.full(T0, np.nan), ci_upper_post])
    periods = np.arange(1, len(tau_full_global) + 1)

    # Plot global
    fig = plt.figure(figsize=(12, 5))
    ax = plt.gca()
    ax.plot(periods, tau_full_global, color='black', marker='o', label='Global Synthetic Gap')
    ax.fill_between(periods, ci_lower_full, ci_upper_full, color='blue', alpha=0.2, label='95% CI (post-treatment)')
    ax.axhline(0, color='black', linestyle='--', linewidth=1)

    # Overlay clusters if requested
    if overlay_clusters:
        tau_post_clusters = inference_results.get('tau_hat_cluster', None)
        if tau_post_clusters is not None:
            K = tau_post_clusters.shape[0]
            colors = cm.tab20(np.linspace(0, 1, K))
            for k in range(K):
                tau_full_cluster = np.concatenate([tau_pre, tau_post_clusters[k]])
                ax.plot(periods, tau_full_cluster,
                        linestyle='--',
                        marker='d',
                        color=colors[k],
                        alpha=alpha_cluster,
                        label=f'Cluster {k}')

    # Reference lines for fit end and treatment start
    ax.axvline(T_fit, color='blue', linestyle='-', linewidth=1.5, label='Fit Period End')
    ax.axvline(T0, color='red', linestyle='-', linewidth=1.5, label='Treatment Start')

    ax.set_xlabel("Time Period")
    ax.set_ylabel("Treatment Effect")
    ax.set_title("Gap Plot")
    ax.legend()
    plt.tight_layout()
    plt.show()

    return fig, ax
