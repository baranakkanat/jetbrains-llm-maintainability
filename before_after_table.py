
import pandas as pd
import numpy as np
from scipy import stats
from pydriller import Repository
from datetime import datetime
import re
import lizard

REPOS = {
    "astminer": "https://github.com/JetBrains-Research/astminer",
    "refactorinsight": "https://github.com/JetBrains-Research/refactorinsight",
    "kotlin-ref-miner": "https://github.com/JetBrains-Research/kotlin-ref-miner",
    "code-change-miner": "https://github.com/JetBrains-Research/code-change-miner",
    "bug-finder": "https://github.com/JetBrains-Research/bug-finder",
    "TestSpark": "https://github.com/JetBrains-Research/TestSpark",
    "lca-baselines": "https://github.com/JetBrains-Research/lca-baselines",
    "reflekt": "https://github.com/JetBrains-Research/reflekt",
    "docs-fine-tuning": "https://github.com/JetBrains-Research/docs-fine-tuning",
    "commit_message_generation": "https://github.com/JetBrains-Research/commit_message_generation",
    "code-summarization-dataset": "https://github.com/JetBrains-Research/code-summarization-dataset",
    "similar-python-dependencies": "https://github.com/JetBrains-Research/similar-python-dependencies",
    "compose-multiplatform": "https://github.com/JetBrains/compose-multiplatform",
    "educational-plugin": "https://github.com/JetBrains/educational-plugin",
    "intellij-plugins": "https://github.com/JetBrains/intellij-plugins",
    "markdown": "https://github.com/JetBrains/markdown",
    "ideavim": "https://github.com/JetBrains/ideavim",
    "spbla": "https://github.com/JetBrains-Research/spbla",
    "spla": "https://github.com/JetBrains-Research/spla",
    "paddle": "https://github.com/JetBrains-Research/paddle",
}

GROUPS = {
    "astminer": "Static Analysis",
    "refactorinsight": "Static Analysis",
    "kotlin-ref-miner": "Static Analysis",
    "code-change-miner": "Static Analysis",
    "bug-finder": "Static Analysis",
    "TestSpark": "AI & ML Research",
    "lca-baselines": "AI & ML Research",
    "reflekt": "AI & ML Research",
    "docs-fine-tuning": "AI & ML Research",
    "commit_message_generation": "AI & ML Research",
    "code-summarization-dataset": "AI & ML Research",
    "similar-python-dependencies": "AI & ML Research",
    "compose-multiplatform": "Developer Tools",
    "educational-plugin": "Developer Tools",
    "intellij-plugins": "Developer Tools",
    "markdown": "Developer Tools",
    "ideavim": "Developer Tools",
    "spbla": "Developer Tools",
    "spla": "Developer Tools",
    "paddle": "Developer Tools",
}

BUG_KEYWORDS = re.compile(r"\b(fix|bug|error|issue|crash|defect|patch|hotfix|broken|failure)\b", re.IGNORECASE)
PRE_END = datetime(2021, 6, 1)
POST_START = datetime(2023, 1, 1)

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

def get_cc(source_code, filename):
    try:
        analysis = lizard.analyze_file.analyze_source_code(filename, source_code)
        if not analysis.function_list:
            return None, None
        cc = sum(f.cyclomatic_complexity for f in analysis.function_list) / len(analysis.function_list)
        fl = sum(f.length for f in analysis.function_list) / len(analysis.function_list)
        return cc, fl
    except:
        return None, None

all_results = []

for repo_name, repo_url in REPOS.items():
    print(f"-> {repo_name}...")
    pre_metrics = {"comment_ratio": [], "bugfix": [], "lines": [], "del_add": [], "cc": [], "fn_len": []}
    post_metrics = {"comment_ratio": [], "bugfix": [], "lines": [], "del_add": [], "cc": [], "fn_len": []}

    try:
        for commit in Repository(repo_url, since=datetime(2019,1,1), only_no_merge=True).traverse_commits():
            dt = commit.committer_date.replace(tzinfo=None)
            if dt <= PRE_END:
                period = "pre"
            elif dt >= POST_START:
                period = "post"
            else:
                continue

            bucket = pre_metrics if period == "pre" else post_metrics
            is_bugfix = 1 if BUG_KEYWORDS.search(commit.msg or "") else 0
            added = sum(f.added_lines for f in commit.modified_files)
            deleted = sum(f.deleted_lines for f in commit.modified_files)
            bucket["bugfix"].append(is_bugfix)
            bucket["lines"].append(added + deleted)
            if added > 0:
                bucket["del_add"].append(deleted / added)

            for file in commit.modified_files:
                ext = None
                for e in [".py", ".kt", ".java"]:
                    if file.filename.endswith(e):
                        ext = e
                        break
                if ext and file.source_code:
                    r = comment_ratio(file.source_code, ext)
                    if r is not None:
                        bucket["comment_ratio"].append(r)
                    cc, fl = get_cc(file.source_code, file.filename)
                    if cc is not None:
                        bucket["cc"].append(cc)
                        bucket["fn_len"].append(fl)

        def safe_mean(lst):
            return np.mean(lst) if lst else None

        def mw_pval(pre, post):
            if len(pre) < 5 or len(post) < 5:
                return None
            _, p = stats.mannwhitneyu(pre, post, alternative="two-sided")
            return p

        for metric_key, label in [
            ("comment_ratio", "Comment Density"),
            ("bugfix", "Bug-Fix Ratio"),
            ("lines", "Avg Lines/Commit"),
            ("del_add", "Del/Add Ratio"),
            ("cc", "Cyclomatic Complexity"),
            ("fn_len", "Avg Function Length"),
        ]:
            pre_vals = pre_metrics[metric_key]
            post_vals = post_metrics[metric_key]
            pre_mean = safe_mean(pre_vals)
            post_mean = safe_mean(post_vals)
            pval = mw_pval(pre_vals, post_vals)

            if pre_mean is not None and post_mean is not None and pre_mean != 0:
                change_pct = ((post_mean - pre_mean) / pre_mean) * 100
            else:
                change_pct = None

            all_results.append({
                "Group": GROUPS[repo_name],
                "Repository": repo_name,
                "Metric": label,
                "Pre-LLM Mean": round(pre_mean, 4) if pre_mean else "N/A",
                "Post-LLM Mean": round(post_mean, 4) if post_mean else "N/A",
                "Change %": f"{change_pct:+.1f}%" if change_pct is not None else "N/A",
                "p-value": f"{pval:.4f}" if pval else "N/A",
                "Significant": "✓" if pval and pval < 0.05 else "",
            })

    except Exception as e:
        print(f"   Error: {e}")

df = pd.DataFrame(all_results)
df = df.sort_values(["Group", "Repository", "Metric"])
df.to_csv("before_after_table.csv", index=False)

print("\n=== BEFORE/AFTER TABLE ===")
print(df.to_string(index=False))
print("\nSaved: before_after_table.csv")
