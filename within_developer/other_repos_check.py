"""Step 4 screen: which other sampled repositories could enter the within-developer design?

Takes every repository in ../llm_signals_summary.csv with at least 20
AI-authored commits (other than the three analysed ones), clones it blobless
into repos/<name>.git (commit and tree objects only), and counts each
developer's AI-co-authored ("pair") and unlabelled ("human") production-code
commits since 2025-01-01 in the repository's AI-active months, using the
classification and production-path rules of mine_commits.py.

A repository qualifies if at least one developer has >= 8 of each.

Writes other_repos_screen.csv (one row per repository) and
other_repos_authors.csv (one row per repository and author).

Usage: python other_repos_check.py
"""

import os
import subprocess
import sys

import pandas as pd

from mine_commits import CODE_EXT, TEST_PATH, classify

SUMMARY = "../llm_signals_summary.csv"
ANALYSED = {"kotlin", "intellij-scala", "ideavim"}
MIN_AI_COMMITS, MIN_EACH, SINCE = 20, 8, "2025-01-01"
START, BODY, END = "\x01", "\x02", "\x03"


def clone(full_name, target):
    if not os.path.isdir(target):
        subprocess.run(["git", "clone", "--quiet", "--bare", "--filter=blob:none",
                        f"https://github.com/{full_name}.git", target], check=True)


def production_commits(repo_dir):
    """One row per non-merge commit since SINCE that touches production code."""
    # --name-only with --no-renames needs tree objects only, so no blobs are fetched.
    fmt = f"{START}%H{BODY}%cI{BODY}%an{BODY}%B{END}"
    out = subprocess.run(["git", "-C", repo_dir, "log", "--no-merges", "--no-renames",
                          f"--since={SINCE}", "--name-only", f"--pretty=format:{fmt}"],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    rows = []
    for block in out.split(START)[1:]:
        header, _, names = block.partition(END)
        parts = header.split(BODY, 3)
        if len(parts) != 4:
            continue
        sha, date, author, message = parts
        group = classify(author, message)
        paths = [p for p in names.strip().splitlines() if p]
        prod = [p for p in paths if p.endswith(CODE_EXT) and not TEST_PATH.search(p)]
        if group is None or not prod:
            continue
        rows.append({"sha": sha, "date": date, "author": author, "group": group})
    d = pd.DataFrame(rows, columns=["sha", "date", "author", "group"])
    d["month"] = pd.to_datetime(d["date"], utc=True).dt.strftime("%Y-%m")
    return d


def main():
    summary = pd.read_csv(SUMMARY)
    candidates = summary[(summary.AuthorshipCommits >= MIN_AI_COMMITS)
                         & ~summary.Repository.isin(ANALYSED)].sort_values(
        "AuthorshipCommits", ascending=False)
    print(f"Sampled repositories with >= {MIN_AI_COMMITS} AI-authored commits "
          f"(excluding {sorted(ANALYSED)}): {len(candidates)}")
    print(candidates[["FullName", "CommitsSince2021", "AuthorshipCommits"]].to_string(index=False))
    os.makedirs("repos", exist_ok=True)
    screen, per_author = [], []
    for row in candidates.itertuples():
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
        print(f"    production commits since {SINCE}: {len(d)} "
              f"({int((d.group == 'pair').sum())} pair); AI-active months: {len(ai_months)}; "
              f"eligible developers: {len(eligible)}", flush=True)
        if len(eligible):
            print(eligible.to_string())
        screen.append({"repo": row.Repository, "status": "ok", "prod_commits": len(d),
                       "pair_prod_commits": int((d.group == "pair").sum()),
                       "ai_active_months": len(ai_months),
                       "first_ai_month": min(ai_months) if ai_months else "",
                       "eligible_developers": len(eligible),
                       "eligible_commits": int(eligible.values.sum())})
        for author, c in counts.iterrows():
            per_author.append({"repo": row.Repository, "author": author, "human": int(c.human),
                               "pair": int(c.pair), "eligible": author in eligible.index})
    pd.DataFrame(screen).to_csv("other_repos_screen.csv", index=False)
    pd.DataFrame(per_author).to_csv("other_repos_authors.csv", index=False)
    print("\nSaved other_repos_screen.csv, other_repos_authors.csv")


if __name__ == "__main__":
    sys.exit(main())
