"""Pooled within-developer analysis of AI-paired vs. unlabelled commits.

Reads m_<repo>.csv files written by mine_commits.py. For each repository the
comparison window is the months in which AI-labelled commits exist, and only
commits that touch production code are used.

Two questions are kept apart on purpose:
  - WHERE is AI used?   complexity of the methods a commit touches
  - WHAT does it add?   complexity added to modified methods, complexity of new
                        methods, net complexity per 100 added lines

Usage: python analyze_pooled.py m_ideavim.csv m_intellij-scala.csv m_kotlin.csv
"""

import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import binomtest, mannwhitneyu
from statsmodels.stats.multitest import multipletests

OUTCOMES = {
    "cc_changed_mean": ("WHERE", "Complexity of methods touched"),
    "nloc_changed_mean": ("WHERE", "Length of methods touched"),
    "cc_delta_modified_mean": ("WHAT", "Complexity added to modified methods"),
    "cc_new_methods_mean": ("WHAT", "Complexity of new methods"),
    "nloc_new_methods_mean": ("WHAT", "Length of new methods"),
    "net_cc_per_100_added": ("WHAT", "Net complexity per 100 added lines"),
    "added_comment_share": ("WHAT", "Comment share of added lines"),
    "touches_tests": ("PROCESS", "Commit touches tests"),
    "is_fix_msg": ("PROCESS", "Message says fix"),
    "log_size": ("PROCESS", "log(lines changed)"),
}
MIN_EACH = 8   # commits of each kind an author needs to enter the within-developer model


def load(paths):
    frames = []
    for p in paths:
        d = pd.read_csv(p)
        d["date"] = pd.to_datetime(d["date"], utc=True)
        d["month"] = d["date"].dt.strftime("%Y-%m")
        d = d[d["prod_files"] > 0].copy()
        ai_months = set(d.loc[d["group"] != "human", "month"])
        frames.append(d[d["month"].isin(ai_months)])
    d = pd.concat(frames, ignore_index=True)
    d["touches_tests"] = (d["test_files"] > 0).astype(float)
    d["is_fix_msg"] = d["is_fix_msg"].astype(float)
    d["log_size"] = np.log1p(d["added_code"] + d["deleted_code"])
    d["repo_month"] = d["repo"] + "_" + d["month"]
    # Winsorize heavy-tailed continuous outcomes within each repository.
    for col in ["cc_changed_mean", "nloc_changed_mean", "cc_delta_modified_mean",
                "cc_new_methods_mean", "nloc_new_methods_mean", "net_cc_per_100_added"]:
        lo = d.groupby("repo")[col].transform(lambda s: s.quantile(0.01))
        hi = d.groupby("repo")[col].transform(lambda s: s.quantile(0.99))
        d[col] = d[col].clip(lo, hi)
    return d


def eligible_authors(d):
    counts = d[d.group.isin(["human", "pair"])].groupby(["author", "group"]).size().unstack(fill_value=0)
    if "pair" not in counts:
        return []
    return counts[(counts["pair"] >= MIN_EACH) & (counts["human"] >= MIN_EACH)].index.tolist()


def within_developer(d, authors):
    w = d[d.group.isin(["human", "pair"]) & d.author.isin(authors)].copy()
    w["pair"] = (w.group == "pair").astype(int)
    rows = []
    for col, (kind, label) in OUTCOMES.items():
        dd = w.dropna(subset=[col])
        if dd.pair.sum() < 10:
            continue
        controls = "" if col == "log_size" else " + log_size"
        formula = f"{col} ~ pair{controls} + C(author) + C(repo_month)"
        fit = smf.ols(formula, data=dd)
        if dd.author.nunique() >= 8:
            res = fit.fit(cov_type="cluster", cov_kwds={"groups": dd["author"]})
        else:
            res = fit.fit(cov_type="HC3")
        # author-level sign test: median(pair) - median(human) per author
        diffs = []
        for a, g in dd.groupby("author"):
            x, y = g.loc[g.pair == 1, col], g.loc[g.pair == 0, col]
            if len(x) >= 3 and len(y) >= 3:
                diffs.append(x.median() - y.median())
        diffs = np.array(diffs)
        lower, higher = int((diffs < 0).sum()), int((diffs > 0).sum())
        sign_p = binomtest(lower, lower + higher, 0.5).pvalue if lower + higher else np.nan
        sd = dd[col].std()
        rows.append({"kind": kind, "outcome": label, "n": len(dd), "n_pair": int(dd.pair.sum()),
                     "authors": dd.author.nunique(), "effect": res.params["pair"],
                     "ci_low": res.conf_int().loc["pair", 0], "ci_high": res.conf_int().loc["pair", 1],
                     "std_effect": res.params["pair"] / sd if sd else np.nan,
                     "p": res.pvalues["pair"], "authors_lower": lower, "authors_higher": higher,
                     "sign_p": sign_p})
    out = pd.DataFrame(rows)
    out["p_BH"] = multipletests(out["p"], method="fdr_bh")[1]
    return out


def per_repo(d, a, b):
    rows = []
    for repo, g in d.groupby("repo"):
        for col, (kind, label) in OUTCOMES.items():
            x = g.loc[g.group == a, col].dropna()
            y = g.loc[g.group == b, col].dropna()
            if len(x) < 10 or len(y) < 10:
                continue
            rows.append({"repo": repo, "outcome": label, f"n_{b}": len(y),
                         f"median_{a}": x.median(), f"median_{b}": y.median(),
                         f"mean_{a}": x.mean(), f"mean_{b}": y.mean(),
                         "p": mannwhitneyu(x, y, alternative="two-sided").pvalue})
    out = pd.DataFrame(rows)
    if not out.empty:
        out["p_BH"] = multipletests(out["p"], method="fdr_bh")[1]
    return out


def main(paths):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:.3f}")
    d = load(paths)
    print("Production-code commits in AI-active months:")
    print(pd.crosstab(d.repo, d.group, margins=True).to_string())
    print("\nAI-active window per repo:")
    print(d.groupby("repo").month.agg(["min", "max", "nunique"]).to_string())
    print("\nTools / models among labelled commits:")
    print(d[d.group != "human"].groupby(["repo", "tool"]).size().to_string())

    authors = eligible_authors(d)
    print(f"\nAuthors with >= {MIN_EACH} AI-paired and >= {MIN_EACH} unlabelled commits: "
          f"{len(authors)}")
    print(d[d.author.isin(authors)].groupby(["repo", "author", "group"]).size()
          .unstack(fill_value=0).to_string())

    print("\n=== WITHIN-DEVELOPER: AI-paired vs own unlabelled commits "
          "(size, author and repo-month fixed effects) ===")
    print(within_developer(d, authors).to_string(index=False))

    print("\n=== PER REPO, unadjusted: pair vs human ===")
    print(per_repo(d, "human", "pair").to_string(index=False))
    print("\n=== PER REPO, unadjusted: agent vs human ===")
    print(per_repo(d, "human", "agent").to_string(index=False))


if __name__ == "__main__":
    main(sys.argv[1:])
