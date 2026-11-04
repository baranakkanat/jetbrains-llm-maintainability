"""
AI-co-authored commits on each sampled repository's default branch.

ai_authorship.png used to count every ref with llm_signal_mining.py's patterns.
This counts the history the within-developer analysis uses instead, so the
numbers match within_developer/REPORT.md and can be reproduced:

  - non-merge commits on the default branch (HEAD of a fresh clone),
  - from 2021-01-01 up to 2026-11-02 05:00 CET, when the analysis clones were
    taken,
  - classified with the rules of within_developer/mine_commits.py:
      pair  : authored by a person, with a Co-authored-by / Generated with /
              Assisted-by trailer naming an AI assistant (the analysis'
              AI-co-authored group);
      agent : authored by an AI agent account such as claude[bot] or
              jetbrains-junie[bot], whatever the message says.
    Other bot accounts are dropped.

Clones in within_developer/repos/ are reused where they exist (the analysis
clones of ideavim, intellij-scala and kotlin are shallow from 2024-12-01; in
the full-history clones the first AI-co-authored commit is from July 2025 and
the first agent commit from March 2025). Every other repository is cloned
blobless into a temporary directory and removed afterwards.

Output: ai_authorship_commits.csv  (one row per pair or agent commit, with its group)
        ai_authorship_repos.csv    (one row per repository: clone used, counts)
"""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import date

sys.path.insert(0, "within_developer")
from mine_commits import classify  # noqa: E402

SAMPLE_FILE = "sampled_repos.json"
LOCAL_CLONES = "within_developer/repos"
SINCE = "2021-01-01T00:00:00Z"
UNTIL = "2026-11-02T04:00:00Z"  # 05:00 CET, when the analysis clones were taken
COMMITS_OUT = "ai_authorship_commits.csv"
REPOS_OUT = "ai_authorship_repos.csv"
CLONE_TIMEOUT = 900
START, BODY, END = "\x01", "\x02", "\x03"


def git(*args, timeout=600):
    return subprocess.run(["git", *args], capture_output=True, text=True, errors="replace",
                          check=True, timeout=timeout).stdout


def local_clones():
    """Map 'Owner/name' to a local clone, preferring full history over shallow clones."""
    found = {}
    if not os.path.isdir(LOCAL_CLONES):
        return found
    for entry in sorted(os.listdir(LOCAL_CLONES)):
        path = os.path.join(LOCAL_CLONES, entry)
        try:
            url = git("-C", path, "config", "remote.origin.url").strip()
        except subprocess.CalledProcessError:
            continue
        name = url.removeprefix("https://github.com/").removesuffix(".git")
        shallow = git("-C", path, "rev-parse", "--is-shallow-repository").strip() == "true"
        if name not in found or (found[name][1] and not shallow):
            found[name] = (path, shallow)
    return found


def labelled_commits(repo_dir):
    fmt = f"{START}%H{BODY}%cI{BODY}%an{BODY}%B{END}"
    out = git("-C", repo_dir, "log", "HEAD", "--no-merges", f"--since={SINCE}",
              f"--until={UNTIL}", f"--pretty=format:{fmt}")
    total, rows = 0, []
    for block in out.split(START)[1:]:
        parts = block.partition(END)[0].split(BODY, 3)
        if len(parts) != 4:
            continue
        total += 1
        sha, date, author, message = parts
        group = classify(author, message)
        if group in ("pair", "agent"):
            rows.append({"Group": group, "Commit": sha, "Date": date, "Author": author})
    return total, rows


def main():
    with open(SAMPLE_FILE) as f:
        sample = json.load(f)
    local = local_clones()
    workdir = tempfile.mkdtemp(prefix="ai_authorship_")
    commit_rows, repo_rows = [], []
    for index, repo in enumerate(sample, start=1):
        full_name = repo["name"]
        short = full_name.split("/")[-1]
        if full_name in local:
            path, shallow = local[full_name]
            source = f"local clone ({'shallow' if shallow else 'full'}): {path}"
            temporary = False
        else:
            path = os.path.join(workdir, short + ".git")
            source = f"blobless clone, {date.today().isoformat()}"
            temporary = True
            try:
                git("clone", "--filter=blob:none", "--bare", "--quiet",
                    f"https://github.com/{full_name}.git", path, timeout=CLONE_TIMEOUT)
            except Exception as exc:
                print(f"[{index}/{len(sample)}] {full_name}: clone failed ({type(exc).__name__})",
                      flush=True)
                repo_rows.append({"Repository": short, "FullName": full_name,
                                  "Status": "clone_failed", "Source": "", "Commits": 0,
                                  "AICoauthored": 0, "AgentCommits": 0})
                continue
        try:
            total, rows = labelled_commits(path)
            status = "ok"
        except Exception as exc:
            total, rows, status = 0, [], f"log_failed:{type(exc).__name__}"
        for r in rows:
            commit_rows.append({"Repository": short, "FullName": full_name, **r})
        pair = sum(r["Group"] == "pair" for r in rows)
        agent = len(rows) - pair
        repo_rows.append({"Repository": short, "FullName": full_name, "Status": status,
                          "Source": source, "Commits": total, "AICoauthored": pair,
                          "AgentCommits": agent})
        if rows or status != "ok":
            print(f"[{index}/{len(sample)}] {full_name}: {pair} AI-co-authored, {agent} agent, "
                  f"of {total} ({status}; {source})", flush=True)
        if temporary:
            shutil.rmtree(path, ignore_errors=True)
    shutil.rmtree(workdir, ignore_errors=True)

    with open(COMMITS_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Repository", "FullName", "Group", "Commit", "Date",
                                               "Author"])
        writer.writeheader()
        writer.writerows(commit_rows)
    with open(REPOS_OUT, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Repository", "FullName", "Status", "Source",
                                               "Commits", "AICoauthored", "AgentCommits"])
        writer.writeheader()
        writer.writerows(repo_rows)
    pair = sum(r["AICoauthored"] for r in repo_rows)
    agent = sum(r["AgentCommits"] for r in repo_rows)
    with_any = sum(1 for r in repo_rows if r["AICoauthored"] or r["AgentCommits"])
    print(f"\n{pair} AI-co-authored and {agent} agent commits in {with_any} of {len(repo_rows)} "
          f"repositories; statuses: "
          f"{ {s: sum(r['Status'] == s for r in repo_rows) for s in {r['Status'] for r in repo_rows}} }")
    print(f"Saved: {COMMITS_OUT}, {REPOS_OUT}")


if __name__ == "__main__":
    main()
