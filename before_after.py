"""
Before/after comparison of maintainability proxies around LLM adoption.

Replaces the earlier before_after_table.py, which had drifted: it carried five
dead copies of the repository dictionary, still listed the previous 97-repository
keyword sample rather than the 199-repository random sample, and reported
uncorrected p-values across roughly a thousand tests.

What this version does differently
  * reads the repository list from sampled_repos.json, so the script and the
    sampling record cannot disagree
  * uses metrics.py, which measures comment density and complexity across every
    language in the sample instead of Python only
  * requires a minimum number of monthly observations in each period before a
    repository/metric pair is tested at all
  * applies Benjamini-Hochberg FDR correction across every test performed
  * reports the share of the whole sample, not only of the significant subset
  * caches each repository's monthly aggregates, so an interrupted run resumes

Usage
    python3 before_after.py              # resume, or start fresh
    python3 before_after.py --fresh      # ignore the cache and re-mine
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

import numpy as np
import pandas as pd
from pydriller import Repository
from scipy import stats
from statsmodels.stats.multitest import multipletests

from metrics import comment_ratio, complexity, file_extension

SAMPLE_FILE = "sampled_repos.json"
CACHE_DIR = "cache_monthly"
OUTPUT = "before_after_table.csv"

HISTORY_START = datetime(2019, 1, 1)
PRE_END = datetime(2021, 6, 1)      # GitHub Copilot technical preview
POST_START = datetime(2023, 1, 1)   # first full month after ChatGPT's release

# A repository/metric pair needs this many monthly observations on each side
# before a comparison is meaningful. Below it, a "significant" result is noise.
MIN_MONTHS_PER_PERIOD = 6

ALPHA = 0.05

BUG_KEYWORDS = re.compile(
    r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)

METRICS = [
    "Comment Density",
    "Avg Lines/Commit",
    "Bug-Fix Ratio",
    "Cyclomatic Complexity",
    "Avg Function Length",
    "Del/Add Ratio",
]

# Direction that counts as degradation, for the three maintainability proxies.
# The other three metrics describe how code is produced, not how healthy it is,
# so they are reported but not scored for or against the hypothesis.
DEGRADES_WHEN_UP = {"Bug-Fix Ratio", "Cyclomatic Complexity", "Avg Function Length"}


def mine_repository(full_name):
    """Return monthly aggregates for one repository as a DataFrame."""
    url = f"https://github.com/{full_name}"
    file_rows = []
    commit_rows = []

    for commit in Repository(url, since=HISTORY_START, only_no_merge=True).traverse_commits():
        added = deleted = 0
        for modified in commit.modified_files:
            added += modified.added_lines
            deleted += modified.deleted_lines

            extension = file_extension(modified.filename)
            source = modified.source_code
            if not source:
                continue

            density = comment_ratio(source, extension)
            cc, length = complexity(source, modified.filename)
            if density is None and cc is None:
                continue
            file_rows.append({
                "date": commit.committer_date,
                "comment_density": density,
                "cyclomatic": cc,
                "function_length": length,
            })

        commit_rows.append({
            "date": commit.committer_date,
            "is_bugfix": 1 if BUG_KEYWORDS.search(commit.msg or "") else 0,
            "lines_changed": added + deleted,
            "del_add_ratio": (deleted / added) if added else np.nan,
        })

    if not commit_rows:
        return pd.DataFrame()

    def monthly(rows, aggregation):
        frame = pd.DataFrame(rows)
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame["month"] = frame["date"].dt.tz_localize(None).dt.to_period("M")
        return frame.groupby("month").agg(aggregation)

    commits = monthly(commit_rows, {
        "lines_changed": "mean", "is_bugfix": "mean", "del_add_ratio": "mean"})
    commits.columns = ["Avg Lines/Commit", "Bug-Fix Ratio", "Del/Add Ratio"]

    if file_rows:
        files = monthly(file_rows, {
            "comment_density": "mean", "cyclomatic": "mean", "function_length": "mean"})
        files.columns = ["Comment Density", "Cyclomatic Complexity", "Avg Function Length"]
        merged = commits.join(files, how="outer")
    else:
        merged = commits
        for column in ["Comment Density", "Cyclomatic Complexity", "Avg Function Length"]:
            merged[column] = np.nan

    return merged.reset_index()


def load_monthly(full_name, short, use_cache=True):
    """Mine a repository, or read its cached monthly aggregates."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{short}.csv")

    if use_cache and os.path.exists(path):
        frame = pd.read_csv(path)
        if frame.empty:
            return frame
        frame["month"] = pd.PeriodIndex(frame["month"], freq="M")
        return frame

    frame = mine_repository(full_name)
    frame.to_csv(path, index=False)
    return frame


def cohens_d(pre, post):
    """Pooled-standard-deviation effect size; None when it is undefined."""
    n1, n2 = len(pre), len(post)
    if n1 < 2 or n2 < 2:
        return None
    pooled_var = ((n1 - 1) * np.var(pre, ddof=1) + (n2 - 1) * np.var(post, ddof=1)) / (n1 + n2 - 2)
    if pooled_var <= 0:
        return None
    return (np.mean(post) - np.mean(pre)) / np.sqrt(pooled_var)


def effect_label(d):
    if d is None:
        return ""
    magnitude = abs(d)
    if magnitude < 0.2:
        return "negligible"
    if magnitude < 0.5:
        return "small"
    if magnitude < 0.8:
        return "medium"
    return "large"


def compare(frame, repo_short, language):
    """Run the before/after test for every metric of one repository."""
    rows = []
    pre_mask = frame["month"] < pd.Period(PRE_END, freq="M")
    post_mask = frame["month"] >= pd.Period(POST_START, freq="M")

    for metric in METRICS:
        if metric not in frame.columns:
            continue
        pre = frame.loc[pre_mask, metric].dropna().to_numpy()
        post = frame.loc[post_mask, metric].dropna().to_numpy()

        row = {
            "Language": language,
            "Repository": repo_short,
            "Metric": metric,
            "N months pre": len(pre),
            "N months post": len(post),
            "Pre-LLM Mean": round(float(np.mean(pre)), 4) if len(pre) else None,
            "Post-LLM Mean": round(float(np.mean(post)), 4) if len(post) else None,
            "Abs Change": None,
            "Change %": None,
            "p-value": None,
            "Cohen d": None,
            "Effect Size": "",
            "Tested": "no",
        }

        if len(pre) >= MIN_MONTHS_PER_PERIOD and len(post) >= MIN_MONTHS_PER_PERIOD:
            row["Tested"] = "yes"
            pre_mean, post_mean = float(np.mean(pre)), float(np.mean(post))
            row["Abs Change"] = round(post_mean - pre_mean, 4)
            # A percentage change computed against a near-zero baseline is an
            # artefact of the baseline, not a finding: a comment density moving
            # from 0.0002 to 0.10 is "+53696%". Report it only when the
            # baseline is large enough for the ratio to mean something.
            if abs(pre_mean) > 0.05 * abs(post_mean) and pre_mean != 0:
                row["Change %"] = round((post_mean - pre_mean) / abs(pre_mean) * 100, 1)
            try:
                _, p = stats.mannwhitneyu(pre, post, alternative="two-sided")
                row["p-value"] = float(p)
            except ValueError:
                row["p-value"] = None
            d = cohens_d(pre, post)
            if d is not None:
                row["Cohen d"] = round(float(d), 3)
                row["Effect Size"] = effect_label(d)

        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true", help="ignore the cache and re-mine")
    args = parser.parse_args()

    with open(SAMPLE_FILE) as f:
        sample = json.load(f)

    all_rows = []
    for index, repo in enumerate(sample, start=1):
        full_name = repo["name"]
        short = full_name.split("/")[-1]
        language = repo.get("language") or "Unknown"
        print(f"[{index}/{len(sample)}] {full_name}", flush=True)

        try:
            frame = load_monthly(full_name, short, use_cache=not args.fresh)
        except Exception as exc:
            print(f"    skipped: {type(exc).__name__}: {exc}", flush=True)
            continue

        if frame.empty:
            print("    no commits in window", flush=True)
            continue

        all_rows.extend(compare(frame, short, language))

    df = pd.DataFrame(all_rows)
    if df.empty:
        print("No results produced.")
        return

    # Benjamini-Hochberg across every test that actually ran.
    testable = df["p-value"].notna()
    df["p_adj_BH"] = np.nan
    df["Significant_FDR"] = ""
    if testable.any():
        reject, p_adj, _, _ = multipletests(
            df.loc[testable, "p-value"], alpha=ALPHA, method="fdr_bh")
        df.loc[testable, "p_adj_BH"] = p_adj
        df.loc[testable, "Significant_FDR"] = np.where(reject, "yes", "")

    df = df.sort_values(["Language", "Repository", "Metric"])
    df.to_csv(OUTPUT, index=False)

    report(df)
    print(f"\nSaved: {OUTPUT}")


def report(df):
    n_repos = df["Repository"].nunique()
    n_tests = int(df["p-value"].notna().sum())
    n_raw = int((df["p-value"] < ALPHA).sum())
    n_fdr = int((df["Significant_FDR"] == "yes").sum())

    print()
    print("=== TESTS ===")
    print(f"Repositories analysed            : {n_repos}")
    print(f"Repository/metric pairs tested   : {n_tests}")
    print(f"  (pairs skipped for having fewer than "
          f"{MIN_MONTHS_PER_PERIOD} months on either side: "
          f"{int((df['Tested'] == 'no').sum())})")
    print(f"Expected false positives at p<{ALPHA}: ~{ALPHA * n_tests:.0f}")
    print(f"Significant, uncorrected         : {n_raw}")
    print(f"Significant, BH-corrected        : {n_fdr}")

    sub = df[df["Metric"].isin(DEGRADES_WHEN_UP) & (df["Significant_FDR"] == "yes")]
    degraded, improved = set(), set()
    for repo, rows in sub.groupby("Repository"):
        up = int((rows["Abs Change"] > 0).sum())
        down = int((rows["Abs Change"] < 0).sum())
        if up or down:
            (degraded if up >= down else improved).add(repo)

    print()
    print("=== HYPOTHESIS: LLM adoption degrades maintainability ===")
    print(f"Repositories with a significant maintainability change: "
          f"{len(degraded) + len(improved)} / {n_repos}")
    print(f"  direction consistent with degradation : {len(degraded)}")
    print(f"  direction consistent with improvement : {len(improved)}")
    if n_repos:
        print(f"Share of the FULL sample showing degradation: "
              f"{len(degraded) / n_repos * 100:.1f}% ({len(degraded)}/{n_repos})")
    print()
    print("Reading: a date-based before/after design cannot attribute these")
    print("changes to LLM adoption. See llm_signal_mining.py for the share of")
    print("commits that actually name an assistant, and README.md for the")
    print("confounders this design does not control.")


if __name__ == "__main__":
    sys.exit(main())
