from pydriller import Repository
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re

print("Extended analysis starting... (may take 30-40 minutes)")

REPOS = {
    # Group 1: Static Analysis & Code Quality
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    # Group 2: AI & ML Research
    "TestSpark": "https://github.com/JetBrains-Research/TestSpark",
    "lca-baselines": "https://github.com/JetBrains-Research/lca-baselines",
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "docs-fine-tuning": "https://github.com/JetBrains-Research/docs-fine-tuning",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "similar-python-dependencies": "https://github.com/JetBrains-Research/similar-python-dependencies",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "intellij-community": "https://github.com/JetBrains/intellij-community",
    "kotlin": "https://github.com/JetBrains/kotlin",
    "paddle": "https://github.com/JetBrains-Research/paddle",
}

BUG_KEYWORDS = re.compile(r'\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b', re.IGNORECASE)

def comment_ratio(source_code, extension):
    if not source_code:
        return None
    lines = source_code.split("\n")
    total = len([l for l in lines if l.strip()])
    if total == 0:
        return None
    if extension == ".py":
        comments = len([l for l in lines if l.strip().startswith("#")])
    elif extension in [".kt", ".java"]:
        comments = len([l for l in lines if l.strip().startswith("//")])
    else:
        return None
    return comments / total

file_results = []
commit_results = []

for repo_name, repo_url in REPOS.items():
    print(f"\n-> Scanning {repo_name}...")
    file_count = 0
    commit_count = 0
    try:
        for commit in Repository(repo_url, since=datetime(2019, 1, 1), only_no_merge=True).traverse_commits():
            is_bugfix = 1 if BUG_KEYWORDS.search(commit.msg or "") else 0
            total_lines = sum(f.added_lines + f.deleted_lines for f in commit.modified_files)
            commit_results.append({"repo": repo_name, "date": commit.committer_date, "is_bugfix": is_bugfix, "lines_changed": total_lines})
            commit_count += 1
            for file in commit.modified_files:
                ext = None
                for e in [".py", ".kt", ".java"]:
                    if file.filename.endswith(e):
                        ext = e
                        break
                if ext and file.source_code:
                    ratio = comment_ratio(file.source_code, ext)
                    if ratio is not None:
                        file_results.append({"repo": repo_name, "date": commit.committer_date, "comment_ratio": ratio})
                        file_count += 1
        print(f"   Done: {commit_count} commits, {file_count} files")
    except Exception as e:
        print(f"   Error: {e}")

df_files = pd.DataFrame(file_results)
df_files["date"] = pd.to_datetime(df_files["date"], utc=True)
df_files["month"] = df_files["date"].dt.to_period("M")
df_commits = pd.DataFrame(commit_results)
df_commits["date"] = pd.to_datetime(df_commits["date"], utc=True)
df_commits["month"] = df_commits["date"].dt.to_period("M")
monthly_comments = df_files.groupby(["repo", "month"])["comment_ratio"].mean().reset_index()
monthly_comments["month_dt"] = monthly_comments["month"].dt.to_timestamp()
monthly_commits = df_commits.groupby(["repo", "month"]).agg(avg_lines_changed=("lines_changed", "mean"), bugfix_ratio=("is_bugfix", "mean")).reset_index()
monthly_commits["month_dt"] = monthly_commits["month"].dt.to_timestamp()

colors = ["#2196F3", "#4CAF50", "#FF9800", "#9C27B0", "#F44336", "#00BCD4"]
repos = list(REPOS.keys())
COPILOT = pd.Timestamp("2021-06-01")
CHATGPT = pd.Timestamp("2022-11-01")

def make_chart(title, filename, df, y_col, ylabel):
    fig, axes = plt.subplots(6, 1, figsize=(14, 20), sharex=True)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    for i, (repo, color) in enumerate(zip(repos, colors)):
        data = df[df["repo"] == repo].sort_values("month_dt")
        axes[i].plot(data["month_dt"], data[y_col], color=color, linewidth=1.2, alpha=0.4)
        if len(data) > 3:
            data = data.copy()
            data["rolling"] = data[y_col].rolling(3, min_periods=1).mean()
            axes[i].plot(data["month_dt"], data["rolling"], color=color, linewidth=2.5, label="3-month avg")
        axes[i].axvline(COPILOT, color="orange", linestyle="--", linewidth=1.3, label="Copilot (Jun 2021)")
        axes[i].axvline(CHATGPT, color="red", linestyle="--", linewidth=1.3, label="ChatGPT (Nov 2022)")
        axes[i].set_title(repo, fontweight="bold", fontsize=9)
        axes[i].set_ylabel(ylabel, fontsize=8)
        axes[i].legend(fontsize=7, loc="upper right")
        axes[i].grid(True, alpha=0.3)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.savefig(filename, dpi=150, bbox_inches="tight")
    print(f"Saved: {filename}")

make_chart("Comment Density Over Time — 6 JetBrains Research Repositories", "chart1_comment_density.png", monthly_comments, "comment_ratio", "Comment Ratio")
make_chart("Avg Lines Changed per Commit — 6 JetBrains Research Repositories", "chart2_commit_size.png", monthly_commits, "avg_lines_changed", "Lines Changed")
make_chart("Bug-Fix Commit Ratio — 6 JetBrains Research Repositories", "chart3_bugfix_ratio.png", monthly_commits, "bugfix_ratio", "Bug-Fix Ratio")
print("\nAll done! 3 charts saved.")
