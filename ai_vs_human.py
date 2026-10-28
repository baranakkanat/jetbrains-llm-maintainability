"""
Within-repository comparison of AI-assisted and human-authored commits.

The before/after design has a confound it cannot remove: everything else that
changed after 2022 — team turnover, project maturity, release cadence, the
projects that simply died — moves the same metrics as LLM adoption does.

Some repositories label the difference directly. A commit carrying a trailer
such as

    Co-authored-by: GitHub Copilot <...>
    Co-authored-by: <AI assistant> <...>

states that an assistant participated. Comparing those commits against the
unlabelled commits of the same repository, over the same months, holds team,
codebase and period fixed and leaves assistance as the thing that varies.

This is still observational: developers choose which work to hand to an
assistant, so the comparison measures the code that is produced with
assistance, not the effect of assistance on arbitrary code.

Input : llm_signals_summary.csv (produced by llm_signal_mining.py)
Output: ai_vs_human_commits.csv, ai_vs_human_tests.csv
"""

import json
import os
import re

import numpy as np
import pandas as pd
from pydriller import Repository
from scipy import stats
from statsmodels.stats.multitest import multipletests

from metrics import comment_ratio, complexity, file_extension

SUMMARY_IN = "llm_signals_summary.csv"
DETAIL_IN = "llm_signals.csv"
SAMPLE_FILE = "sampled_repos.json"
COMMITS_OUT = "ai_vs_human_commits.csv"
TESTS_OUT = "ai_vs_human_tests.csv"
CACHE_DIR = "cache_ai_vs_human"

# Only repositories with at least this many labelled commits are worth testing.
MIN_AI_COMMITS = 20
MIN_HUMAN_COMMITS = 20
ALPHA = 0.05

# Authorship evidence: the commit says an assistant took part in writing it.
# A commit that merely mentions Copilot or OpenAI is talking about AI, not
# written with it, and must not be counted here.
AUTHORSHIP = re.compile(
    r"co-?authored-by:[^\n]*(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|"
    r"openai|anthropic|ai-assistant)"
    r"|generated\s+with\s+\[?(claude|copilot|chatgpt|cursor)"
    r"|assisted-by:[^\n]*(copilot|claude|chatgpt)",
    re.IGNORECASE,
)

BUG_KEYWORDS = re.compile(
    r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)

METRICS = [
    "Lines Changed",
    "Files Touched",
    "Comment Density",
    "Cyclomatic Complexity",
    "Avg Function Length",
    "Del/Add Ratio",
    "Is Bug-Fix",
]

DEGRADES_WHEN_UP = {"Cyclomatic Complexity", "Avg Function Length", "Is Bug-Fix"}


def collect_commits(full_name, short, since=None):
    """
    Per-commit metrics for one repository, cached on disk.

    `since` bounds the mining to the period in which labelled commits exist.
    The comparison only ever uses those months, so mining a decade of earlier
    history would cost hours and contribute nothing — for intellij-community
    it is the difference between 263,000 commits and a few thousand.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{short}.csv")
    if os.path.exists(path):
        return pd.read_csv(path)

    rows = []
    url = f"https://github.com/{full_name}"
    for commit in Repository(url, since=since, only_no_merge=True).traverse_commits():
        message = commit.msg or ""
        added = deleted = files = 0
        densities, complexities, lengths = [], [], []

        try:
            modified_files = list(commit.modified_files)
        except Exception:
            # A single malformed diff should not discard the whole repository.
            modified_files = []

        for modified in modified_files:
            files += 1
            added += modified.added_lines
            deleted += modified.deleted_lines
            try:
                source = modified.source_code
            except Exception:
                source = None
            if not source:
                continue
            extension = file_extension(modified.filename)
            density = comment_ratio(source, extension)
            cc, length = complexity(source, modified.filename)
            if density is not None:
                densities.append(density)
            if cc is not None:
                complexities.append(cc)
            if length is not None:
                lengths.append(length)

        rows.append({
            "Repository": short,
            "Commit": commit.hash,
            "Date": commit.committer_date.isoformat(),
            "AI": 1 if AUTHORSHIP.search(message) else 0,
            "Lines Changed": added + deleted,
            "Files Touched": files,
            "Comment Density": np.mean(densities) if densities else np.nan,
            "Cyclomatic Complexity": np.mean(complexities) if complexities else np.nan,
            "Avg Function Length": np.mean(lengths) if lengths else np.nan,
            "Del/Add Ratio": (deleted / added) if added else np.nan,
            "Is Bug-Fix": 1 if BUG_KEYWORDS.search(message) else 0,
        })

    frame = pd.DataFrame(rows)
    frame.to_csv(path, index=False)
    return frame


def overlapping_window(frame):
    """
    Restrict to the months in which both labelled and unlabelled commits exist.

    Without this the comparison would silently become a before/after test
    again, since assistant trailers only appear in recent months.
    """
    frame = frame.copy()
    frame["month"] = pd.to_datetime(frame["Date"], utc=True, format="mixed").dt.to_period("M")
    ai_months = set(frame.loc[frame["AI"] == 1, "month"])
    if not ai_months:
        return frame.iloc[0:0]
    return frame[frame["month"].isin(ai_months)]


def cohens_d(a, b):
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    pooled = ((n1 - 1) * np.var(a, ddof=1) + (n2 - 1) * np.var(b, ddof=1)) / (n1 + n2 - 2)
    if pooled <= 0:
        return None
    return (np.mean(b) - np.mean(a)) / np.sqrt(pooled)


def effect_label(d):
    if d is None:
        return ""
    m = abs(d)
    return "negligible" if m < 0.2 else "small" if m < 0.5 else "medium" if m < 0.8 else "large"


def main():
    if not os.path.exists(SUMMARY_IN):
        raise SystemExit(f"{SUMMARY_IN} not found. Run llm_signal_mining.py first.")

    summary = pd.read_csv(SUMMARY_IN)
    candidates = summary[summary["AuthorshipCommits"] >= MIN_AI_COMMITS]
    print(f"Repositories with >= {MIN_AI_COMMITS} AI-authored commits: {len(candidates)}")

    # Earliest labelled commit per repository bounds how far back to mine.
    first_labelled = {}
    if os.path.exists(DETAIL_IN):
        detail = pd.read_csv(DETAIL_IN)
        detail = detail[detail["Tier"] == "authorship"]
        detail["Date"] = pd.to_datetime(detail["Date"], utc=True, format="mixed")
        for repo, when in detail.groupby("Repository")["Date"].min().items():
            # a month of margin, so the unlabelled comparison group is not
            # truncated at exactly the first labelled commit
            first_labelled[repo] = (when - pd.Timedelta(days=31)).tz_localize(None).to_pydatetime()

    all_commits = []
    for index, row in enumerate(candidates.itertuples(), start=1):
        since = first_labelled.get(row.Repository)
        print(f"[{index}/{len(candidates)}] {row.FullName} "
              f"(since {since.date() if since else 'start'})", flush=True)
        try:
            all_commits.append(collect_commits(row.FullName, row.Repository, since=since))
        except Exception as exc:
            print(f"    skipped: {type(exc).__name__}: {exc}", flush=True)

    if not all_commits:
        raise SystemExit("No repositories could be processed.")

    commits = pd.concat(all_commits, ignore_index=True)
    commits.to_csv(COMMITS_OUT, index=False)

    results = []
    for repo, frame in commits.groupby("Repository"):
        window = overlapping_window(frame)
        ai = window[window["AI"] == 1]
        human = window[window["AI"] == 0]
        if len(ai) < MIN_AI_COMMITS or len(human) < MIN_HUMAN_COMMITS:
            continue

        for metric in METRICS:
            a = human[metric].dropna().to_numpy()
            b = ai[metric].dropna().to_numpy()
            if len(a) < 10 or len(b) < 10:
                continue
            try:
                _, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            except ValueError:
                continue
            d = cohens_d(a, b)
            results.append({
                "Repository": repo,
                "Metric": metric,
                "N human": len(a),
                "N AI": len(b),
                "Human Mean": round(float(np.mean(a)), 4),
                "AI Mean": round(float(np.mean(b)), 4),
                "Abs Change": round(float(np.mean(b) - np.mean(a)), 4),
                "p-value": float(p),
                "Cohen d": round(float(d), 3) if d is not None else None,
                "Effect Size": effect_label(d),
            })

    tests = pd.DataFrame(results)
    if tests.empty:
        raise SystemExit(
            "No repository had enough labelled and unlabelled commits in overlapping months.")

    reject, p_adj, _, _ = multipletests(tests["p-value"], alpha=ALPHA, method="fdr_bh")
    tests["p_adj_BH"] = p_adj
    tests["Significant_FDR"] = np.where(reject, "yes", "")
    tests = tests.sort_values(["Repository", "Metric"])
    tests.to_csv(TESTS_OUT, index=False)

    print()
    print("=== AI-ASSISTED vs HUMAN COMMITS (same repository, same months) ===")
    print(f"Repositories tested : {tests['Repository'].nunique()}")
    print(f"Tests               : {len(tests)}")
    print(f"Significant (BH)    : {int((tests['Significant_FDR'] == 'yes').sum())}")
    print()
    significant = tests[tests["Significant_FDR"] == "yes"]
    for metric in METRICS:
        rows = significant[significant["Metric"] == metric]
        if rows.empty:
            continue
        higher = int((rows["Abs Change"] > 0).sum())
        lower = int((rows["Abs Change"] < 0).sum())
        direction = "higher in AI commits" if higher >= lower else "lower in AI commits"
        print(f"  {metric}: {len(rows)} significant, mostly {direction} "
              f"({higher} higher / {lower} lower)")
    print()
    print(f"Saved: {COMMITS_OUT}, {TESTS_OUT}")


if __name__ == "__main__":
    main()
