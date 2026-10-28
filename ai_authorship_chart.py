"""
Figure of the direct AI-authorship evidence found by llm_signal_mining.py.

Left : labelled commits per repository (repositories with at least 5).
Right: labelled commits per month, against the "post-LLM" window used by the
       date-based before/after design (Jan 2023 - Dec 2025).

The right panel is the point of the figure: almost every labelled commit
falls after the window that the before/after design attributes to LLMs.

Input : llm_signals_summary.csv, llm_signals.csv
Output: ai_authorship.png
"""

import matplotlib.pyplot as plt
import pandas as pd

SUMMARY_IN = "llm_signals_summary.csv"
DETAIL_IN = "llm_signals.csv"
OUT = "ai_authorship.png"
MIN_COMMITS_SHOWN = 5

summary = pd.read_csv(SUMMARY_IN)
labelled = summary[summary["AuthorshipCommits"] > 0]
shown = labelled[labelled["AuthorshipCommits"] >= MIN_COMMITS_SHOWN] \
    .sort_values("AuthorshipCommits")

detail = pd.read_csv(DETAIL_IN)
detail = detail[detail["Tier"] == "authorship"].copy()
detail["Date"] = pd.to_datetime(detail["Date"], utc=True, format="mixed").dt.tz_localize(None)
monthly = detail.groupby(detail["Date"].dt.to_period("M")).size()
monthly = monthly.reindex(pd.period_range("2023-01", monthly.index.max(), freq="M"), fill_value=0)

fig, (left, right) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1, 1.4]})

# Left: per-repository counts
left.barh(shown["Repository"], shown["AuthorshipCommits"], color="#3b6ea5")
for y, value in enumerate(shown["AuthorshipCommits"]):
    left.text(value + 5, y, str(value), va="center", fontsize=9)
left.set_xlabel("Commits with an AI-authorship trailer")
left.set_title(f"{int(labelled['AuthorshipCommits'].sum()):,} labelled commits in "
               f"{len(labelled)} of {len(summary)} repositories", fontsize=11)
left.spines[["top", "right"]].set_visible(False)

# Right: monthly timeline against the post-LLM window
x = monthly.index.to_timestamp()
right.bar(x, monthly.values, width=25, color="#3b6ea5")
right.axvspan(pd.Timestamp("2023-01-01"), pd.Timestamp("2025-12-31"),
              color="#d9a441", alpha=0.18, label="'Post-LLM' window of the before/after design")
right.set_ylabel("Labelled commits per month")
right.set_title("When the labelled commits appear", fontsize=11)
right.legend(loc="upper left", frameon=False, fontsize=9)
right.spines[["top", "right"]].set_visible(False)

fig.suptitle("Direct evidence of AI-assisted commits in the 199-repository JetBrains sample",
             fontsize=13, y=1.0)
fig.text(0.5, -0.02,
         "Labels: Co-Authored-By / Generated-with / Assisted-by trailers naming an AI assistant. "
         "Commits that only mention AI tools are excluded.",
         ha="center", fontsize=8.5, color="#555555")
fig.tight_layout()
fig.savefig(OUT, dpi=150, bbox_inches="tight")
print(f"Saved: {OUT}")
