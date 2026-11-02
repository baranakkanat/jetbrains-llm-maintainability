"""Pre-registered analyses H1-H4 (see ANALYSIS_PLAN.md).

Inputs per repo: m2_<repo>.csv (mine_commits.py, since 2025-01-01) and
fh_<repo>_commits.csv / fh_<repo>_files.csv (file_history.py).

Fixed effects are absorbed by alternating demeaning, then the coefficients of
interest are estimated by OLS on the demeaned data with standard errors
clustered by author (Frisch-Waugh-Lovell).

Usage: python analyze_overnight.py ideavim intellij-scala kotlin
"""

import re
import sys
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import fisher_exact
from statsmodels.stats.multitest import multipletests

warnings.filterwarnings("ignore")
MIN_EACH = 8
FOLLOWUP_DAYS = 30
H4_OUTCOMES = {
    "log_size": "log(lines changed)",
    "added_comment_share": "Comment share of added lines",
    "cc_delta_modified_mean": "Complexity added to modified methods",
    "net_cc_per_100_added": "Net complexity per 100 added lines",
}
TYPE_RULES = [
    ("revert", r"^revert\b"),
    ("fix", r"\b(fix|fixes|fixed|fixing|bug|crash|regression|broken)\b"),
    ("test", r"^(add |update |fix )?tests?\b|\btests? for\b"),
    ("refactor", r"\b(refactor\w*|cleanup|clean up|rename\w*|move[sd]?|extract\w*|simplif\w*|"
                 r"reformat\w*|inline[sd]?)\b"),
    ("docs", r"\b(docs?|kdoc|javadoc|readme|documentation|comments?)\b"),
    ("build", r"\b(build|gradle|bump\w*|dependenc\w*|deps|version|ci|bootstrap)\b"),
    ("feature", r"\b(add\w*|implement\w*|support\w*|introduc\w*|new|enable\w*)\b"),
]


def commit_type(subject):
    s = str(subject).lower()
    for name, pattern in TYPE_RULES:
        if re.search(pattern, s):
            return name
    return "other"


# ---------------------------------------------------------------------------
def demean(df, cols, fes, tol=1e-9, max_iter=500):
    """Absorb several fixed effects from `cols` by alternating projections."""
    out = df[cols].astype(float).to_numpy().copy()
    codes = [pd.factorize(df[f])[0] for f in fes]
    for _ in range(max_iter):
        before = out.copy()
        for c in codes:
            counts = np.bincount(c)
            for j in range(out.shape[1]):
                means = np.bincount(c, weights=out[:, j]) / counts
                out[:, j] -= means[c]
        if np.abs(out - before).max() < tol:
            break
    return out


def fe_ols(df, y, interest, controls, fes, cluster="author"):
    cols = [y] + interest + controls
    d = df.dropna(subset=cols).copy()
    if len(d) < 30 or d[cluster].nunique() < 2:
        return [{"term": name, "effect": np.nan, "ci_low": np.nan, "ci_high": np.nan,
                 "p": np.nan, "n": len(d), "clusters": d[cluster].nunique()} for name in interest]
    dm = demean(d, cols, fes)
    Y, X = dm[:, 0], dm[:, 1:]
    res = sm.OLS(Y, X).fit(cov_type="cluster",
                           cov_kwds={"groups": pd.factorize(d[cluster])[0]})
    rows = []
    for k, name in enumerate(interest):
        b, se, p = float(res.params[k]), float(res.bse[k]), float(res.pvalues[k])
        rows.append({"term": name, "effect": b, "ci_low": b - 1.96 * se, "ci_high": b + 1.96 * se,
                     "p": p, "n": len(d), "clusters": d[cluster].nunique()})
    return rows


# ---------------------------------------------------------------------------
def load(repos):
    metrics, fh_c, fh_f = [], [], []
    for r in repos:
        m = pd.read_csv(f"m2_{r}.csv")
        m["repo"] = r
        metrics.append(m)
        c = pd.read_csv(f"fh_{r}_commits.csv", keep_default_na=False)
        c["repo"] = r
        fh_c.append(c)
        f = pd.read_csv(f"fh_{r}_files.csv", keep_default_na=False)
        f["repo"] = r
        fh_f.append(f)
    m = pd.concat(metrics, ignore_index=True)
    c = pd.concat(fh_c, ignore_index=True)
    f = pd.concat(fh_f, ignore_index=True)
    f["prod"] = f["prod"].astype(str).str.lower().eq("true")
    for d in (m, c):
        d["date"] = pd.to_datetime(d["date"], utc=True)
    m["month"] = m["date"].dt.strftime("%Y-%m")
    m["repo_month"] = m["repo"] + "_" + m["month"]
    m["log_size"] = np.log1p(m["added_code"] + m["deleted_code"])
    m["log_prod_files"] = np.log1p(m["prod_files"])
    m["is_pair"] = (m["group"] == "pair").astype(float)
    c["fix_subject"] = c["fix_subject"].astype(str).str.lower().eq("true")
    m = m.merge(c[["sha", "subject", "reverted_by"]], on="sha", how="left")
    m["commit_type"] = m["subject"].map(commit_type)
    m["reverted"] = (m["reverted_by"].fillna("") != "").astype(float)
    # Winsorize heavy-tailed outcomes within repository (as in the earlier run).
    for col in ["cc_delta_modified_mean", "net_cc_per_100_added"]:
        lo = m.groupby("repo")[col].transform(lambda s: s.quantile(0.01))
        hi = m.groupby("repo")[col].transform(lambda s: s.quantile(0.99))
        m[col] = m[col].clip(lo, hi)
    return m, c, f


def to_epoch(series):
    """Seconds since the epoch, independent of the datetime resolution pandas chose."""
    return ((series - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).astype("int64")


def followup_fix(m, c, f):
    """H1 outcome and prior-fix control from file-level history."""
    prod = f[f["prod"]]
    fix_shas = set(c.loc[c.fix_subject, "sha"])
    date_of = dict(zip(c.sha, to_epoch(c.date)))
    fixes_by_path = {}
    for row in prod[prod.sha.isin(fix_shas)].itertuples():
        fixes_by_path.setdefault((row.repo, row.path), []).append((date_of[row.sha], row.sha))
    for k in fixes_by_path:
        fixes_by_path[k].sort()
    paths_of = prod.groupby("sha").apply(lambda g: list(zip(g.repo, g.path))).to_dict()
    primary = (prod.sort_values("added", ascending=False).drop_duplicates("sha")
               .set_index("sha")["path"].to_dict())
    end_of = to_epoch(c.groupby("repo").date.max())
    window = FOLLOWUP_DAYS * 86400
    follow, prior, eligible = [], [], []
    for row in m.itertuples():
        t = date_of.get(row.sha)
        paths = paths_of.get(row.sha, [])
        if t is None or not paths:
            follow.append(np.nan); prior.append(np.nan); eligible.append(False)
            continue
        has_follow, n_prior = False, 0
        for p in paths:
            events = fixes_by_path.get(p, [])
            times = np.array([e[0] for e in events])
            if len(times) == 0:
                continue
            lo, hi = np.searchsorted(times, t, "right"), np.searchsorted(times, t + window, "right")
            if any(events[i][1] != row.sha for i in range(lo, hi)):
                has_follow = True
            n_prior += int(np.searchsorted(times, t, "left") - np.searchsorted(times, t - window, "left"))
        follow.append(float(has_follow))
        prior.append(n_prior)
        eligible.append(t <= end_of[row.repo] - window)
    m = m.copy()
    m["followup_fix"] = follow
    m["log_prior_fix"] = np.log1p(prior)
    m["followup_eligible"] = eligible
    m["primary_file"] = m["sha"].map(primary)
    return m


def ai_active(m):
    ai_months = m[(m.group != "human") & (m.prod_files > 0)].groupby("repo").month.apply(set)
    return m[m.apply(lambda r: r.month in ai_months.get(r.repo, set()), axis=1)]


def eligible_authors(d):
    counts = d[d.group.isin(["human", "pair"])].groupby(["author", "group"]).size().unstack(fill_value=0)
    return counts[(counts.get("pair", 0) >= MIN_EACH) & (counts["human"] >= MIN_EACH)].index.tolist()


# ---------------------------------------------------------------------------
def main(repos):
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    m, c, f = load(repos)
    m = followup_fix(m, c, f)
    prod = m[(m.prod_files > 0) & m.group.isin(["human", "pair"])].copy()
    win = ai_active(prod)
    authors = eligible_authors(win)
    core = win[win.author.isin(authors)].copy()
    print(f"Repos: {repos}")
    print(f"Production commits since 2025-01: {len(prod)}; in AI-active months: {len(win)}; "
          f"eligible developers: {len(authors)}; their commits: {len(core)} "
          f"({int(core.is_pair.sum())} AI-paired)")

    confirmatory = []

    # H1 -------------------------------------------------------------------
    h1 = core[core.followup_eligible]
    rate = h1.groupby("group").followup_fix.mean()
    print(f"\n[H1] follow-up fix within {FOLLOWUP_DAYS} days: human {rate.get('human', np.nan):.3f}, "
          f"pair {rate.get('pair', np.nan):.3f} (n={len(h1)})")
    r = fe_ols(h1, "followup_fix", ["is_pair"], ["log_size", "log_prod_files", "log_prior_fix"],
               ["author", "repo_month"])[0]
    confirmatory.append({"hypothesis": "H1 follow-up fix (30d)", **r})

    # H2 -------------------------------------------------------------------
    tab = pd.crosstab(core.group, core.reverted)
    print(f"\n[H2] reverts:\n{tab.to_string()}")
    if tab.shape == (2, 2):
        odds, fp = fisher_exact(tab.loc[["human", "pair"], [0.0, 1.0]].to_numpy())
        print(f"     Fisher exact: odds ratio {odds:.3f}, p={fp:.4f}")
    r = fe_ols(core, "reverted", ["is_pair"], ["log_size"], ["author", "repo_month"])[0]
    confirmatory.append({"hypothesis": "H2 reverted", **r})

    # H3 -------------------------------------------------------------------
    first = prod[prod.group == "pair"].groupby("author").date.min()
    n_lab = prod[prod.group == "pair"].groupby("author").size()
    pre_counts = prod.assign(first=prod.author.map(first)).query("date < first").groupby("author").size()
    adopters = [a for a in n_lab.index if n_lab[a] >= MIN_EACH and pre_counts.get(a, 0) >= 20]
    totals = prod.groupby("author").size()
    others = [a for a in totals.index if a not in adopters and totals[a] >= 20]
    h3 = prod[prod.author.isin(adopters + others)].copy()
    is_adopter = h3.author.isin(adopters)
    after = h3.date > h3.author.map(first)
    h3["post_unlabelled"] = (is_adopter & after & (h3.group == "human")).astype(float)
    h3["post_labelled"] = (is_adopter & (h3.group == "pair")).astype(float)
    print(f"\n[H3] adopters: {len(adopters)}, non-adopters: {len(others)}, commits: {len(h3)}")
    print(h3[is_adopter].assign(period=np.where(h3[is_adopter].group == "pair", "labelled",
                                                np.where(after[is_adopter], "post-unlabelled",
                                                         "pre"))).groupby("period")[
        ["added_comment_share", "log_size"]].mean().to_string())
    for label, y, controls in [("H3a spillover: comment share", "added_comment_share", ["log_size"]),
                               ("H3b spillover: commit size", "log_size", [])]:
        rows = fe_ols(h3, y, ["post_unlabelled", "post_labelled"], controls, ["author", "repo_month"])
        confirmatory.append({"hypothesis": label, **rows[0]})
        print(f"     {label}: post_labelled effect {rows[1]['effect']:.4f} "
              f"[{rows[1]['ci_low']:.4f}, {rows[1]['ci_high']:.4f}]")

    conf = pd.DataFrame(confirmatory)
    conf["p_BH"] = multipletests(conf["p"], method="fdr_bh")[1]
    print("\n=== CONFIRMATORY (BH across H1, H2, H3a, H3b) ===")
    print(conf.to_string(index=False))
    conf.to_csv("overnight_confirmatory.csv", index=False)

    # H4 -------------------------------------------------------------------
    allmonths = prod[prod.author.isin(authors)].copy()
    claude_only = core[(core.group == "human") | (core.tool == "Claude")]
    variants = {
        "base": (core, [], ["author", "repo_month"]),
        "a_commit_type": (core, [], ["author", "repo_month", "commit_type"]),
        "b_same_file": (core.dropna(subset=["primary_file"]), [],
                        ["author", "repo_month", "primary_file"]),
        "c_claude_only": (claude_only, [], ["author", "repo_month"]),
        "d_since_2025_01": (allmonths, [], ["author", "repo_month"]),
    }
    rows = []
    for col, label in H4_OUTCOMES.items():
        controls = [] if col == "log_size" else ["log_size"]
        for vname, (data, extra, fes) in variants.items():
            r = fe_ols(data, col, ["is_pair"], controls + extra, fes)[0]
            rows.append({"outcome": label, "variant": vname, **r})
    h4 = pd.DataFrame(rows)
    print("\n=== H4 ROBUSTNESS of earlier findings ===")
    print(h4.drop(columns=["term"]).to_string(index=False))
    verdict = h4.groupby("outcome").apply(lambda g: pd.Series({
        "same_sign": (np.sign(g.effect) == np.sign(g.loc[g.variant == "base", "effect"].iloc[0])).all(),
        "ci_excludes_0_all": ((g.ci_low > 0) | (g.ci_high < 0)).all()}))
    print("\nRobust = same sign and CI excludes 0 in every variant:")
    print(verdict.to_string())
    h4.to_csv("overnight_h4.csv", index=False)

    # Sensitivity for H3 noted in the report (exploratory): controls without any labelled commits.
    clean = h3[~(h3.author.isin(others) & h3.author.isin(n_lab.index))]
    rows = fe_ols(clean, "added_comment_share", ["post_unlabelled", "post_labelled"], ["log_size"],
                  ["author", "repo_month"])
    print(f"\n[exploratory] H3a with non-adopters restricted to never-labelled developers: "
          f"post_unlabelled {rows[0]['effect']:.4f} [{rows[0]['ci_low']:.4f}, {rows[0]['ci_high']:.4f}] "
          f"p={rows[0]['p']:.4f}, n={rows[0]['n']}")
    core.to_csv("overnight_core_commits.csv", index=False)


if __name__ == "__main__":
    main(sys.argv[1:])
