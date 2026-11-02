"""(c) H4 base coefficients re-estimated with explicit dummy variables (no
demeaning), OLS with standard errors clustered by author.

Run: .venv/bin/python3 within_developer/verification/c_dummy_regression.py
Writes c_dummy_regression_output.txt.
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrices
from scipy import stats

from common import HERE, WD

OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def manual_cluster_se(res, groups, term):
    """Sandwich estimator computed by hand (no statsmodels cov), CR0 and CR1."""
    X = res.model.exog
    e = res.resid.values
    n, k = X.shape
    k = int(np.linalg.matrix_rank(X))
    xtx_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((X.shape[1], X.shape[1]))
    g = pd.Series(groups).astype("category").cat.codes.values
    G = g.max() + 1
    for j in range(G):
        s = (X[g == j] * e[g == j, None]).sum(axis=0)
        meat += np.outer(s, s)
    V0 = xtx_inv @ meat @ xtx_inv
    j = res.model.exog_names.index(term)
    cr0 = np.sqrt(V0[j, j])
    cr1 = cr0 * np.sqrt(G / (G - 1) * (n - 1) / (n - k))
    return cr0, cr1, G, n, k


def full_rank(X: pd.DataFrame) -> pd.DataFrame:
    """Drop dummy columns that are exact linear combinations of earlier ones.

    Authors are nested in repositories, so per repository the author dummies
    and the repo-month dummies sum to the same vector; patsy's treatment coding
    leaves such exact collinearities in. Columns are added left to right and
    kept only if they raise the rank (the slope terms come first, so they are
    always kept).
    """
    keep = []
    for c in X.columns:
        trial = keep + [c]
        if np.linalg.matrix_rank(X[trial].values) == len(trial):
            keep.append(c)
    return X[keep]


def run(df, formula, term, label, ref):
    cols = [c.strip() for c in formula.replace("~", "+").split("+")]
    cols = [c[2:-1] if c.startswith("C(") else c for c in cols]
    d = df.dropna(subset=cols).copy().reset_index(drop=True)
    say(f"\n=== {label} ===\n{formula}  (n={len(d)}, authors={d.author.nunique()}, repo_months={d.repo_month.nunique()})")
    y, X = dmatrices(formula, d, return_type="dataframe")
    Xf = full_rank(X)
    say(f"design: {X.shape[1]} columns from patsy, {X.shape[1] - Xf.shape[1]} exactly collinear dummy column(s) dropped: "
        f"{[c for c in X.columns if c not in Xf.columns]}")
    m = sm.OLS(y, Xf)
    # Stata-style CR1: G/(G-1) * (N-1)/(N-K), t(G-1) reference distribution.
    r_t = m.fit(cov_type="cluster", cov_kwds={"groups": d.author, "use_correction": True}, use_t=True)
    # Same CR1 SE, normal reference distribution.
    r_z = m.fit(cov_type="cluster", cov_kwds={"groups": d.author, "use_correction": True}, use_t=False)
    b = r_t.params[term]
    cr0, cr1, G, n, k = manual_cluster_se(r_t, d.author.values, term)
    se_t = r_t.bse[term]
    say(f"coef {term} = {b:.6f}")
    say(f"K (rank of design incl. dummies) = {k}, clusters G = {G}")
    say(f"[A] CR1 (G/(G-1)*(N-1)/(N-K)), t(G-1={G-1}): SE {se_t:.6f}, "
        f"95% CI [{r_t.conf_int().loc[term, 0]:.6f}, {r_t.conf_int().loc[term, 1]:.6f}], p {r_t.pvalues[term]:.6g}")
    say(f"[B] CR1, normal:                        SE {r_z.bse[term]:.6f}, "
        f"95% CI [{r_z.conf_int().loc[term, 0]:.6f}, {r_z.conf_int().loc[term, 1]:.6f}], p {r_z.pvalues[term]:.6g}")
    say(f"    manual sandwich check: CR0 {cr0:.6f}, CR1 {cr1:.6f} (statsmodels {se_t:.6f})")
    # Correction without the (N-1)/(N-K) term (what a demeaned regression that
    # counts only the non-absorbed regressors in K gets almost exactly).
    k_small = len([t for t in r_t.params.index if not t.startswith("C(") and t != "Intercept"])
    se_c = cr0 * np.sqrt(G / (G - 1) * (n - 1) / (n - k_small))
    z = b / se_c
    say(f"[C] G/(G-1)*(N-1)/(N-{k_small}) [K = slope regressors only], normal: SE {se_c:.6f}, "
        f"95% CI [{b - 1.959964 * se_c:.6f}, {b + 1.959964 * se_c:.6f}], p {2 * stats.norm.sf(abs(z)):.6g}")
    say(f"analysis (overnight_h4.csv): coef {ref.effect:.6f}, 95% CI [{ref.ci_low:.6f}, {ref.ci_high:.6f}], "
        f"p {ref.p:.6g}, n {ref.n}, clusters {ref.clusters}; implied SE if normal {(ref.ci_high - ref.ci_low) / (2 * 1.959964):.6f}")
    say(f"coef difference fresh - analysis = {b - ref.effect:.2e}")


def main():
    df = pd.read_csv(os.path.join(WD, "results_overnight", "overnight_core_commits.csv"))
    h4 = pd.read_csv(os.path.join(WD, "results_overnight", "overnight_h4.csv"))
    ref1 = h4[(h4.outcome == "Comment share of added lines") & (h4.variant == "base")].iloc[0]
    ref2 = h4[(h4.outcome == "log(lines changed)") & (h4.variant == "base")].iloc[0]
    run(df, "added_comment_share ~ is_pair + log_size + C(author) + C(repo_month)", "is_pair",
        "Comment share of added lines, base", ref1)
    run(df, "log_size ~ is_pair + C(author) + C(repo_month)", "is_pair",
        "log(lines changed), base", ref2)
    # All H4 rows under t(G-1) instead of normal, using the SE implied by each CI.
    h = h4.copy()
    h["se"] = (h.ci_high - h.ci_low) / (2 * 1.96)
    h["p_t"] = 2 * stats.t.sf((h.effect / h.se).abs(), h.clusters - 1)
    tc = stats.t.ppf(0.975, h.clusters - 1)
    h["excl0_normal"] = (h.ci_low > 0) | (h.ci_high < 0)
    h["excl0_t"] = ((h.effect - tc * h.se) > 0) | ((h.effect + tc * h.se) < 0)
    say("\nAll overnight_h4.csv rows, normal vs t(G-1) inference (SE implied by the CI):")
    say(h[["outcome", "variant", "effect", "p", "p_t", "excl0_normal", "excl0_t"]].to_string(index=False))
    with open(os.path.join(HERE, "c_dummy_regression_output.txt"), "w") as fh:
        fh.write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
