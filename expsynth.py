import numpy as np
import cvxpy as cp
import pandas as pd

def generate_synthetic_hotel_data(
        N_units=15,
        T_naught=104-28,
        T_total=104,
        r_ob_covariates_dim=7,
        F_unob_covariates_dim=5,
        noise_variance=.05,
        random_seed=123456
    ):
    """
    Generate synthetic panel data for N_units hotels across T_total time periods.

    Returns:
        Y_N_df : pd.DataFrame of shape (N_units, T_total)
                 Observed potential outcomes (N units x T_total periods)
        Z_ob_covariates_df : pd.DataFrame (r_ob_covariates_dim x N_units)
        mu_unob_covariates_df : pd.DataFrame (F_unob_covariates_dim x N_units)
    """
    np.random.seed(random_seed)

    # Initialize matrices
    Z_ob_covariates_matrix = np.full((r_ob_covariates_dim, N_units), np.nan)
    mu_unob_covariates_matrix = np.full((F_unob_covariates_dim, N_units), np.nan)

    theta_ob_N_matrix = np.full((r_ob_covariates_dim, T_total), np.nan)
    gamma_ob_I_matrix = np.full((r_ob_covariates_dim, T_total), np.nan)
    lambda_unob_N_matrix = np.full((F_unob_covariates_dim, T_total), np.nan)
    eta_unob_I_matrix = np.full((F_unob_covariates_dim, T_total), np.nan)

    epsilon_N_matrix = np.full((N_units, T_total), np.nan)
    xi_I_matrix = np.full((N_units, T_total), np.nan)

    Y_N_matrix = np.full((N_units, T_total), np.nan)
    Y_I_matrix = np.full((N_units, T_total), np.nan)

    # Population weights (just for completeness)
    beta_temp = np.random.uniform(0, 1, N_units)
    beta_vector = beta_temp / np.sum(beta_temp)

    # Constants
    range_intercept_max = 20
    delta_N_vector = np.sort(np.concatenate([
        range_intercept_max * np.random.uniform(0, 1, T_naught),
        range_intercept_max * np.random.uniform(0, 1, T_total - T_naught)
    ]))
    upsilon_I_vector = np.concatenate([
        np.full(T_naught, np.nan),
        np.sort(range_intercept_max * np.random.uniform(0, 1, T_total - T_naught))
    ])

    # Covariates
    range_covariates_max = 1
    for j in range(N_units):
        Z_ob_covariates_matrix[:, j] = range_covariates_max * np.random.uniform(0, 1, r_ob_covariates_dim)
        mu_unob_covariates_matrix[:, j] = range_covariates_max * np.random.uniform(0, 1, F_unob_covariates_dim)

    Z_ob_covariates_df = pd.DataFrame(Z_ob_covariates_matrix, columns=range(1, N_units + 1))
    mu_unob_covariates_df = pd.DataFrame(mu_unob_covariates_matrix, columns=range(1, N_units + 1))

    # Coefficients
    range_coefficients_max = 10
    for t in range(T_total):
        theta_ob_N_matrix[:, t] = range_coefficients_max * np.random.uniform(0, 1, r_ob_covariates_dim)
        lambda_unob_N_matrix[:, t] = range_coefficients_max * np.random.uniform(0, 1, F_unob_covariates_dim)
        if t < T_naught:
            gamma_ob_I_matrix[:, t] = np.full(r_ob_covariates_dim, np.nan)
            eta_unob_I_matrix[:, t] = np.full(F_unob_covariates_dim, np.nan)
        else:
            gamma_ob_I_matrix[:, t] = range_coefficients_max * np.random.uniform(0, 1, r_ob_covariates_dim)
            eta_unob_I_matrix[:, t] = range_coefficients_max * np.random.uniform(0, 1, F_unob_covariates_dim)

    # Noise
    for t in range(T_total):
        epsilon_N_matrix[:, t] = np.random.normal(0, noise_variance, N_units)
        if t < T_naught:
            xi_I_matrix[:, t] = np.full(N_units, np.nan)
        else:
            xi_I_matrix[:, t] = np.random.normal(0, noise_variance, N_units)

    # Generate potential outcomes
    for j in range(N_units):
        for t in range(T_total):
            Y_N_matrix[j, t] = (
                delta_N_vector[t] +
                np.dot(theta_ob_N_matrix[:, t], Z_ob_covariates_matrix[:, j]) +
                np.dot(lambda_unob_N_matrix[:, t], mu_unob_covariates_matrix[:, j]) +
                epsilon_N_matrix[j, t]
            )
            Y_I_matrix[j, t] = (
                upsilon_I_vector[t] +
                np.dot(gamma_ob_I_matrix[:, t], Z_ob_covariates_matrix[:, j]) +
                np.dot(eta_unob_I_matrix[:, t], mu_unob_covariates_matrix[:, j]) +
                xi_I_matrix[j, t]
            )
    # Build full DataFrame: pre-period observed + post-period potential
    Y_pre_df = pd.DataFrame(Y_N_matrix[:, :T_naught], columns=[f"Week {t+1}" for t in range(T_naught)])
    Y_post_df = pd.DataFrame(Y_I_matrix[:, T_naught:], columns=[f"Week {t+1}" for t in range(T_naught, T_total)])
    return {"data": pd.concat([Y_pre_df, Y_post_df], axis=1), "pre_periods": T_naught}, Z_ob_covariates_df, mu_unob_covariates_df


def _get_per_cluster_param(param, klabel, default=None):
    """Helper: param may be None, scalar, or dict {klabel: val}."""
    if param is None:
        return default
    if isinstance(param, dict):
        return param.get(klabel, default)
    return param  # scalar

def SCMEXP(Y,
                                     clusters,
                                     m_eq=None,
                                     m_min=None,
                                     m_max=None,
                                     exclusive=False,
                                     weakly_targeted=False,
                                     beta=1e-6,  # Default small value; adjustable if weakly_targeted
                                     solver=cp.ECOS_BB,
                                     verbose=False):
    """
    Clustered synthetic control that matches each cluster's population mean, with optional weakly-targeted design.
    Args:
        Y : np.ndarray, shape (N, T)   -- rows = units, cols = time.
        clusters : array-like length N -- cluster label (ints or strings) for each unit.
        m_eq / m_min / m_max : int or dict(cluster_label->int) or None
            Constraints for number of selected (treated) units PER CLUSTER.
        exclusive : bool
            If True, enforce sum_k z[j,k] <= 1 (a unit can be chosen in at most one cluster).
        weakly_targeted : bool
            If True, replace control-to-population match with control-to-treated match (beta-weighted).
        beta : float > 0 -- Trade-off parameter for weakly-targeted design (ignored if weakly_targeted=False).
        solver : cvxpy solver (default ECOS_BB)
        verbose : bool, pass to prob.solve(...)
    Returns:
        dict with keys:
            - w_opt (N x K) treated weights per cluster
            - v_opt (N x K) control weights per cluster
            - z_opt (N x K) binary selection indicators per cluster
            - y_syn_treated_clusters list length K (each shape (T,))
            - y_syn_control_clusters list length K (each shape (T,))
            - Xbar_clusters list length K (each shape (T,))
            - cluster_labels list of unique cluster labels (in order)
    """
    Y = np.asarray(Y)
    N, T = Y.shape
    clusters = np.asarray(clusters)
    if clusters.shape[0] != N:
        raise ValueError("clusters must have length N (rows of Y).")

    cluster_labels = np.unique(clusters)
    K = len(cluster_labels)

    # Map label -> column index (0..K-1) for consistent ordering
    label_to_k = {lab: i for i, lab in enumerate(cluster_labels)}

    # boolean mask M: shape (N, K) where M[j,k] True if unit j in cluster k
    M = np.zeros((N, K), dtype=bool)
    for j in range(N):
        M[j, label_to_k[clusters[j]]] = True

    # Compute cluster-level population means Xbar_k (shape (T,))
    Xbar_clusters = []
    cluster_members = []
    for k_idx, lab in enumerate(cluster_labels):
        members = np.where(M[:, k_idx])[0]
        if members.size == 0:
            raise ValueError(f"Cluster '{lab}' has no members.")
        cluster_members.append(members)
        Xbar_k = Y[members, :].mean(axis=0)  # shape (T,)
        Xbar_clusters.append(Xbar_k)

    # CVXPY variables: per-cluster
    w = cp.Variable((N, K), nonneg=True)   # treated weights per cluster
    v = cp.Variable((N, K), nonneg=True)   # control weights per cluster
    z = cp.Variable((N, K), boolean=True)  # selection indicators per cluster

    constraints = []

    # Enforce mask: non-members can't have weights/selections for that cluster
    for k in range(K):
        for j in range(N):
            if not M[j, k]:
                constraints += [w[j, k] == 0, v[j, k] == 0, z[j, k] == 0]

    # Per-cluster constraints: weights sum to 1 over cluster members; link w/v to z
    for k_idx, lab in enumerate(cluster_labels):
        members = cluster_members[k_idx]

        # weight sums = 1 inside cluster
        constraints += [cp.sum(w[members, k_idx]) == 1]
        constraints += [cp.sum(v[members, k_idx]) == 1]

        # selection cardinality constraints (flexible)
        m_eq_k = _get_per_cluster_param(m_eq, lab, default=None)
        m_min_k = _get_per_cluster_param(m_min, lab, default=None)
        m_max_k = _get_per_cluster_param(m_max, lab, default=None)

        if m_eq_k is not None:
            constraints += [cp.sum(z[members, k_idx]) == int(m_eq_k)]
        if m_min_k is not None:
            constraints += [cp.sum(z[members, k_idx]) >= int(m_min_k)]
        if m_max_k is not None:
            constraints += [cp.sum(z[members, k_idx]) <= int(m_max_k)]

        # link weights to selection indicators
        for j in members:
            constraints += [w[j, k_idx] <= z[j, k_idx]]
            constraints += [v[j, k_idx] <= 1 - z[j, k_idx]]

    # Optional exclusivity across clusters: a unit can't be selected in more than one cluster
    if exclusive:
        for j in range(N):
            constraints += [cp.sum(z[j, :]) <= 1]

    # Build objective: sum of cluster-level matching errors (treated + control)
    Y_T = Y.T  # shape (T, N)
    obj_terms = []
    for k_idx in range(K):
        Xbar_k = Xbar_clusters[k_idx]  # numpy array (T,)
        syn_treated_k = Y_T @ w[:, k_idx]  # shape (T,)
        syn_control_k = Y_T @ v[:, k_idx]  # shape (T,)
        obj_terms.append(cp.sum_squares(Xbar_k - syn_treated_k))  # Match treated to population

        # Replace control match based on weakly_targeted flag
        if weakly_targeted:
            obj_terms.append(beta * cp.sum_squares(syn_treated_k - syn_control_k))  # Match control to treated
        else:
            obj_terms.append(cp.sum_squares(Xbar_k - syn_control_k))  # Match control to population

    objective = cp.Minimize(cp.sum(obj_terms))

    prob = cp.Problem(objective, constraints)
    prob.solve(solver=solver, verbose=verbose)

    # Extract values
    w_opt = w.value  # shape (N, K)
    v_opt = v.value
    z_opt = z.value

    # Build cluster-level synthetic series
    y_syn_treated_clusters = []
    y_syn_control_clusters = []
    for k_idx in range(K):
        w_k = w_opt[:, k_idx]
        v_k = v_opt[:, k_idx]
        y_syn_treated_clusters.append(Y_T @ w_k)   # shape (T,)
        y_syn_control_clusters.append(Y_T @ v_k)

    return {
        "w_opt": w_opt,
        "v_opt": v_opt,
        "z_opt": z_opt,
        "y_syn_treated_clusters": y_syn_treated_clusters,
        "y_syn_control_clusters": y_syn_control_clusters,
        "Xbar_clusters": Xbar_clusters,
        "cluster_labels": list(cluster_labels),
        "cluster_members": cluster_members
    }




import numpy as np
from congestprice import SCMEXP, generate_synthetic_hotel_data
import matplotlib.pyplot as plt

from mlsynth.utils.estutils import effects

# Example usage
dataset, Z_cov, mu_cov  = generate_synthetic_hotel_data()

Y =dataset['data'].iloc[:, :dataset["pre_periods"]].to_numpy()

result = SCMEXP(Y, np.array(["Group1"] * Y.shape[0]), m_min=1, m_max=2, weakly_targeted=True, beta=1.0)



# Recompute full-period cluster means from original dataset
Y_full = dataset["data"].to_numpy()
Xbar_full = []
for members in result["cluster_members"]:
    Xbar_full.append(Y_full[members, :].mean(axis=0))  # shape (T_total,)

# Apply weights to get synthetic treated/control across the full horizon
Y_full_T = Y_full.T
synthetics_full = []
for k_idx, lab in enumerate(result["cluster_labels"]):
    w_k = result["w_opt"][:, k_idx]
    v_k = result["v_opt"][:, k_idx]
    syn_treated = Y_full_T @ w_k
    syn_control = Y_full_T @ v_k
    synthetics_full.append((syn_treated, syn_control))

postperiod = Y_full.shape[1]-dataset["pre_periods"]

attdict, fitdict, Vectors = effects.calculate(synthetics_full[0][0], synthetics_full[0][1],dataset["pre_periods"], postperiod)

# Example plot for cluster 0
weeks = dataset["data"].columns
T_total = dataset["data"].shape[1]
x_axis = np.arange(1, T_total + 1)

plt.plot(x_axis, synthetics_full[0][0], label="Synthetic treated")
plt.plot(x_axis, synthetics_full[0][1], label="Synthetic control")

# Intervention marker
plt.axvline(x=dataset["pre_periods"], color="k", linestyle="--", label="Intervention")

plt.xlabel("Time period")
plt.ylabel("Outcome")
plt.legend()
plt.show()
