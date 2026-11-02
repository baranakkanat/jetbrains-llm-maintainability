"""Sensitivity of the reported inference (added after the results; not confirmatory).

  1. t(G-1) instead of the normal reference for every confirmatory and H4 row.
  2. Variant (b) with the primary-file fixed effects counted in the
     small-sample correction. analyze_overnight.py counts only the non-absorbed
     regressors; that is standard for fixed effects nested in the clusters
     (author) but not for repo-month or file effects. Two versions:
       - singletons kept: all fixed-effect levels counted (most conservative);
       - singletons dropped iteratively, as reghdfe does, then levels counted.
  3. H1: how much of the raw gap in follow-up-fix rates is within developer.
  4. Reach of the rename defect found by the verification: how many fix-subject
     commits rename a production file (file_history.py links them to the new
     path only).

Reads results_overnight/overnight_core_commits.csv, overnight_confirmatory.csv,
overnight_h4.csv and the clones in repos/.
Usage: python inference_checks.py > results_overnight/inference_checks.txt
"""

import subprocess
import warnings

import numpy as np
import pandas as pd
from scipy.stats import norm, t

from analyze_overnight import H4_OUTCOMES, fe_ols
from file_history import CODE_EXT, FIX_SUBJECT, TEST_PATH

warnings.filterwarnings("ignore")
OUT = "results_overnight"
G = 19


def t_reference():
    print("=== 1. t(G-1) reference instead of normal ===")
    rows = []
    for name in ["overnight_confirmatory.csv", "overnight_h4.csv"]:
        d = pd.read_csv(f"{OUT}/{name}")
        for r in d.itertuples():
            se = (r.ci_high - r.effect) / 1.96
            df = r.clusters - 1
            q = t.ppf(0.975, df)
            rows.append({"row": getattr(r, "hypothesis", None) or f"{r.outcome} | {r.variant}",
                         "clusters": r.clusters, "p_normal": r.p,
                         "p_t": 2 * t.sf(abs(r.effect / se), df),
                         "ci_t_low": r.effect - q * se, "ci_t_high": r.effect + q * se})
    out = pd.DataFrame(rows)
    out["excludes_0_normal"] = out.p_normal < 0.05
    out["excludes_0_t"] = (out.ci_t_low > 0) | (out.ci_t_high < 0)
    print(out.to_string(index=False))


def drop_singletons(d, fes):
    while True:
        keep = np.ones(len(d), bool)
        for f in fes:
            keep &= d.groupby(f)[f].transform("size").to_numpy() > 1
        if keep.all():
            return d
        d = d[keep]


def variant_b():
    print("\n=== 2. Variant (b): primary-file fixed effects in the small-sample correction ===")
    core = pd.read_csv(f"{OUT}/overnight_core_commits.csv").dropna(subset=["primary_file"])
    fes = ["author", "repo_month", "primary_file"]
    rows = []
    for col, label in H4_OUTCOMES.items():
        controls = [] if col == "log_size" else ["log_size"]
        full = core.dropna(subset=[col] + controls)
        for version, data in [("singletons kept", full),
                              ("singletons dropped", drop_singletons(full, fes))]:
            r = fe_ols(data, col, ["is_pair"], controls, fes)[0]
            se_script = (r["ci_high"] - r["effect"]) / 1.96
            n, k_x = len(data), 1 + len(controls)
            # author is nested in the cluster and not counted; the other two are.
            k_fe = data.repo_month.nunique() - 1 + data.primary_file.nunique() - 1
            factor = np.sqrt((n - 1) / (n - k_x - k_fe)) / np.sqrt((n - 1) / (n - k_x))
            se = se_script * factor
            z = r["effect"] / se
            rows.append({"outcome": label, "version": version, "n": n, "fe_levels_counted": k_fe,
                         "effect": r["effect"], "se_script": se_script, "se_factor": factor,
                         "se_corrected": se, "p_normal": 2 * norm.sf(abs(z)),
                         "p_t18": 2 * t.sf(abs(z), G - 1)})
    print(pd.DataFrame(rows).to_string(index=False))


def h1_composition():
    print("\n=== 3. H1: raw gap vs within-developer gap (eligible commits) ===")
    core = pd.read_csv(f"{OUT}/overnight_core_commits.csv")
    h1 = core[core.followup_eligible]
    rate = h1.groupby("group").followup_fix.mean()
    print(f"raw: human {rate['human']:.4f}, pair {rate['pair']:.4f}, gap {rate['pair'] - rate['human']:+.4f}")
    by = h1.groupby(["author", "group"]).followup_fix.agg(["mean", "size"]).unstack()
    gap = by[("mean", "pair")] - by[("mean", "human")]
    w = by[("size", "pair")]
    print(f"within-author gap weighted by AI commits: {np.average(gap, weights=w):+.4f}; "
          f"authors with a higher rate on AI commits: {int((gap > 0).sum())} of {len(gap)}")
    print("rate by repository:", h1.groupby("repo").followup_fix.mean().round(4).to_dict())
    total, kept = core.groupby("group").size(), h1.groupby("group").size()
    print("excluded by the 30-day cut-off:",
          {g: f"{total[g] - kept[g]} of {total[g]} ({1 - kept[g] / total[g]:.0%})" for g in total.index})


def renamed_fixes():
    print("\n=== 4. Fix-subject commits that rename a production file (git log -M) ===")
    for repo in ["ideavim", "intellij-scala", "kotlin"]:
        out = subprocess.run(["git", "-C", f"repos/{repo}", "log", "--no-merges", "--since=2025-01-01",
                              "-M", "--name-status", "--format=\x01%H\x02%s"],
                             capture_output=True, text=True, errors="replace", check=True).stdout
        fixes = renaming = old_paths = 0
        for block in out.split("\x01")[1:]:
            head, _, body = block.partition("\n")
            subject = head.split("\x02", 1)[1]
            if not FIX_SUBJECT.search(subject):
                continue
            fixes += 1
            olds = [line.split("\t")[1] for line in body.splitlines() if line.startswith("R")]
            olds = [p for p in olds if p.endswith(CODE_EXT) and not TEST_PATH.search(p)]
            renaming += bool(olds)
            old_paths += len(olds)
        print(f"{repo}: fix-subject commits {fixes}; renaming a production file {renaming} "
              f"({old_paths} old paths)")


if __name__ == "__main__":
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    t_reference()
    variant_b()
    h1_composition()
    renamed_fixes()
