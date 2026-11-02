"""Exploratory (not pre-registered): JetBrains/intellij-community in the within-developer design.

Inputs: m2_intellij-community.csv from mine_selected.py (eligible developers'
commits plus all AI-labelled commits since 2025-09-01) and
fh_intellij-community_*.csv from file_history.py, plus the three main
repositories' inputs for the pooled run.

  X1  intellij-community alone: H1, H2 and the four H4 outcomes (base model),
      and per developer the sign of median(pair) - median(human).
  X2  pooled with ideavim, intellij-scala and kotlin: the same estimates.

With 4 developers in X1 the clustered standard errors rest on 4 clusters and
are not reliable; X1 is descriptive.

Usage: python exploratory_intellij_community.py
"""

import warnings

import numpy as np
import pandas as pd

from analyze_overnight import (H4_OUTCOMES, ai_active, eligible_authors, fe_ols, followup_fix,
                               load)

warnings.filterwarnings("ignore")
OUT = "results_exploratory"
MAIN = ["ideavim", "intellij-scala", "kotlin"]


def core_of(repos):
    m, c, f = load(repos)
    m = followup_fix(m, c, f)
    prod = m[(m.prod_files > 0) & m.group.isin(["human", "pair"])].copy()
    win = ai_active(prod)
    authors = eligible_authors(win)
    return win[win.author.isin(authors)].copy(), authors


def estimates(core, label):
    rows = []
    h1 = core[core.followup_eligible]
    specs = [("H1 follow-up fix (30d)", h1, "followup_fix",
              ["log_size", "log_prod_files", "log_prior_fix"]),
             ("H2 reverted", core, "reverted", ["log_size"])]
    specs += [(name, core, col, [] if col == "log_size" else ["log_size"])
              for col, name in H4_OUTCOMES.items()]
    for name, data, col, controls in specs:
        r = fe_ols(data, col, ["is_pair"], controls, ["author", "repo_month"])[0]
        means = data.groupby("group")[col].mean()
        rows.append({"analysis": label, "outcome": name, "mean_human": means.get("human", np.nan),
                     "mean_pair": means.get("pair", np.nan), **r})
    return pd.DataFrame(rows)


def per_developer(core):
    rows = []
    for col, name in {"followup_fix": "H1 follow-up fix (30d)", **H4_OUTCOMES}.items():
        for a, g in core.groupby("author"):
            x, y = g.loc[g.group == "pair", col].dropna(), g.loc[g.group == "human", col].dropna()
            if len(x) >= 3 and len(y) >= 3:
                rows.append({"outcome": name, "author": a, "n_pair": len(x), "n_human": len(y),
                             "median_pair": x.median(), "median_human": y.median(),
                             "mean_pair": x.mean(), "mean_human": y.mean()})
    return pd.DataFrame(rows)


def main():
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")

    core, authors = core_of(["intellij-community"])
    print(f"[X1] intellij-community: eligible developers {len(authors)}, commits {len(core)} "
          f"({int(core.is_pair.sum())} AI-paired), AI-active months {core.month.nunique()}")
    print(core.groupby(["author", "group"]).size().unstack(fill_value=0).to_string())
    x1 = estimates(core, "X1 intellij-community")
    print(x1.drop(columns="term").to_string(index=False))
    dev = per_developer(core)
    print("\n[X1] per developer:")
    print(dev.to_string(index=False))

    pooled, authors4 = core_of(MAIN + ["intellij-community"])
    print(f"\n[X2] pooled four repositories: eligible developers {len(authors4)}, "
          f"commits {len(pooled)} ({int(pooled.is_pair.sum())} AI-paired)")
    x2 = estimates(pooled, "X2 pooled with intellij-community")
    print(x2.drop(columns="term").to_string(index=False))

    pd.concat([x1, x2], ignore_index=True).to_csv(f"{OUT}/intellij_community_estimates.csv",
                                                  index=False)
    dev.to_csv(f"{OUT}/intellij_community_per_developer.csv", index=False)


if __name__ == "__main__":
    main()
