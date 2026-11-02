"""Exploratory analyses (not pre-registered; see ANALYSIS_PLAN.md).

Uses overnight_core_commits.csv written by analyze_overnight.py: eligible
developers' production commits in AI-active months.

  E1  tool: Claude vs Junie vs Codex labelled commits, each vs own unlabelled
  E2  Claude model family: Sonnet vs Opus vs Fable
  E3  Claude model generation: 4.x vs 5.x
"""

import re
import warnings

import numpy as np
import pandas as pd

from analyze_overnight import fe_ols

warnings.filterwarnings("ignore")
OUTCOMES = {"added_comment_share": "Comment share of added lines",
            "log_size": "log(lines changed)",
            "cc_delta_modified_mean": "Complexity added to modified methods"}


def family(model):
    m = str(model).lower()
    for f in ["fable", "opus", "sonnet", "haiku"]:
        if f in m:
            return f
    return ""


def generation(model):
    hit = re.search(r"(\d)(?:\.\d+)?", str(model))
    return f"{hit.group(1)}.x" if hit and "claude" in str(model).lower() else ""


def run(d, indicators, title):
    print(f"\n=== {title} ===")
    counts = {k: int(d[k].sum()) for k in indicators}
    print("labelled commits per indicator:", counts)
    rows = []
    for col, label in OUTCOMES.items():
        controls = [] if col == "log_size" else ["log_size"]
        for r in fe_ols(d, col, indicators, controls, ["author", "repo_month"]):
            rows.append({"outcome": label, **r})
    out = pd.DataFrame(rows)
    print(out.to_string(index=False))
    return out


def main():
    pd.set_option("display.width", 250)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    d = pd.read_csv("overnight_core_commits.csv")
    d["model"] = d["model"].fillna("")
    d["tool"] = d["tool"].fillna("")
    pair = d.group == "pair"
    for t in ["Claude", "Junie", "Codex"]:
        d[f"is_{t.lower()}"] = (pair & (d.tool == t)).astype(float)
    d["fam"] = np.where(pair, d.model.map(family), "")
    for f in ["sonnet", "opus", "fable"]:
        d[f"is_{f}"] = (d.fam == f).astype(float)
    d["gen"] = np.where(pair, d.model.map(generation), "")
    d["is_gen4"] = (d.gen == "4.x").astype(float)
    d["is_gen5"] = (d.gen == "5.x").astype(float)

    keep_tools = d[(d.group == "human") | d.tool.isin(["Claude", "Junie", "Codex"])]
    e1 = run(keep_tools, ["is_claude", "is_junie", "is_codex"], "E1 tool vs own unlabelled commits")
    keep_fam = d[(d.group == "human") | d.fam.isin(["sonnet", "opus", "fable"])]
    e2 = run(keep_fam, ["is_sonnet", "is_opus", "is_fable"], "E2 Claude family vs own unlabelled")
    keep_gen = d[(d.group == "human") | d.gen.isin(["4.x", "5.x"])]
    e3 = run(keep_gen, ["is_gen4", "is_gen5"], "E3 Claude generation vs own unlabelled")
    pd.concat([e1.assign(analysis="E1"), e2.assign(analysis="E2"), e3.assign(analysis="E3")]
              ).to_csv("overnight_exploratory.csv", index=False)


if __name__ == "__main__":
    main()
