"""How many developers stand behind each exploratory tool / model group (context for E1-E3).

A clustered estimate for a group that one developer dominates is that
developer's contrast, not a property of the tool.

Reads results_overnight/overnight_core_commits.csv.
Usage: python exploratory_counts.py > results_overnight/exploratory_counts.txt
"""

import pandas as pd

from exploratory import family, generation


def main():
    d = pd.read_csv("results_overnight/overnight_core_commits.csv")
    p = d[d.group == "pair"].copy()
    p["model"] = p.model.fillna("")
    p["tool"] = p.tool.fillna("")
    p["family"] = p.model.map(family)
    p["generation"] = p.model.map(generation)
    for col in ["tool", "family", "generation"]:
        t = p.groupby(col).agg(commits=("sha", "size"), developers=("author", "nunique"))
        t["largest_developer_share"] = p.groupby(col).author.agg(
            lambda s: s.value_counts().iloc[0] / len(s)).round(2)
        print(f"=== AI-co-authored commits by {col} ('' = not identified) ===")
        print(t.to_string(), "\n")
    for tool in ["Codex", "Junie"]:
        print(f"=== {tool} commits per developer ===")
        print(p[p.tool == tool].groupby(["repo", "author"]).size().to_string(), "\n")
    print("=== Claude model strings ===")
    print(p[p.tool == "Claude"].model.replace("", "(none)").value_counts().to_string())


if __name__ == "__main__":
    main()
