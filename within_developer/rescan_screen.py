"""Exploratory: screen repositories that newly reach >= 20 AI-authored commits under the fuller patterns.

Reads results_exploratory/llm_signals_full_patterns_summary.csv (signal_rescan.py)
and compares it with the original summary (../llm_signals_summary.csv). Every
repository at >= 20 under the fuller patterns that was not already screened
(the three analysed ones, intellij-community, sbt-ide-settings,
kotlin-web-site) is screened for eligible developers exactly as in
other_repos_check.py (>= 8 pair and >= 8 unlabelled production commits since
2025-01-01 in AI-active months).

Writes results_exploratory/rescan_screen.csv and rescan_authors.csv.
Usage: python rescan_screen.py
"""

import os
import subprocess

import pandas as pd

from other_repos_check import MIN_AI_COMMITS, MIN_EACH, clone, production_commits

FULL = "results_exploratory/llm_signals_full_patterns_summary.csv"
ORIGINAL = "../llm_signals_summary.csv"
SCREENED = {"kotlin", "intellij-scala", "ideavim", "intellij-community", "sbt-ide-settings",
            "kotlin-web-site"}


def main():
    pd.set_option("display.width", 200)
    full = pd.read_csv(FULL)
    orig = pd.read_csv(ORIGINAL)[["Repository", "AuthorshipCommits"]]
    m = full.merge(orig, on="Repository", suffixes=("", "_original"))
    changed = m[m.AuthorshipCommits != m.AuthorshipCommits_original]
    print(f"Repositories whose AI-authored count changes with the fuller patterns: {len(changed)}")
    print(changed[["FullName", "AuthorshipCommits_original", "AuthorshipCommits"]]
          .sort_values("AuthorshipCommits", ascending=False).to_string(index=False))
    qualifying = m[m.AuthorshipCommits >= MIN_AI_COMMITS]
    new = qualifying[~qualifying.Repository.isin(SCREENED)]
    print(f"\n>= {MIN_AI_COMMITS} AI-authored commits under the fuller patterns: {len(qualifying)}; "
          f"not screened before: {len(new)}")
    os.makedirs("repos", exist_ok=True)
    screen, per_author = [], []
    for row in new.itertuples():
        target = f"repos/{row.Repository}.git"
        print(f"\n[{row.FullName}] cloning blobless", flush=True)
        try:
            clone(row.FullName, target)
            d = production_commits(target)
        except subprocess.CalledProcessError as exc:
            print(f"    failed: {exc}", flush=True)
            screen.append({"repo": row.Repository, "status": "failed"})
            continue
        d = d[d.group.isin(["human", "pair"])]
        ai_months = set(d.loc[d.group == "pair", "month"])
        win = d[d.month.isin(ai_months)]
        counts = win.groupby(["author", "group"]).size().unstack(fill_value=0)
        for col in ["human", "pair"]:
            if col not in counts:
                counts[col] = 0
        eligible = counts[(counts.pair >= MIN_EACH) & (counts.human >= MIN_EACH)]
        print(f"    production commits since 2025-01-01: {len(d)} "
              f"({int((d.group == 'pair').sum())} pair); AI-active months: {len(ai_months)}; "
              f"eligible developers: {len(eligible)}", flush=True)
        if len(eligible):
            print(eligible.to_string())
        screen.append({"repo": row.Repository, "status": "ok",
                       "ai_authored_original": row.AuthorshipCommits_original,
                       "ai_authored_full": row.AuthorshipCommits, "prod_commits": len(d),
                       "pair_prod_commits": int((d.group == "pair").sum()),
                       "ai_active_months": len(ai_months), "eligible_developers": len(eligible),
                       "eligible_commits": int(eligible.values.sum())})
        for author, c in counts.iterrows():
            per_author.append({"repo": row.Repository, "author": author, "human": int(c.human),
                               "pair": int(c.pair), "eligible": author in eligible.index})
    pd.DataFrame(screen).to_csv("results_exploratory/rescan_screen.csv", index=False)
    pd.DataFrame(per_author).to_csv("results_exploratory/rescan_authors.csv", index=False)
    print("\nSaved results_exploratory/rescan_screen.csv, rescan_authors.csv")


if __name__ == "__main__":
    main()
