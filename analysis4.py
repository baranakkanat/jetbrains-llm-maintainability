from pydriller import Repository
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import re
import lizard

print("Full analysis starting... (may take 1-2 hours for 20 repos)")

REPOS = {
    # Group 1: Static Analysis & Code Quality
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "buckwheat": "https://github.com/JetBrains-Research/buckwheat",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    # Group 2: AI & ML Research
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "washu": "https://github.com/JetBrains-Research/washu",
    "codetracker": "https://github.com/JetBrains-Research/codetracker",
    "formal-lang-course": "https://github.com/JetBrains-Research/formal-lang-course",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "plugin-utilities": "https://github.com/JetBrains-Research/plugin-utilities",
    "spla": "https://github.com/JetBrains-Research/spla",
}

REPOS = {
    # Group 1: Static Analysis & Code Quality
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "buckwheat": "https://github.com/JetBrains-Research/buckwheat",
    "authorship-detection": "https://github.com/JetBrains-Research/authorship-detection",
    "kotlinRMiner": "https://github.com/JetBrains-Research/kotlinRMiner",
    # Group 2: AI & ML Research
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "washu": "https://github.com/JetBrains-Research/washu",
    "codetracker": "https://github.com/JetBrains-Research/codetracker",
    "formal-lang-course": "https://github.com/JetBrains-Research/formal-lang-course",
    # Group 3: Developer Tools & Infrastructure
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "plugin-utilities": "https://github.com/JetBrains-Research/plugin-utilities",
    "spla": "https://github.com/JetBrains-Research/spla",
}

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
    "spbla": "https://github.com/JetBrains-Research/spbla",
    "spla": "https://github.com/JetBrains-Research/spla",
    "paddle": "https://github.com/JetBrains-Research/paddle",
}

BUG_KEYWORDS = re.compile(r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)

SUPPORTED_EXTENSIONS = {".py", ".kt", ".java"}

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

def get_complexity(source_code, filename):
    if not source_code:
        return None, None
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
        if not analysis.function_list:
            return None, None
        cc = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)
        avg_len = sum(f.length for f in analysis.function_list) / len(analysis.function_list)
        return cc, avg_len
    except Exception as e:
        return None, None

from cache_utils import cache_exists, save_cache, load_cache
import os

file_results = []
commit_results = []

if cache_exists():
    print("Cache found! Loading from cache...")
    df_files, df_commits = load_cache()
else:
    print("No cache found, scanning repos...")

for repo_name, repo_url in REPOS.items():
    print(f"\n-> Scanning {repo_name}...")
    file_count = 0
    commit_count = 0
    try:
        for commit in Repository(repo_url, since=datetime(2019, 1, 1), only_no_merge=True).traverse_commits():
            is_bugfix = 1 if BUG_KEYWORDS.search(commit.msg or "") else 0
            added = sum(f.added_lines for f in commit.modified_files)
            deleted = sum(f.deleted_lines for f in commit.modified_files)
            total_lines = added + deleted
            del_add_ratio = deleted / added if added > 0 else None
            commit_results.append({
                "repo": repo_name,
                "date": commit.committer_date,
                "is_bugfix": is_bugfix,
                "lines_changed": total_lines,
                "del_add_ratio": del_add_ratio,
            })
            commit_count += 1
            for file in commit.modified_files:
                ext = None
                for e in SUPPORTED_EXTENSIONS:
                    if file.filename.endswith(e):
                        ext = e
                        break
                if ext and file.source_code:
                    ratio = comment_ratio(file.source_code, ext)
                    cc, avg_len = get_complexity(file.source_code, file.filename)
                    if ratio is not None:
                        file_results.append({
                            "repo": repo_name,
                            "date": commit.committer_date,
                            "comment_ratio": ratio,
                            "cyclomatic_complexity": cc,
                            "cognitive_complexity": avg_len,
                        })
                        file_count += 1
        print(f"   Done: {commit_count} commits, {file_count} files")
    except Exception as e:
        print(f"   Error: {e}")

    save_cache(pd.DataFrame(file_results), pd.DataFrame(commit_results))

df_files = pd.DataFrame(file_results)
df_files["date"] = pd.to_datetime(df_files["date"], utc=True)
df_files["month"] = df_files["date"].dt.to_period("M")

df_commits = pd.DataFrame(commit_results)
df_commits["date"] = pd.to_datetime(df_commits["date"], utc=True)
df_commits["month"] = df_commits["date"].dt.to_period("M")

monthly_files = df_files.groupby(["repo", "month"]).agg(
    comment_ratio=("comment_ratio", "mean"),
    cyclomatic_complexity=("cyclomatic_complexity", "mean"),
    cognitive_complexity=("cognitive_complexity", "mean"),
).reset_index()
monthly_files["month_dt"] = monthly_files["month"].dt.to_timestamp()

monthly_commits = df_commits.groupby(["repo", "month"]).agg(
    avg_lines_changed=("lines_changed", "mean"),
    bugfix_ratio=("is_bugfix", "mean"),
    del_add_ratio=("del_add_ratio", "mean"),
).reset_index()
monthly_commits["month_dt"] = monthly_commits["month"].dt.to_timestamp()

repos = list(REPOS.keys())
colors = [
    "#2196F3","#1565C0","#42A5F5","#0D47A1","#64B5F6",
    "#4CAF50","#2E7D32","#81C784","#1B5E20","#A5D6A7",
    "#FF9800","#E65100","#FFB74D","#BF360C","#FFCC02",
    "#9C27B0","#6A1B9A","#CE93D8","#AB47BC","#7B1FA2",
]

COPILOT = pd.Timestamp("2021-06-01")
CHATGPT = pd.Timestamp("2022-11-01")

def make_chart(title, filename, df, y_col, ylabel):
    fig, axes = plt.subplots(20, 1, figsize=(14, 60), sharex=True)
    fig.suptitle(title, fontsize=13, fontweight="bold")
    for i, (repo, color) in enumerate(zip(repos, colors)):
        data = df[df["repo"] == repo].sort_values("month_dt")
        if data.empty or data[y_col].dropna().empty:
            axes[i].set_title(f"{repo} — no data", fontsize=8)
            continue
        axes[i].plot(data["month_dt"], data[y_col], color=color, linewidth=1.2, alpha=0.4)
        if len(data) > 3:
            data = data.copy()
            data["rolling"] = data[y_col].rolling(3, min_periods=1).mean()
            axes[i].plot(data["month_dt"], data["rolling"], color=color, linewidth=2.5, label="3-month avg")
        axes[i].axvline(COPILOT, color="orange", linestyle="--", linewidth=1.3, label="Copilot (Jun 2021)")
        axes[i].axvline(CHATGPT, color="red", linestyle="--", linewidth=1.3, label="ChatGPT (Nov 2022)")
        axes[i].set_title(repo, fontweight="bold", fontsize=8)
        axes[i].set_ylabel(ylabel, fontsize=7)
        axes[i].legend(fontsize=6, loc="upper right")
        axes[i].grid(True, alpha=0.3)
    axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[-1].xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.setp(axes[-1].xaxis.get_majorticklabels(), rotation=45)
    plt.tight_layout()
    plt.savefig(filename, dpi=120, bbox_inches="tight")
    print(f"Saved: {filename}")

make_chart("Comment Density — 20 JetBrains Repositories", "chart1_comment_density.png", monthly_files, "comment_ratio", "Comment Ratio")
make_chart("Avg Lines Changed per Commit — 20 JetBrains Repositories", "chart2_commit_size.png", monthly_commits, "avg_lines_changed", "Lines Changed")
make_chart("Bug-Fix Commit Ratio — 20 JetBrains Repositories", "chart3_bugfix_ratio.png", monthly_commits, "bugfix_ratio", "Bug-Fix Ratio")
make_chart("Cyclomatic Complexity — 20 JetBrains Repositories", "chart4_cyclomatic.png", monthly_files, "cyclomatic_complexity", "Cyclomatic Complexity")
make_chart("Avg Function Length — 20 JetBrains Repositories", "chart5_avg_function_length.png", monthly_files, "cognitive_complexity", "Avg Lines per Function")
make_chart("Deletion/Addition Ratio — 20 JetBrains Repositories", "chart6_del_add_ratio.png", monthly_commits, "del_add_ratio", "Del/Add Ratio")

print("\nAll done! 6 charts saved.")
