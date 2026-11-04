"""
Fast miner for the before/after analysis.

before_after.py mines with PyDriller, which re-parses every modified file of
every commit. On this sample that is days of work: intellij-community alone has
well over 100,000 commits since 2019. This script produces the same monthly
aggregates, in the same cache format, by talking to git directly.

How each metric is obtained
  * Avg Lines/Commit, Bug-Fix Ratio, Del/Add Ratio come from `git log --numstat`
    and are computed over EVERY non-merge commit since 2019. They are exact.
  * Comment Density, Cyclomatic Complexity and Avg Function Length need the
    content of each modified file. For these, up to COMMITS_PER_MONTH commits
    are drawn at random from each month (seeded, so the draw is reproducible),
    and up to FILES_PER_COMMIT modified code files are measured per commit with
    the corrected metrics in metrics.py. Months with fewer commits use all of
    them. Monthly means estimated this way are unbiased but noisier than a
    full census; the noise is the same before and after the LLM cut-off.

Details that keep the numbers comparable with before_after.py
  * non-merge commits on the default branch only, dated by committer date
  * the same bug-fix keyword list
  * rename detection stays on, as in PyDriller: a moved file counts only the
    lines that changed, not its whole content as deleted and re-added
    (checked against PyDriller output for ideavim: identical bug-fix ratios
    and line counts month by month)
  * commits at the boundary of the shallow clone are excluded from the line
    metrics: git cannot diff them against their missing parent and would
    report the whole tree as added

Output: cache_monthly/<repo>.csv, read by before_after.py.

Usage
    python3 mine_fast.py              # resume
    python3 mine_fast.py --workers 2
"""

import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from multiprocessing import Pool

import numpy as np
import pandas as pd

from before_after import BUG_KEYWORDS, CACHE_DIR, SAMPLE_FILE
from metrics import CODE_EXTENSIONS, comment_ratio, complexity, file_extension

SINCE = "2019-01-01"
SHALLOW_SINCE = "2018-12-01"      # one month of margin before the window opens
COMMITS_PER_MONTH = 10
FILES_PER_COMMIT = 15
MAX_BLOB_BYTES = 400_000          # matches metrics.MAX_CHARS
CLONE_TIMEOUT = 3600
SEED = 42

COLUMNS = ["month", "Avg Lines/Commit", "Bug-Fix Ratio", "Del/Add Ratio",
           "Comment Density", "Cyclomatic Complexity", "Avg Function Length"]


def git(args, cwd, **kwargs):
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, **kwargs)


def clone(full_name, target):
    """Bare, single-branch clone holding only history since SHALLOW_SINCE."""
    url = f"https://github.com/{full_name}.git"
    result = subprocess.run(
        ["git", "clone", "--bare", "--single-branch", "--quiet",
         f"--shallow-since={SHALLOW_SINCE}", url, target],
        capture_output=True, timeout=CLONE_TIMEOUT)
    if result.returncode != 0:
        message = result.stderr.decode(errors="replace")
        # a repository with no commits after the cut-off cannot be cloned
        # shallowly at all; that is "no data", not a failure
        if "no commits selected" in message or "error processing shallow info" in message:
            return False
        raise RuntimeError(message.strip()[:300])
    return True


def path_after_change(path):
    """
    Resolve git's rename notation to the new path.

    "src/{old => new}/A.kt" -> "src/new/A.kt"
    "old/A.kt => new/B.kt"  -> "new/B.kt"
    """
    if " => " not in path:
        return path
    if "{" in path and "}" in path:
        prefix, rest = path.split("{", 1)
        inner, suffix = rest.split("}", 1)
        new = inner.split(" => ", 1)[1]
        return (prefix + new + suffix).replace("//", "/")
    return path.split(" => ", 1)[1]


def read_log(repo_dir):
    """Every non-merge commit since SINCE, with its message and numstat."""
    raw = git(["log", "--no-merges", "-M", f"--since={SINCE}",
               "--format=%x1e%H%x1f%cI%x1f%B%x1d", "--numstat", "HEAD"],
              cwd=repo_dir).stdout.decode("utf-8", errors="replace")

    commits = []
    for chunk in raw.split("\x1e")[1:]:
        header, _, stats = chunk.partition("\x1d")
        sha, date, message = header.split("\x1f", 2)
        added = deleted = 0
        paths = []
        for line in stats.strip("\n").split("\n"):
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            a, d, path = parts
            # binary files report "-": PyDriller counts them as zero lines
            added += int(a) if a.isdigit() else 0
            deleted += int(d) if d.isdigit() else 0
            paths.append(path_after_change(path))
        commits.append({"sha": sha, "date": date, "message": message,
                        "added": added, "deleted": deleted, "paths": paths})
    return commits


def shallow_boundary(repo_dir):
    path = os.path.join(repo_dir, "shallow")
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {line.strip() for line in f if line.strip()}


class BlobReader:
    """Reads file contents at a given commit through one `git cat-file --batch`."""

    def __init__(self, repo_dir):
        self.proc = subprocess.Popen(["git", "cat-file", "--batch"], cwd=repo_dir,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, sha, path):
        if "\n" in path:
            return None
        self.proc.stdin.write(f"{sha}:{path}\n".encode())
        self.proc.stdin.flush()
        header = self.proc.stdout.readline().decode(errors="replace").split()
        if len(header) < 3 or header[-1] == "missing":
            return None                      # the file was deleted by this commit
        size = int(header[2])
        data = self.proc.stdout.read(size)
        self.proc.stdout.read(1)             # trailing newline
        if header[1] != "blob" or size > MAX_BLOB_BYTES:
            return None
        return data.decode("utf-8", errors="replace")

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()


def content_metrics(repo_dir, commits, short):
    """Sampled comment density / complexity / function length per month."""
    by_month = defaultdict(list)
    for commit in commits:
        code_paths = [p for p in commit["paths"] if file_extension(p) in CODE_EXTENSIONS]
        if code_paths:
            by_month[commit["date"][:7]].append((commit["sha"], code_paths))

    reader = BlobReader(repo_dir)
    rows = []
    try:
        for month, candidates in sorted(by_month.items()):
            rng = random.Random(f"{SEED}-{short}-{month}")
            chosen = candidates if len(candidates) <= COMMITS_PER_MONTH \
                else rng.sample(candidates, COMMITS_PER_MONTH)
            for sha, paths in chosen:
                picked = paths if len(paths) <= FILES_PER_COMMIT \
                    else rng.sample(paths, FILES_PER_COMMIT)
                for path in picked:
                    source = reader.read(sha, path)
                    if not source:
                        continue
                    density = comment_ratio(source, file_extension(path))
                    cc, length = complexity(source, path)
                    if density is None and cc is None:
                        continue
                    rows.append({"month": month, "comment_density": density,
                                 "cyclomatic": cc, "function_length": length})
    finally:
        reader.close()
    return rows


def mine(repo):
    full_name = repo["name"]
    short = full_name.split("/")[-1]
    out_path = os.path.join(CACHE_DIR, f"{short}.csv")
    if os.path.exists(out_path):
        return short, "cached", 0, 0.0

    started = time.time()
    workdir = tempfile.mkdtemp(prefix="mine_fast_")
    repo_dir = os.path.join(workdir, "repo.git")
    try:
        if not clone(full_name, repo_dir):
            pd.DataFrame(columns=COLUMNS).to_csv(out_path, index=False)
            return short, "no commits since 2019", 0, time.time() - started

        commits = read_log(repo_dir)
        if not commits:
            pd.DataFrame(columns=COLUMNS).to_csv(out_path, index=False)
            return short, "no commits since 2019", 0, time.time() - started

        boundary = shallow_boundary(repo_dir)
        commit_frame = pd.DataFrame([{
            "month": c["date"][:7],
            "lines_changed": np.nan if c["sha"] in boundary else c["added"] + c["deleted"],
            "is_bugfix": 1 if BUG_KEYWORDS.search(c["message"]) else 0,
            "del_add_ratio": np.nan if c["sha"] in boundary or not c["added"]
            else c["deleted"] / c["added"],
        } for c in commits])
        monthly = commit_frame.groupby("month").agg(
            {"lines_changed": "mean", "is_bugfix": "mean", "del_add_ratio": "mean"})
        monthly.columns = ["Avg Lines/Commit", "Bug-Fix Ratio", "Del/Add Ratio"]

        file_rows = content_metrics(repo_dir, commits, short)
        if file_rows:
            files = pd.DataFrame(file_rows).groupby("month").agg(
                {"comment_density": "mean", "cyclomatic": "mean", "function_length": "mean"})
            files.columns = ["Comment Density", "Cyclomatic Complexity", "Avg Function Length"]
            monthly = monthly.join(files, how="outer")
        for column in COLUMNS[1:]:
            if column not in monthly.columns:
                monthly[column] = np.nan

        monthly = monthly.reset_index()[COLUMNS]
        tmp_path = out_path + ".tmp"
        monthly.to_csv(tmp_path, index=False)
        os.replace(tmp_path, out_path)       # never leave a half-written cache file
        return short, "ok", len(commits), time.time() - started
    except Exception as exc:
        return short, f"failed: {type(exc).__name__}: {str(exc)[:200]}", 0, time.time() - started
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(SAMPLE_FILE) as f:
        sample = json.load(f)

    print(f"Mining {len(sample)} repositories with {args.workers} workers", flush=True)
    done = 0
    failed = []
    with Pool(args.workers) as pool:
        for short, status, n_commits, seconds in pool.imap_unordered(mine, sample):
            done += 1
            print(f"[{done}/{len(sample)}] {short}: {status} "
                  f"({n_commits} commits, {seconds:.0f}s)", flush=True)
            if status.startswith("failed"):
                failed.append(short)

    print(f"\nFinished. Failed: {len(failed)} {failed}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
