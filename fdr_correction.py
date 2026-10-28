"""
Multiple-comparison correction and honest hypothesis accounting.

Reads before_after_table.csv (one row per repository x metric), applies
Benjamini-Hochberg FDR correction across all valid p-values, and recomputes
the hypothesis verdict using the FULL sample as the denominator instead of
only the subset with significant findings.

Output: before_after_table_fdr.csv and a printed summary.
"""

import pandas as pd
import numpy as np
from statsmodels.stats.multitest import multipletests

ALPHA = 0.05
INPUT = "before_after_table.csv"
OUTPUT = "before_after_table_fdr.csv"

# Metrics used to judge the maintainability hypothesis, and the direction
# of change that counts as degradation.
MAINTAINABILITY = {
    "Bug-Fix Ratio": "up",
    "Cyclomatic Complexity": "up",
    "Avg Function Length": "up",
}

df = pd.read_csv(INPUT)
df["p_num"] = pd.to_numeric(df["p-value"], errors="coerce")

valid = df["p_num"].notna()
n_tests_total = len(df)
n_tests_valid = int(valid.sum())

# Benjamini-Hochberg across every test actually performed
reject, p_adj, _, _ = multipletests(df.loc[valid, "p_num"], alpha=ALPHA, method="fdr_bh")
df.loc[valid, "p_adj_BH"] = p_adj
df.loc[valid, "Significant_FDR"] = np.where(reject, "yes", "")
df["Significant_FDR"] = df["Significant_FDR"].fillna("")

df.drop(columns=["p_num"]).to_csv(OUTPUT, index=False)

n_sig_raw = int((df["Significant"] == "✓").sum())
n_sig_fdr = int((df["Significant_FDR"] == "yes").sum())
expected_by_chance = ALPHA * n_tests_valid

print("=== MULTIPLE-COMPARISON CORRECTION (Benjamini-Hochberg, alpha=0.05) ===")
print(f"Repositories in table       : {df['Repository'].nunique()}")
print(f"Tests in table              : {n_tests_total}")
print(f"Tests with a valid p-value  : {n_tests_valid}")
print(f"False positives expected by chance at p<0.05: ~{expected_by_chance:.0f}")
print(f"Significant, uncorrected    : {n_sig_raw}")
print(f"Significant, BH-corrected   : {n_sig_fdr}")
print()


def change_direction(value):
    """Return +1 if the metric increased, -1 if it decreased, else None."""
    try:
        return 1 if float(str(value).replace("%", "").replace("+", "")) > 0 else -1
    except (TypeError, ValueError):
        return None


def verdict_table(sig_column, label):
    sub = df[df["Metric"].isin(MAINTAINABILITY)]
    sig = sub[sub[sig_column].isin(["✓", "yes"])]

    degraded_repos, improved_repos = set(), set()
    per_repo = {}
    for repo, rows in sig.groupby("Repository"):
        d = i = 0
        for _, row in rows.iterrows():
            direction = change_direction(row["Change %"])
            if direction is None:
                continue
            # every maintainability metric here degrades when it goes up
            if direction > 0:
                d += 1
            else:
                i += 1
        if d or i:
            per_repo[repo] = (d, i)
            (degraded_repos if d >= i else improved_repos).add(repo)

    n_total_repos = df["Repository"].nunique()
    n_with_finding = len(per_repo)

    print(f"--- {label} ---")
    print(f"Repositories with any significant maintainability finding: "
          f"{n_with_finding} / {n_total_repos}")
    print(f"  consistent with degradation : {len(degraded_repos)}")
    print(f"  consistent with improvement : {len(improved_repos)}")
    if n_total_repos:
        print(f"Share of the FULL sample showing degradation: "
              f"{len(degraded_repos) / n_total_repos * 100:.1f}% "
              f"({len(degraded_repos)}/{n_total_repos})")
    if n_with_finding:
        print(f"Share of the significant SUBSET showing degradation: "
              f"{len(degraded_repos) / n_with_finding * 100:.1f}% "
              f"({len(degraded_repos)}/{n_with_finding})  "
              f"<- conditional on significance, not a population estimate")
    print()
    return per_repo


verdict_table("Significant", "Uncorrected (p < 0.05)")
per_repo_fdr = verdict_table("Significant_FDR", "BH-corrected (FDR < 0.05)")

if per_repo_fdr:
    print("Repositories surviving FDR correction:")
    for repo, (d, i) in sorted(per_repo_fdr.items()):
        print(f"  {repo}: {d} degraded, {i} improved")

print()
print(f"Saved: {OUTPUT}")
