import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("before_after_table.csv")
df = df[(df["Pre-LLM Mean"] != "N/A") & (df["Post-LLM Mean"] != "N/A")]
df["Change_num"] = df["Change %"].str.replace("%","").str.replace("+","").apply(lambda x: float(x) if x != "N/A" else None)

metrics = ["Bug-Fix Ratio", "Cyclomatic Complexity", "Avg Function Length", "Comment Density"]
groups = ["Static Analysis", "AI & ML Research", "Developer Tools"]
colors = ["#2196F3", "#4CAF50", "#FF9800"]

fig, axes = plt.subplots(1, len(metrics), figsize=(18, 6))
fig.suptitle("LLM Impact by Repository Group — Mean Change %", fontsize=13, fontweight="bold")

for j, metric in enumerate(metrics):
    df_m = df[df["Metric"] == metric]
    means = []
    for group in groups:
        vals = df_m[df_m["Group"] == group]["Change_num"].dropna()
        means.append(vals.mean() if len(vals) > 0 else 0)
    bars = axes[j].bar(groups, means, color=colors, alpha=0.8, edgecolor="black", linewidth=0.5)
    axes[j].axhline(y=0, color="black", linewidth=0.8)
    axes[j].set_title(metric, fontweight="bold", fontsize=10)
    axes[j].set_ylabel("Mean Change %")
    axes[j].tick_params(axis="x", rotation=25)
    axes[j].grid(True, alpha=0.3, axis="y")
    for bar, val in zip(bars, means):
        axes[j].text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + (2 if val >= 0 else -8),
                    f"{val:+.0f}%", ha="center", fontsize=8, fontweight="bold")

plt.tight_layout()
plt.savefig("group_comparison.png", dpi=150, bbox_inches="tight")
print("Saved: group_comparison.png")
