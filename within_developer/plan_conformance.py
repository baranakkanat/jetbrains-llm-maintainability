"""Plan-exact versions of the two places where analyze_overnight.py departs from ANALYSIS_PLAN.md.

Written before the overnight results were seen (see PROGRESS.md, 05:00).

  1. H2 with the controls the plan names: "same model as H1 without the
     prior-fix control" = pair + log(lines changed) + log(production files)
     + author FE + repo-month FE. BH is recomputed over H1, H2 (plan-exact),
     H3a, H3b.
  2. H4 verdict as the plan words it: robust if the sign equals the sign of the
     earlier run (results_2025-06) and the 95% CI excludes zero in each of the
     variants (a)-(d).

Reads results_overnight/overnight_core_commits.csv, overnight_confirmatory.csv
and overnight_h4.csv; writes results_overnight/plan_conformance.csv.

Usage: python plan_conformance.py
"""

import warnings

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests

from analyze_overnight import fe_ols

warnings.filterwarnings("ignore")
OUT = "results_overnight"


def main():
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    core = pd.read_csv(f"{OUT}/overnight_core_commits.csv")
    conf = pd.read_csv(f"{OUT}/overnight_confirmatory.csv")
    h4 = pd.read_csv(f"{OUT}/overnight_h4.csv")
    earlier = pd.read_csv("results_2025-06/within_developer_clustered.csv")

    # 1. H2 with log(production files) ---------------------------------------
    r = fe_ols(core, "reverted", ["is_pair"], ["log_size", "log_prod_files"],
               ["author", "repo_month"])[0]
    h2_plan = {"hypothesis": "H2 reverted (plan-exact controls)", **r}
    family = pd.concat([conf[~conf.hypothesis.str.startswith("H2")].drop(columns="p_BH"),
                        pd.DataFrame([h2_plan])], ignore_index=True)
    family["p_BH"] = multipletests(family["p"], method="fdr_bh")[1]
    print("=== Confirmatory family with plan-exact H2 (BH across H1, H2, H3a, H3b) ===")
    print(family.to_string(index=False))
    print("\nScript H2 for comparison:")
    print(conf[conf.hypothesis.str.startswith("H2")].to_string(index=False))

    # 2. H4 verdict over (a)-(d) against the earlier run's sign -----------------
    sign_before = dict(zip(earlier.outcome, np.sign(earlier.effect)))
    rows = []
    for outcome, g in h4.groupby("outcome"):
        v = g[g.variant.str.match(r"^[a-d]_")]
        same = (np.sign(v.effect) == sign_before[outcome]).all()
        excl = ((v.ci_low > 0) | (v.ci_high < 0)).all()
        rows.append({"outcome": outcome, "earlier_sign": int(sign_before[outcome]),
                     "variants": len(v), "same_sign_a_to_d": bool(same),
                     "ci_excludes_0_a_to_d": bool(excl), "robust_per_plan": bool(same and excl)})
    verdict = pd.DataFrame(rows)
    print("\n=== H4 verdict as worded in the plan ((a)-(d), sign of the earlier run) ===")
    print(verdict.to_string(index=False))

    pd.concat([family.assign(section="confirmatory_plan_exact_H2"),
               verdict.assign(section="h4_verdict_per_plan")], ignore_index=True
              ).to_csv(f"{OUT}/plan_conformance.csv", index=False)


if __name__ == "__main__":
    main()
