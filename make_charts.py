"""
All figures for the corrected 199-repository analysis.

Input : before_after_table.csv   (before_after.py, FDR-corrected tests)
        cache_monthly/*.csv      (mine_fast.py, monthly aggregates per repository)
Output: figures/heatmap.png
        figures/direction_summary.png
        figures/trends.png and figures/trend_<metric>.png

The AI-authorship figure is ai_authorship.png in the repository root, made by
ai_authorship_counts.py and ai_authorship_chart.py from default-branch history.

Every figure states its sample size and window in the title or caption, so a
reader who sees one image out of context still knows what it describes.
"""

import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.patches import Patch

TABLE = "before_after_table.csv"
CACHE_DIR = "cache_monthly"
OUT_DIR = "figures"
SAMPLE_SIZE = 199

METRICS = ["Comment Density", "Avg Lines/Commit", "Bug-Fix Ratio",
           "Cyclomatic Complexity", "Avg Function Length", "Del/Add Ratio"]
SLUG = {
    "Comment Density": "comment_density",
    "Avg Lines/Commit": "lines_per_commit",
    "Bug-Fix Ratio": "bug_fix_ratio",
    "Cyclomatic Complexity": "cyclomatic_complexity",
    "Avg Function Length": "function_length",
    "Del/Add Ratio": "del_add_ratio",
}
UNITS = {
    "Comment Density": "share of non-blank lines that are comments",
    "Avg Lines/Commit": "lines added + deleted per commit",
    "Bug-Fix Ratio": "share of commits whose message names a fix",
    "Cyclomatic Complexity": "mean per function",
    "Avg Function Length": "lines per function",
    "Del/Add Ratio": "deleted / added lines per commit",
}

# Reference palette (dataviz skill): light surface, ink, diverging blue <-> red.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
NEUTRAL = "#f0efec"
BLUE = "#2a78d6"
BLUE_LIGHT = "#cde2fb"
RED = "#e34948"
ORANGE = "#eb6834"

PRE = (pd.Timestamp("2019-01-01"), pd.Timestamp("2021-06-01"))
POST = (pd.Timestamp("2023-01-01"), pd.Timestamp("2026-01-01"))
COPILOT = pd.Timestamp("2021-06-29")
CHATGPT = pd.Timestamp("2022-11-30")

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK_2, "xtick.color": MUTED,
    "ytick.color": MUTED, "text.color": INK, "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
})


def save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {path}")


# ---------------------------------------------------------------------------
# 1. Heatmap of significant effects
# ---------------------------------------------------------------------------

def heatmap(table):
    sig = table[table["Significant_FDR"] == "yes"]
    repos = sorted(sig["Repository"].unique(), key=str.lower)
    if not repos:
        print("No FDR-significant results; heatmap skipped.")
        return

    d = table.pivot_table(index="Repository", columns="Metric", values="Cohen d", aggfunc="first")
    tested = table.pivot_table(index="Repository", columns="Metric",
                               values="Tested", aggfunc="first")
    flag = table.pivot_table(index="Repository", columns="Metric",
                             values="Significant_FDR", aggfunc="first")
    d, tested, flag = (x.reindex(index=repos, columns=METRICS) for x in (d, tested, flag))

    shown = d.where(flag == "yes")
    # The colour scale is capped at |d| = 3. One extreme cell (d = -6.3) would
    # otherwise wash every moderate effect out to near-grey. The printed value
    # in each cell is always the uncapped one.
    limit = 3.0
    cmap = LinearSegmentedColormap.from_list("div", [BLUE, NEUTRAL, RED])
    norm = TwoSlopeNorm(vmin=-limit, vcenter=0, vmax=limit)
    norm.clip = True

    height = max(4.0, 0.32 * len(repos) + 2.2)
    fig, ax = plt.subplots(figsize=(10, height))
    ax.grid(False)
    for i, repo in enumerate(repos):
        for j, metric in enumerate(METRICS):
            value = shown.loc[repo, metric]
            if pd.notna(value):
                color = cmap(norm(value))
            elif tested.loc[repo, metric] == "yes":
                color = NEUTRAL
            else:
                color = SURFACE
            ax.add_patch(plt.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, color=color,
                                       linewidth=0))
            if pd.notna(value):
                ax.text(j + 0.5, i + 0.5, f"{value:+.2f}", ha="center", va="center",
                        fontsize=8, color="#ffffff" if abs(value) > 0.55 * limit else INK)
            elif tested.loc[repo, metric] != "yes":
                ax.text(j + 0.5, i + 0.5, "–", ha="center", va="center",
                        fontsize=8, color=MUTED)

    ax.set_xlim(0, len(METRICS))
    ax.set_ylim(len(repos), 0)
    ax.set_xticks(np.arange(len(METRICS)) + 0.5)
    ax.set_xticklabels([m.replace(" ", "\n", 1) for m in METRICS], fontsize=9, color=INK_2)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(repos)) + 0.5)
    ax.set_yticklabels(repos, fontsize=8.5, color=INK_2)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    bar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, extend="both", shrink=0.6)
    bar.set_label("Cohen's d (post − pre), colour capped at ±3", color=INK_2)
    bar.outline.set_visible(False)

    n_tested = table.loc[table["Tested"] == "yes", "Repository"].nunique()
    ax.set_title(f"Significant before/after changes: {len(repos)} of {n_tested} testable "
                 f"repositories\n(random sample of {SAMPLE_SIZE} JetBrains repositories, "
                 f"Benjamini-Hochberg FDR < 0.05)",
                 loc="left", fontsize=11.5, color=INK, pad=42)
    ax.annotate(
             "Pre-LLM: Jan 2019 – May 2021. Post-LLM: Jan 2023 – Dec 2025. Red = metric went up, "
             "blue = went down.\nGrey = tested, no significant change. "
             "– = too few active months to test. Repositories without any significant "
             "change are not listed.",
             xy=(0, 0), xycoords="axes fraction", xytext=(0, -10), textcoords="offset points",
             fontsize=8, color=MUTED, va="top", annotation_clip=False)
    save(fig, "heatmap.png")


# ---------------------------------------------------------------------------
# 2. Direction summary: how many repositories moved, and which way
# ---------------------------------------------------------------------------

def direction_summary(table):
    rows = []
    for metric in METRICS:
        sub = table[table["Metric"] == metric]
        testable = sub[sub["Tested"] == "yes"]
        sig = testable[testable["Significant_FDR"] == "yes"]
        rows.append({
            "Metric": metric,
            "Down": int((sig["Abs Change"] < 0).sum()),
            "No significant change": len(testable) - len(sig),
            "Up": int((sig["Abs Change"] > 0).sum()),
            "Not testable": SAMPLE_SIZE - len(testable),
        })
    frame = pd.DataFrame(rows).set_index("Metric").loc[METRICS[::-1]]

    segments = [("Down", BLUE, "#ffffff"), ("No significant change", NEUTRAL, INK_2),
                ("Up", RED, "#ffffff"), ("Not testable", SURFACE, MUTED)]
    fig, ax = plt.subplots(figsize=(10, 4.4))
    ax.grid(False)
    y = np.arange(len(frame))
    left = np.zeros(len(frame))
    for name, color, text_color in segments:
        values = frame[name].to_numpy()
        ax.barh(y, values, left=left, height=0.62, color=color,
                edgecolor=SURFACE if name != "Not testable" else AXIS,
                linewidth=2 if name != "Not testable" else 0.8, label=name)
        for yi, (v, l) in enumerate(zip(values, left)):
            if v >= 6:
                ax.text(l + v / 2, yi, str(v), ha="center", va="center",
                        fontsize=9, color=text_color)
        left += values

    # thin segments cannot hold their own number, so every row also states
    # its significant counts in words at the right edge
    for yi, metric in enumerate(frame.index):
        ax.text(SAMPLE_SIZE + 3, yi,
                f"{frame.loc[metric, 'Down']} down · {frame.loc[metric, 'Up']} up",
                va="center", fontsize=9, color=INK_2, clip_on=False)

    ax.set_yticks(y)
    ax.set_yticklabels(frame.index, color=INK_2)
    ax.set_xlim(0, SAMPLE_SIZE)
    ax.set_xlabel("Repositories", color=INK_2)
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), frameon=False,
              fontsize=9, handlelength=1.2)
    ax.set_title(f"Direction of significant change per metric, all {SAMPLE_SIZE} repositories",
                 loc="left", fontsize=11.5, pad=30)
    fig.text(0.01, -0.02,
             "Post-LLM (2023–2025) vs pre-LLM (2019 – mid 2021), Mann-Whitney U on monthly "
             "values, Benjamini-Hochberg FDR < 0.05.\nNot testable = fewer than 6 active "
             "months in either period. A date-based comparison shows change, not its cause.",
             fontsize=8, color=MUTED, va="top")
    save(fig, "direction_summary.png")
    return frame


# ---------------------------------------------------------------------------
# 3. Trends: cross-repository median per month
# ---------------------------------------------------------------------------

def load_monthly():
    frames = []
    for path in glob.glob(os.path.join(CACHE_DIR, "*.csv")):
        frame = pd.read_csv(path)
        if frame.empty:
            continue
        frame["Repository"] = os.path.basename(path)[:-4]
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    data["month"] = pd.PeriodIndex(data["month"], freq="M").to_timestamp()
    return data[data["month"] < POST[1]]


SMOOTH_WINDOW = "183D"   # six months
MIN_ACTIVE_REPOS = 15


def smoothed(data, metric):
    """
    Six-month moving average of one metric within each repository.

    A small repository with two commits in a month has a bug-fix ratio of
    exactly 0, 0.5 or 1; taking the cross-repository median of such values
    makes the curve jump to zero whenever most active repositories happened to
    commit no fix that month. Averaging each repository over a time window
    first (time-based, so inactive gaps are not bridged) removes that
    small-count noise without letting any single repository dominate.
    """
    parts = []
    for repo, frame in data[["Repository", "month", metric]].dropna().groupby("Repository"):
        series = frame.set_index("month")[metric].sort_index()
        rolled = series.rolling(SMOOTH_WINDOW, min_periods=2).mean()
        parts.append(pd.DataFrame({"Repository": repo, "month": rolled.index,
                                   metric: rolled.to_numpy()}))
    return pd.concat(parts, ignore_index=True).dropna()


def trend_panel(ax, data, metric):
    grouped = smoothed(data, metric).groupby("month")[metric]
    median = grouped.median()
    q1, q3 = grouped.quantile(0.25), grouped.quantile(0.75)
    counts = grouped.count()
    # months with very few active repositories make the median jump around
    keep = counts >= MIN_ACTIVE_REPOS
    median, q1, q3 = median[keep], q1[keep], q3[keep]

    for start, end in (PRE, POST):
        ax.axvspan(start, end, color="#f4f3ef", zorder=0, linewidth=0)
    ax.fill_between(q1.index, q1, q3, color=BLUE_LIGHT, linewidth=0, zorder=1,
                    label="Middle 50% of repositories")
    ax.plot(median.index, median, color=BLUE, linewidth=2, zorder=3,
            label="Median repository")
    for when, label in ((COPILOT, "Copilot"), (CHATGPT, "ChatGPT")):
        ax.axvline(when, color=INK_2, linewidth=0.9, linestyle=(0, (3, 3)), zorder=4)
        ax.text(when, 1.0, f" {label}", transform=ax.get_xaxis_transform(),
                fontsize=8, color=INK_2, va="top")
    ax.set_title(metric, loc="left", fontsize=10.5, color=INK)
    ax.set_ylabel(UNITS[metric], fontsize=8, color=MUTED)
    ax.set_ylim(bottom=0)
    ax.set_xlim(pd.Timestamp("2019-01-01"), POST[1])
    return int(counts.max())


def trends(data):
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.6), sharex=True)
    peak = 0
    for ax, metric in zip(axes.flat, METRICS):
        peak = max(peak, trend_panel(ax, data, metric))
    handles = [Patch(color=BLUE_LIGHT, label="Middle 50% of repositories"),
               plt.Line2D([], [], color=BLUE, linewidth=2, label="Median repository"),
               Patch(color="#f4f3ef", label="Pre- and post-LLM comparison windows")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.01, 0.955), ncol=3,
               frameon=False, fontsize=9)
    fig.suptitle(f"Maintainability proxies over time across {SAMPLE_SIZE} randomly sampled "
                 f"JetBrains repositories", x=0.01, ha="left", fontsize=13, y=0.995)
    fig.text(0.01, -0.01,
             f"Each repository is first averaged over a six-month moving window; each month then "
             f"shows the median and interquartile range across active repositories (up to {peak}; "
             f"months with fewer than {MIN_ACTIVE_REPOS} are omitted).\nLine metrics use every "
             f"commit; comment density, complexity and function length use a seeded sample of up "
             f"to 10 commits per repository-month. The set of active repositories\nchanges over "
             f"time, so these curves describe the sample, not individual projects.",
             fontsize=8, color=MUTED, va="top")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, "trends.png")

    for metric in METRICS:
        fig, ax = plt.subplots(figsize=(9, 4.2))
        trend_panel(ax, data, metric)
        ax.legend(loc="upper left", bbox_to_anchor=(0, -0.1), ncol=2, frameon=False, fontsize=8.5)
        ax.set_title(f"{metric} — median across {SAMPLE_SIZE} sampled JetBrains repositories",
                     loc="left", fontsize=11)
        save(fig, f"trend_{SLUG[metric]}.png")


def main():
    table = pd.read_csv(TABLE)
    heatmap(table)
    summary = direction_summary(table)
    print(summary.loc[METRICS].to_string())
    trends(load_monthly())


if __name__ == "__main__":
    main()
