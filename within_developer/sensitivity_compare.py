"""Main results (results_overnight/) vs the sensitivity run with fixed mining code (results_sensitivity/).

The sensitivity run differs only in the mining code (see run_sensitivity.sh):
*Test.kts as test code, old paths of renamed files kept, jetbrains-junie[bot]
as agent, rename detection and the start time pinned. Same clones, same
analysis script.

Usage: python sensitivity_compare.py > results_sensitivity/comparison.txt
"""

import numpy as np
import pandas as pd

MAIN, SENS = "results_overnight", "results_sensitivity"


def fmt(r):
    return f"{r.effect:+.4f} [{r.ci_low:+.4f}, {r.ci_high:+.4f}] p={r.p:.4f}"


def main():
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_colwidth", 60)

    core = {d: pd.read_csv(f"{d}/overnight_core_commits.csv") for d in (MAIN, SENS)}
    print("=== Core sample ===")
    for d, c in core.items():
        print(f"{d}: {c.author.nunique()} developers, {len(c)} commits, {int(c.is_pair.sum())} AI-co-authored")
    a, b = set(core[MAIN].sha), set(core[SENS].sha)
    print(f"commits only in main: {len(a - b)}; only in sensitivity: {len(b - a)}")
    for label, shas, d in [("only in main", a - b, MAIN), ("only in sensitivity", b - a, SENS)]:
        if shas:
            print(f"  {label}:")
            print(core[d][core[d].sha.isin(shas)][["repo", "sha", "author", "group", "prod_files"]]
                  .to_string(index=False))
    both = core[MAIN].merge(core[SENS], on="sha", suffixes=("_main", "_sens"))
    for col in ["followup_fix", "log_prior_fix", "reverted", "primary_file", "added_comment_share",
                "log_size", "cc_delta_modified_mean", "net_cc_per_100_added"]:
        x, y = both[f"{col}_main"], both[f"{col}_sens"]
        changed = ~((x == y) | (x.isna() & y.isna()))
        print(f"common commits with a different {col}: {int(changed.sum())}")
    h1 = both[both.followup_eligible_main & both.followup_eligible_sens]
    flips = h1[h1.followup_fix_main != h1.followup_fix_sens]
    print("follow-up fix changes among eligible common commits:",
          flips.groupby(["repo_main", "group_main"]).size().to_dict(),
          f"(0 -> 1: {int((flips.followup_fix_sens == 1).sum())}, 1 -> 0: {int((flips.followup_fix_sens == 0).sum())})")

    print("\n=== Confirmatory (BH across H1, H2, H3a, H3b) ===")
    conf = {d: pd.read_csv(f"{d}/overnight_confirmatory.csv") for d in (MAIN, SENS)}
    rows = []
    for (_, m), (_, s) in zip(conf[MAIN].iterrows(), conf[SENS].iterrows()):
        rows.append({"hypothesis": m.hypothesis, "main": fmt(m), "main_p_BH": round(m.p_BH, 4),
                     "sensitivity": fmt(s), "sens_p_BH": round(s.p_BH, 4),
                     "n_main": m.n, "n_sens": s.n})
    out_conf = pd.DataFrame(rows)
    print(out_conf.to_string(index=False))

    print("\n=== H4 ===")
    h4 = {d: pd.read_csv(f"{d}/overnight_h4.csv") for d in (MAIN, SENS)}
    merged = h4[MAIN].merge(h4[SENS], on=["outcome", "variant"], suffixes=("_main", "_sens"))
    rows = []
    for r in merged.itertuples():
        rows.append({"outcome": r.outcome, "variant": r.variant,
                     "main": f"{r.effect_main:+.4f} [{r.ci_low_main:+.4f}, {r.ci_high_main:+.4f}]",
                     "sensitivity": f"{r.effect_sens:+.4f} [{r.ci_low_sens:+.4f}, {r.ci_high_sens:+.4f}]",
                     "n_main": r.n_main, "n_sens": r.n_sens})
    out_h4 = pd.DataFrame(rows)
    print(out_h4.to_string(index=False))

    earlier = pd.read_csv("results_2025-06/within_developer_clustered.csv")
    sign = dict(zip(earlier.outcome, np.sign(earlier.effect)))
    print("\nRobust per plan (sign of the earlier run and CI excludes 0 in each of (a)-(d)):")
    for d, h in h4.items():
        v = h[h.variant.str.match(r"^[a-d]_")]
        verdict = v.groupby("outcome").apply(
            lambda g: bool((np.sign(g.effect) == sign[g.name]).all()
                           and ((g.ci_low > 0) | (g.ci_high < 0)).all()))
        print(f"  {d}: {verdict.to_dict()}")

    out_conf.to_csv(f"{SENS}/comparison_confirmatory.csv", index=False)
    out_h4.to_csv(f"{SENS}/comparison_h4.csv", index=False)


if __name__ == "__main__":
    main()
