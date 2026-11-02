"""Exploratory extension (step 4): mine only the commits the within-developer model uses.

JetBrains/intellij-community has about 60k production commits since 2025-01,
too many to mine overnight. The within-developer comparison only uses the
eligible developers' commits, so this mines
  - every commit by the developers other_repos_check.py marked eligible, and
  - every AI-labelled ("pair") commit by anyone, because those define the
    repository's AI-active months,
with exactly the metric code of mine_commits.py: its pydriller Repository is
wrapped with the `only_commits` filter, nothing else changes.

Usage: python mine_selected.py <repo_path> <repo_name> <out_csv> <since>
"""

import subprocess
import sys

import pandas as pd
from pydriller import Repository

import mine_commits
from mine_commits import classify

START, BODY, END = "\x01", "\x02", "\x03"


def selected_shas(repo_path, repo_name, since):
    authors = pd.read_csv("other_repos_authors.csv")
    eligible = set(authors.loc[(authors.repo == repo_name) & authors.eligible, "author"])
    fmt = f"{START}%H{BODY}%an{BODY}%B{END}"
    out = subprocess.run(["git", "-C", repo_path, "log", "--no-merges", f"--since={since}",
                          f"--pretty=format:{fmt}"],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    shas = []
    for block in out.split(START)[1:]:
        parts = block.partition(END)[0].split(BODY, 2)
        if len(parts) == 3 and (parts[1] in eligible or classify(parts[1], parts[2]) == "pair"):
            shas.append(parts[0])
    print(f"[{repo_name}] eligible developers: {sorted(eligible)}; selected commits: {len(shas)}",
          flush=True)
    return shas


def main(repo_path, repo_name, out_csv, since):
    shas = selected_shas(repo_path, repo_name, since)
    mine_commits.Repository = lambda path, **kw: Repository(path, only_commits=shas, **kw)
    mine_commits.main(repo_path, repo_name, out_csv, since)


if __name__ == "__main__":
    main(*sys.argv[1:])
