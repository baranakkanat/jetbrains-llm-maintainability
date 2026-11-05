"""Defect found after the main run: the other-bot rule matches "robot" inside surnames.

mine_commits.py drops every author whose name matches OTHER_BOT, which includes
the substring "robot". For each author the rule matched in the main run, this
counts their commits, production commits and AI-co-authored commits in the
repository's AI-active months, and whether they would have been an eligible
developer (>= 8 AI-co-authored and >= 8 unlabelled production commits).

The agent rule is that of the main run (mine_commits.py as of commit 24d7497,
before jetbrains-junie[bot] was recognised as an agent); OTHER_BOT and
AI_TRAILER are unchanged since. Reads fh_<repo>_commits.csv, fh_<repo>_files.csv
and m2_<repo>.csv, and the clones in repos/ for the commit messages.

Usage: python bot_filter_check.py > bot_filter_check.txt
"""

import re
import subprocess

import pandas as pd

from mine_commits import AI_TRAILER, OTHER_BOT

AGENT_AS_RUN = re.compile(r"^(claude|copilot|codex|cursor|junie)(\[bot\]|-bot|\b)", re.I)
REPOS = ["ideavim", "intellij-scala", "kotlin", "intellij-community"]
MIN_EACH = 8


def messages(repo, shas):
    out = subprocess.run(["git", "-C", f"repos/{repo}", "log", "--no-walk=unsorted", "--stdin",
                          "--format=%x1e%H%x1f%B"], input="\n".join(shas) + "\n",
                         capture_output=True, text=True, errors="replace", check=True).stdout
    return dict(record.split("\x1f", 1) for record in out.split("\x1e")[1:])


def main():
    pd.set_option("display.width", 200)
    rows = []
    for repo in REPOS:
        commits = pd.read_csv(f"fh_{repo}_commits.csv", dtype=str, keep_default_na=False)
        files = pd.read_csv(f"fh_{repo}_files.csv", dtype=str, keep_default_na=False)
        production = set(files.loc[files["prod"] == "True", "sha"])
        m2 = pd.read_csv(f"m2_{repo}.csv")
        m2["month"] = pd.to_datetime(m2["date"], utc=True).dt.strftime("%Y-%m")
        ai_months = set(m2.loc[(m2.group == "pair") & (m2.prod_files > 0), "month"])
        matched = [a for a in commits.author.unique()
                   if not AGENT_AS_RUN.search(a) and OTHER_BOT.search(a)]
        for author in matched:
            mine = commits[commits.author == author].copy()
            text = messages(repo, mine.sha.tolist())
            mine["is_pair"] = mine.sha.map(lambda s: bool(AI_TRAILER.search(text.get(s, ""))))
            mine["is_prod"] = mine.sha.isin(production)
            mine["month"] = pd.to_datetime(mine["date"], utc=True).dt.strftime("%Y-%m")
            window = mine[mine.is_prod & mine.month.isin(ai_months)]
            pair, human = int(window.is_pair.sum()), int((~window.is_pair).sum())
            rows.append({"repo": repo, "author": author, "rule match": OTHER_BOT.search(author).group(0),
                         "commits": len(mine), "production": int(mine.is_prod.sum()),
                         "AI-co-authored": int(mine.is_pair.sum()),
                         "AI-active prod: AI-co-authored": pair, "AI-active prod: unlabelled": human,
                         "eligible": pair >= MIN_EACH and human >= MIN_EACH})
    print("Authors dropped by the other-bot rule in the main run (fh_<repo>_commits.csv windows)")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
