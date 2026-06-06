import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.read_csv("before_after_table.csv")
df = df[(df["Pre-LLM Mean"] != "N/A") & (df["Post-LLM Mean"] != "N/A")]
df["Change_num"] = df["Change %"].str.replace("%","").str.replace("+","").apply(lambda x: float(x) if x != "N/A" else None)

pivot = df.pivot_table(index="Repository", columns="Metric", values="Change_num", aggfunc="mean")

fig, ax = plt.subplots(figsize=(14, 10))
im = ax.imshow(pivot.values, cmap="RdYlGn_r", aspect="auto", vmin=-100, vmax=200)

ax.set_xticks(range(len(pivot.columns)))
ax.set_xticklabels(pivot.columns, rotation=45, ha="right", fontsize=9)
ax.set_yticks(range(len(pivot.index)))
ax.set_yticklabels(pivot.index, fontsize=9)

for i in range(len(pivot.index)):
    for j in range(len(pivot.columns)):
        val = pivot.values[i, j]
        if not np.isnan(val):
            ax.text(j, i, f"{val:+.0f}%", ha="center", va="center", fontsize=7)

plt.colorbar(im, ax=ax, label="Change % (Post vs Pre LLM)")
ax.set_title("Before/After LLM Adoption — Change % by Repository and Metric", 
             fontsize=12, fontweight="bold", pad=20)
plt.tight_layout()
plt.savefig("heatmap.png", dpi=150, bbox_inches="tight")
print("Saved: heatmap.png")
