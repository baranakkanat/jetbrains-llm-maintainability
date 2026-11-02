"""Coefficient plot of the within-developer effects (AI-co-authored vs own unlabelled commits).

One panel per outcome, because the outcomes are on different scales. Each
panel shows the estimate and 95% CI of `pair` for the confirmatory model or the
H4 variants, with the earlier run (results_2025-06) as a grey reference.

Reads results_overnight/overnight_confirmatory.csv, results_overnight/overnight_h4.csv
and results_2025-06/within_developer_clustered.csv; writes
results_overnight/within_developer_effects.png.

Usage: python coef_plot.py
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = "results_overnight"
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SERIES, EARLIER = "#2a78d6", "#8a8984"
VARIANT_LABELS = {"base": "base", "a_commit_type": "(a) commit-type FE",
                  "b_same_file": "(b) primary-file FE", "c_claude_only": "(c) Claude only",
                  "d_since_2025_01": "(d) all months since 2025-01"}
PANELS = [  # (title, source, key, x label)
    ("H1  Follow-up fix within 30 days", "conf", "H1 follow-up fix (30d)", "percentage points"),
    ("H2  Reverted later", "conf", "H2 reverted", "percentage points"),
    ("Commit size", "h4", "log(lines changed)", "log(lines changed)"),
    ("Comment share of added lines", "h4", "Comment share of added lines", "percentage points"),
    ("Complexity added to modified methods", "h4", "Complexity added to modified methods",
     "cyclomatic complexity per method"),
    ("Net complexity per 100 added lines", "h4", "Net complexity per 100 added lines",
     "cyclomatic complexity"),
]
PCT = {"H1 follow-up fix (30d)", "H2 reverted", "Comment share of added lines"}


def rows_for(source, key, conf, h4, earlier):
    if source == "conf":
        r = conf[conf.hypothesis == key].iloc[0]
        return [("confirmatory", r.effect, r.ci_low, r.ci_high, SERIES)]
    rows = []
    e = earlier[earlier.outcome == key]
    if len(e):
        e = e.iloc[0]
        rows.append(("earlier run (2025-06 data)", e.effect, e.ci_low, e.ci_high, EARLIER))
    for v, label in VARIANT_LABELS.items():
        r = h4[(h4.outcome == key) & (h4.variant == v)]
        if len(r):
            r = r.iloc[0]
            rows.append((label, r.effect, r.ci_low, r.ci_high, SERIES))
    return rows


def main():
    conf = pd.read_csv(f"{OUT}/overnight_confirmatory.csv")
    h4 = pd.read_csv(f"{OUT}/overnight_h4.csv")
    earlier = pd.read_csv("results_2025-06/within_developer_clustered.csv")
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                         "axes.edgecolor": GRID, "axes.labelcolor": INK_2,
                         "xtick.color": INK_2, "ytick.color": INK_2, "text.color": INK})
    fig, axes = plt.subplots(3, 2, figsize=(11, 9.5), facecolor=SURFACE,
                             gridspec_kw={"height_ratios": [1.3, 3, 3]})
    for ax, (title, source, key, xlabel) in zip(axes.flat, PANELS):
        rows = rows_for(source, key, conf, h4, earlier)
        scale = 100 if key in PCT else 1
        ax.set_facecolor(SURFACE)
        ax.axvline(0, color=INK_2, lw=1, zorder=1)
        for i, (label, b, lo, hi, color) in enumerate(rows):
            y = len(rows) - 1 - i
            ax.plot([lo * scale, hi * scale], [y, y], color=color, lw=2, solid_capstyle="round",
                    zorder=2)
            ax.plot(b * scale, y, "o", ms=8, color=color, mec=SURFACE, mew=2, zorder=3)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([r[0] for r in reversed(rows)])
        ax.set_ylim(-0.7, len(rows) - 0.3)
        ax.set_title(title, loc="left", fontsize=10, color=INK, pad=6)
        ax.set_xlabel(xlabel, fontsize=8.5)
        ax.grid(axis="x", color=GRID, lw=1)
        ax.set_axisbelow(True)
        for side in ["top", "right", "left"]:
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)
    fig.suptitle("AI-co-authored vs the same developer's unlabelled commits: "
                 "estimate and 95% CI\n(author and repo-month fixed effects, "
                 "SE clustered by author; 0 = no difference)",
                 x=0.02, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(f"{OUT}/within_developer_effects.png", dpi=180, facecolor=SURFACE)
    print(f"Saved {OUT}/within_developer_effects.png")


if __name__ == "__main__":
    main()
