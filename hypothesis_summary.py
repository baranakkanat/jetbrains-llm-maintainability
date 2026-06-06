import pandas as pd

df = pd.read_csv("before_after_table.csv")
df = df[(df["Pre-LLM Mean"] != "N/A") & (df["Post-LLM Mean"] != "N/A")]

maintainability_metrics = ["Bug-Fix Ratio", "Cyclomatic Complexity", "Avg Function Length"]
df_main = df[df["Metric"].isin(maintainability_metrics)]

supported = 0
not_supported = 0
total = 0

print("=== HYPOTHESIS TEST ===")
print("H: LLMs degrade the maintainability of code bases")
print()

for repo in df_main["Repository"].unique():
    repo_data = df_main[df_main["Repository"] == repo]
    sig = repo_data[repo_data["Significant"] == "✓"]
    if len(sig) == 0:
        continue
    degraded = 0
    improved = 0
    for _, row in sig.iterrows():
        change = row["Change %"].replace("%", "").replace("+", "")
        try:
            val = float(change)
            if val > 0:
                degraded += 1
            else:
                improved += 1
        except:
            pass
    if degraded > 0 or improved > 0:
        total += 1
        if degraded >= improved:
            supported += 1
            verdict = "SUPPORTS hypothesis"
        else:
            not_supported += 1
            verdict = "CONTRADICTS hypothesis"
        print(f"  {repo}: {verdict} ({degraded} degraded, {improved} improved)")

print()
print(f"=== RESULT ===")
print(f"Total repos with significant findings: {total}")
print(f"Support hypothesis: {supported}")
print(f"Contradict hypothesis: {not_supported}")
if total > 0:
    pct = supported/total*100
    print(f"Conclusion: Hypothesis {'PARTIALLY SUPPORTED' if supported > not_supported else 'NOT SUPPORTED'} ({supported}/{total} repos, {pct:.0f}%)")
