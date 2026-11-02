"""Per-commit metrics for the within-developer AI vs. human comparison.

For every non-merge commit since a date, records who wrote it (agent bot,
human with an AI co-author trailer, or unlabelled human) and what the commit
did to production code:

  - size: code lines added/deleted, production and test files touched
  - complexity of the methods it changed (new version)
  - complexity it added: delta for modified methods, complexity of brand-new
    methods, and net cyclomatic complexity added per 100 added lines
  - share of added production lines that are comments
  - whether the commit message says it is a fix

Test code (test/, tests/, testData/, *Test.*) is counted but excluded from the
complexity measures: in kotlin, testData holds thousands of compiler inputs
that are not production code. Files above 5000 lines or 400 KB are skipped,
as in the original pipeline (generated tables).

Usage: python mine_commits.py <repo_path> <repo_name> <out_csv> [since]
"""

import re
import sys
import time

import numpy as np
import pandas as pd
from pydriller import Repository

sys.setrecursionlimit(20000)

AI_TRAILER = re.compile(
    r"co-?authored-by:[^\n]*(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|"
    r"openai|anthropic|ai-assistant|codex|junie)"
    r"|generated\s+with\s+\[?(claude|copilot|chatgpt|cursor|codex|junie)"
    r"|assisted-by:[^\n]*(copilot|claude|chatgpt|codex|junie)",
    re.I,
)
TOOL = [("claude", "Claude"), ("anthropic", "Claude"), ("codex", "Codex"),
        ("openai", "Codex"), ("chatgpt", "ChatGPT"), ("copilot", "Copilot"),
        ("cursor", "Cursor"), ("junie", "Junie"), ("gemini", "Gemini")]
MODEL = re.compile(r"co-?authored-by:\s*([^<\n]+?)\s*<", re.I)
AGENT_AUTHOR = re.compile(r"^(jetbrains-)?(claude|copilot|codex|cursor|junie)(\[bot\]|-bot|\b)", re.I)
OTHER_BOT = re.compile(r"\[bot\]|dependabot|renovate|^ideavim bot$|teamcity|buildserver"
                       r"|^space$|automation|robot", re.I)
CODE_EXT = (".kt", ".kts", ".java", ".scala")
TEST_PATH = re.compile(r"(^|/)(test|tests|testData|testdata|test-data|testSrc|testResources)(/|$)"
                       r"|Test[s]?\.(kt|kts|java|scala)$|Spec\.(kt|kts|scala)$")
FIX = re.compile(r"\b(fix|fixes|fixed|fixing|bug|crash|regression|broken)\b", re.I)
MAX_LINES, MAX_CHARS = 5000, 400_000


def comment_line(line):
    s = line.strip()
    return s.startswith("//") or s.startswith("/*") or s.startswith("*") or s.endswith("*/")


def too_big(src):
    return bool(src) and (len(src) > MAX_CHARS or src.count("\n") > MAX_LINES)


def classify(author, msg):
    if AGENT_AUTHOR.search(author):
        return "agent"
    if OTHER_BOT.search(author):
        return None
    return "pair" if AI_TRAILER.search(msg) else "human"


def tool_and_model(author, msg):
    text = (author + " " + msg).lower()
    tool = next((t for k, t in TOOL if k in text), "")
    model = ""
    for m in MODEL.finditer(msg):
        name = m.group(1).strip()
        if any(k in name.lower() for k, _ in TOOL):
            model = name
            break
    return tool, model


def file_metrics(m):
    """Return a dict of complexity measures for one production code file."""
    out = {"cc_changed": [], "nloc_changed": [], "params_changed": [],
           "cc_delta_modified": [], "nloc_delta_modified": [],
           "cc_new_methods": [], "nloc_new_methods": [], "net_cc": 0.0, "ok": False}
    try:
        if too_big(m.source_code) or too_big(m.source_code_before):
            return out
        before = {f.long_name: f for f in m.methods_before}
        after = m.methods
        changed = m.changed_methods
    except Exception:
        return out
    out["ok"] = True
    out["net_cc"] = (sum(f.complexity for f in after)
                     - sum(f.complexity for f in before.values()))
    after_names = {f.long_name for f in after}
    for f in changed:
        if f.long_name not in after_names:      # deleted method, reported in before-list
            continue
        out["cc_changed"].append(f.complexity)
        out["nloc_changed"].append(f.nloc)
        out["params_changed"].append(len(f.parameters))
        old = before.get(f.long_name)
        if old is None:
            out["cc_new_methods"].append(f.complexity)
            out["nloc_new_methods"].append(f.nloc)
        else:
            out["cc_delta_modified"].append(f.complexity - old.complexity)
            out["nloc_delta_modified"].append(f.nloc - old.nloc)
    return out


def mean(values):
    return float(np.mean(values)) if values else np.nan


def main(repo_path, repo_name, out_csv, since="2025-06-01"):
    rows, t0 = [], time.time()
    repo = Repository(repo_path, since=pd.Timestamp(since).to_pydatetime(), only_no_merge=True)
    for i, c in enumerate(repo.traverse_commits()):
        author = c.author.name or ""
        msg = c.msg or ""
        group = classify(author, msg)
        if group is None:
            continue
        tool, model = tool_and_model(author, msg) if group != "human" else ("", "")

        prod_files = test_files = added = deleted = 0
        added_nonblank = added_comment = 0
        agg = {k: [] for k in ["cc_changed", "nloc_changed", "params_changed",
                               "cc_delta_modified", "nloc_delta_modified",
                               "cc_new_methods", "nloc_new_methods"]}
        net_cc, measured = 0.0, 0
        try:
            mods = list(c.modified_files)
        except Exception:
            mods = []
        for m in mods:
            path = m.new_path or m.old_path or ""
            if not path.endswith(CODE_EXT):
                continue
            if TEST_PATH.search(path):
                test_files += 1
                continue
            prod_files += 1
            added += m.added_lines
            deleted += m.deleted_lines
            try:
                for _, line in m.diff_parsed.get("added", []):
                    if line.strip():
                        added_nonblank += 1
                        added_comment += comment_line(line)
            except Exception:
                pass
            fm = file_metrics(m)
            if fm["ok"]:
                measured += 1
                net_cc += fm["net_cc"]
                for k in agg:
                    agg[k].extend(fm[k])

        rows.append({
            "repo": repo_name, "sha": c.hash, "date": c.committer_date.isoformat(),
            "author": author, "group": group, "tool": tool, "model": model,
            "files": len(mods), "prod_files": prod_files, "test_files": test_files,
            "measured_files": measured, "added_code": added, "deleted_code": deleted,
            "added_comment_share": added_comment / added_nonblank if added_nonblank else np.nan,
            "changed_methods": len(agg["cc_changed"]),
            "new_methods": len(agg["cc_new_methods"]),
            "cc_changed_mean": mean(agg["cc_changed"]),
            "nloc_changed_mean": mean(agg["nloc_changed"]),
            "params_changed_mean": mean(agg["params_changed"]),
            "cc_delta_modified_mean": mean(agg["cc_delta_modified"]),
            "nloc_delta_modified_mean": mean(agg["nloc_delta_modified"]),
            "cc_new_methods_mean": mean(agg["cc_new_methods"]),
            "nloc_new_methods_mean": mean(agg["nloc_new_methods"]),
            "net_cc": net_cc if measured else np.nan,
            "net_cc_per_100_added": (100 * net_cc / added) if measured and added >= 5 else np.nan,
            "is_fix_msg": bool(FIX.search(msg.splitlines()[0] if msg else "")),
        })
        if i and i % 500 == 0:
            rate = i / (time.time() - t0)
            print(f"[{repo_name}] {i} commits, {rate:.1f}/s", flush=True)
            pd.DataFrame(rows).to_csv(out_csv, index=False)  # checkpoint
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    print(f"[{repo_name}] DONE {len(rows)} commits in {time.time() - t0:.0f}s -> {out_csv}",
          flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
