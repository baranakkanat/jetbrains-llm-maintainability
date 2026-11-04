"""
Figure of the direct AI-authorship evidence in the 199-repository sample.

Left : commits per repository (repositories with at least 5).
Right: commits per month, against the "post-LLM" window used by the
       date-based before/after design (Jan 2023 - Dec 2025).
Both panels stack two groups: commits by a person with an AI co-author
trailer (the within-developer analysis' AI-co-authored group) and commits
authored by an AI agent account.

The right panel is the point of the figure: almost every labelled commit
falls after the window that the before/after design attributes to LLMs.

Counts come from ai_authorship_counts.py: default-branch history up to the
moment the analysis clones were taken, with the rules of the within-developer
analysis, so the AI-co-authored segment matches within_developer/REPORT.md.

Input : ai_authorship_commits.csv, ai_authorship_repos.csv
Output: ai_authorship.png
"""

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch

from ai_authorship_counts import UNTIL

COMMITS_IN = "ai_authorship_commits.csv"
REPOS_IN = "ai_authorship_repos.csv"
OUT = "ai_authorship.png"
MIN_COMMITS_SHOWN = 5
HUMAN, HUMAN_LIGHT = "#3b6ea5", "#a9c1dc"
AGENT, AGENT_LIGHT = "#e0703a", "#f2c2a6"

repos = pd.read_csv(REPOS_IN)
repos["Total"] = repos["AICoauthored"] + repos["AgentCommits"]
labelled = repos[repos["Total"] > 0]
shown = labelled[labelled["Total"] >= MIN_COMMITS_SHOWN].sort_values("Total")

commits = pd.read_csv(COMMITS_IN)
commits["Date"] = pd.to_datetime(commits["Date"], utc=True, format="mixed").dt.tz_localize(None)
commits["Month"] = commits["Date"].dt.to_period("M")
last_month = commits["Month"].max()
months = pd.period_range("2023-01", last_month, freq="M")
monthly = commits.groupby(["Month", "Group"]).size().unstack(fill_value=0) \
    .reindex(index=months, columns=["pair", "agent"], fill_value=0)
cutoff = pd.Timestamp(UNTIL).tz_localize(None)
partial = cutoff < last_month.end_time

fig, (left, right) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1, 1.4]})

# Left: per-repository counts, agent commits stacked on the AI-co-authored ones
left.barh(shown["Repository"], shown["AICoauthored"], color=HUMAN)
left.barh(shown["Repository"], shown["AgentCommits"], left=shown["AICoauthored"], color=AGENT)
for y, (human, agent, total) in enumerate(shown[["AICoauthored", "AgentCommits", "Total"]].values):
    label = f"{human}" + (f" + {agent}" if agent else "")
    left.text(total + 5, y, label, va="center", fontsize=9)
left.set_xlabel("Commits")
scope = f" (top {len(shown)} of {len(labelled)} shown)" if len(shown) < len(labelled) else ""
left.set_title(f"{int(labelled['AICoauthored'].sum()):,} AI-co-authored + "
               f"{int(labelled['AgentCommits'].sum()):,} agent commits in {len(labelled)} of "
               f"{len(repos)} repositories{scope}", fontsize=10.5)
left.spines[["top", "right"]].set_visible(False)

# Right: monthly timeline against the post-LLM window; each bar covers its month
starts = months.to_timestamp()
human_colors = [HUMAN] * len(months)
agent_colors = [AGENT] * len(months)
if partial:
    human_colors[-1], agent_colors[-1] = HUMAN_LIGHT, AGENT_LIGHT
human_bars = right.bar(starts, monthly["pair"], width=27, align="edge", color=human_colors)
agent_bars = right.bar(starts, monthly["agent"], bottom=monthly["pair"], width=27, align="edge",
                       color=agent_colors)
peak = monthly.sum(axis=1).max()
right.set_ylim(0, peak * 1.22)
if partial:
    for bar, edge in [(human_bars[-1], HUMAN), (agent_bars[-1], AGENT)]:
        bar.set_hatch("///")
        bar.set_edgecolor(edge)
    # label above the plot with a vertical leader, clear of the neighbouring bars
    middle = starts[-1] + pd.Timedelta(days=13)
    right.annotate(f"{last_month.strftime('%b %Y')}: partial month\n"
                   f"(data to {cutoff:%d %b} {cutoff:%H:%M} UTC)",
                   xy=(middle, monthly.iloc[-1].sum()), xytext=(middle, peak * 1.12),
                   ha="right", va="center", fontsize=8.5,
                   arrowprops={"arrowstyle": "-", "color": "#555555", "lw": 0.8,
                               "shrinkA": 0, "relpos": (1, 0.5)})
right.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31"), color="#d9a441", alpha=0.18,
              zorder=0)
right.set_xlim(pd.Timestamp("2023-01-01"), last_month.end_time)
right.set_ylabel("Commits per month")
right.set_title("When the commits appear", fontsize=11)
right.spines[["top", "right"]].set_visible(False)

fig.legend(handles=[Patch(color=HUMAN, label="AI-co-authored: a person's commit with an AI co-author trailer"),
                    Patch(color=AGENT, label="Agent: authored by an AI agent account"),
                    Patch(color="#d9a441", alpha=0.18, label="'Post-LLM' window of the before/after design")],
           loc="upper center", bbox_to_anchor=(0.5, 0.95), ncol=3, frameon=False, fontsize=9)
fig.suptitle("Direct evidence of AI-assisted commits in the 199-repository JetBrains sample",
             fontsize=13, y=1.0)
fig.text(0.5, -0.07,
         "Counting rule: non-merge commits on each repository's default branch, 2021-01-01 to "
         f"{cutoff:%Y-%m-%d %H:%M} UTC (when the analysis clones were taken). AI-co-authored: authored "
         "by a person and carrying a\nCo-authored-by, Generated with or Assisted-by trailer that names an "
         "AI assistant (Copilot, ChatGPT, Claude, Cursor, Codeium, Tabnine, Gemini, OpenAI, Anthropic, "
         "AI Assistant, Codex, Junie).\nAgent: authored by an AI agent account (e.g. claude[bot], Copilot, "
         "jetbrains-junie[bot]), whatever the message says. Other bots are excluded. Rules of "
         "within_developer/mine_commits.py.",
         ha="center", fontsize=8.5, color="#555555")
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT}")
