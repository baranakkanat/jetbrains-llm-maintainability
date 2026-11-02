"""(a) AI-co-authored ('pair') commit counts straight from git, then a SHA-level
comparison with m2_<repo>.csv.

Run: .venv/bin/python3 within_developer/verification/a_pair_counts.py
Writes a_pair_counts_output.txt, a_pair_commits_<repo>.csv next to this file.
"""
import collections
import os
import re
import subprocess

import pandas as pd

from common import (GIT_PATTERNS, HERE, PY_PATTERNS, REPO_ROOT, REPOS, WD,
                    WINDOW_START, git, is_prod, log_records)

OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


GREP_ARGS = ["-i", "-E"] + [f"--grep={p}" for p in GIT_PATTERNS]

# Tool of a matched line. Order matters: the first hit wins on a line, so
# "Junie/Opus 5" -> Junie and "OpenCode with GPT-5.3 Codex <noreply@openai.com>"
# -> Codex (Codex is checked before OpenAI).
TOOL_ORDER = [
    ("Junie", r"junie"), ("Codex", r"codex"), ("Copilot", r"copilot"),
    ("Cursor", r"cursor"), ("ChatGPT", r"chatgpt"), ("Codeium", r"codeium"),
    ("Tabnine", r"tabnine"), ("Gemini", r"gemini"),
    ("AI Assistant", r"ai[ -]assistant"),
    ("Claude", r"claude|anthropic"), ("OpenAI", r"openai"),
]
AGENT_NAMES = {"claude", "copilot", "junie", "codex", "cursor", "devin",
               "chatgpt", "gemini", "openai", "anthropic"}


def line_tool(line: str) -> str:
    low = line.lower()
    for name, pat in TOOL_ORDER:
        if re.search(pat, low):
            return name
    return "?"


def is_bot_author(an: str, ae: str) -> bool:
    if "[bot]" in an.lower() or "[bot]" in ae.lower():
        return True
    if an.strip().lower() in AGENT_NAMES:
        return True
    local = ae.split("@")[0].lower()
    local = re.sub(r"^\d+\+", "", local)          # GitHub noreply "1234+name"
    return local in AGENT_NAMES


def analyse(repo: str):
    say(f"\n=== {repo} ===")
    # 1. Plain git counts (shell-equivalent commands shown in VERIFICATION.md).
    n_plain_since = len(git(repo, "log", "--no-merges", "--since=2025-01-01T00:00:00Z",
                            *GREP_ARGS, "--format=%H").split())
    say(f"git log --no-merges --since=2025-01-01T00:00:00Z -i -E --grep x3 : {n_plain_since}")
    # 2. Same grep without --since; window applied on %ct (guards against the
    #    --since early-stop heuristic on out-of-order committer dates).
    recs = [r for r in log_records(repo, GREP_ARGS, with_files="name-status-norenames")
            if r["ct"] >= WINDOW_START]
    say(f"same grep, window filtered on committer time            : {len(recs)}")

    rows = []
    for r in recs:
        lines = [ln for ln in r["body"].splitlines() if any(p.search(ln) for p in PY_PATTERNS)]
        tools = sorted({line_tool(ln) for ln in lines})
        kinds = sorted({i for ln in lines for i, p in enumerate(PY_PATTERNS) if p.search(ln)})
        # Production files: union of old and new paths (renames appear as D+A
        # because of --no-renames).
        paths = {f[1] for f in r["files"]} | {f[2] for f in r["files"]}
        prod = sorted(p for p in paths if is_prod(p))
        rows.append(dict(sha=r["sha"], ct=r["ct"], author=r["an"], email=r["ae"],
                         tools="+".join(tools), kinds="+".join(map(str, kinds)),
                         bot_author=is_bot_author(r["an"], r["ae"]),
                         n_files=len(paths), n_prod=len(prod),
                         subject=r["subject"], matched="|".join(l.strip() for l in lines)))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(HERE, f"a_pair_commits_{repo}.csv"), index=False)

    say(f"  by tool       : {df.tools.value_counts().to_dict()}")
    say(f"  by pattern    : {df.kinds.value_counts().to_dict()}  (0=Co-authored-by, 1=Generated with [..], 2=Assisted-by)")
    say(f"  bot/agent author: {int(df.bot_author.sum())}  {df[df.bot_author].author.value_counts().to_dict()}")
    human = df[~df.bot_author]
    say(f"  pair (non-bot author)                 : {len(human)}")
    say(f"  pair (non-bot author) with prod file  : {int((human.n_prod > 0).sum())}")
    say(f"  pair (non-bot) by tool                : {human.tools.value_counts().to_dict()}")
    say(f"  pair (non-bot) with prod, by tool     : {human[human.n_prod > 0].tools.value_counts().to_dict()}")

    # 3. Compare with the analysis' m2 file.
    m2 = pd.read_csv(os.path.join(WD, f"m2_{repo}.csv"))
    m2p = m2[m2.group == "pair"]
    say(f"  m2: group==pair {len(m2p)}, with prod_files>0 {int((m2p.prod_files > 0).sum())}; "
        f"group==agent {int((m2.group == 'agent').sum())}; rows {len(m2)}")
    mine = set(human.sha)
    theirs = set(m2p.sha)
    say(f"  SHA sets: fresh-only {len(mine - theirs)}, m2-only {len(theirs - mine)}, both {len(mine & theirs)}")
    mine_p = set(human[human.n_prod > 0].sha)
    theirs_p = set(m2p[m2p.prod_files > 0].sha)
    say(f"  with prod files: fresh-only {len(mine_p - theirs_p)}, m2-only {len(theirs_p - mine_p)}, both {len(mine_p & theirs_p)}")

    m2i = m2.set_index("sha")
    for sha in sorted(mine - theirs):
        row = human[human.sha == sha].iloc[0]
        where = (f"m2 group={m2i.loc[sha, 'group']} tool={m2i.loc[sha, 'tool']}"
                 if sha in m2i.index else "not in m2")
        say(f"    fresh-only {sha[:10]} [{where}] author={row.author!r} line={row.matched[:110]!r}")
    for sha in sorted(theirs - mine):
        info = git(repo, "log", "-1", "--format=%ct|%an|%ae|%s", sha).strip()
        trailers = [ln.strip() for ln in git(repo, "log", "-1", "--format=%B", sha).splitlines()
                    if re.search(r"co-authored|generated|assisted|claude|codex|junie|copilot", ln, re.I)]
        say(f"    m2-only {sha[:10]} tool={m2i.loc[sha, 'tool']} {info[:100]!r} lines={trailers[:3]}")
    # Tool labels on the shared SHAs.
    both = sorted(mine & theirs)
    hb = human.set_index("sha").loc[both]
    ct = pd.crosstab(hb.tools, m2i.loc[both, "tool"].fillna("-"), rownames=["fresh"], colnames=["m2"])
    say("  tool label crosstab on shared SHAs:\n" + "\n".join("    " + l for l in ct.to_string().splitlines()))
    # Production-file disagreements among SHAs in both sets.
    pf = hb["n_prod"]
    diff = [(s[:10], int(pf[s]), int(m2i.loc[s, "prod_files"])) for s in both if pf[s] != m2i.loc[s, "prod_files"]]
    say(f"  prod-file count (old+new paths, --no-renames) differs on {len(diff)} of {len(both)} shared SHAs (fresh, m2): {diff[:6]}")
    # Same count with rename detection, counting each renamed file once (new path).
    pf2 = {r["sha"]: len({f[2] for f in r["files"] if is_prod(f[2])})
           for r in log_records(repo, GREP_ARGS, with_files="name-status-renames") if r["sha"] in set(both)}
    diff2 = [(s[:10], pf2[s], int(m2i.loc[s, "prod_files"])) for s in both if pf2[s] != m2i.loc[s, "prod_files"]]
    say(f"  prod-file count (-M, new path once) differs on {len(diff2)} SHAs (fresh, m2): {diff2}")
    # Agent / bot accounts in the whole window and how m2 treats them.
    allrecs = [r for r in log_records(repo) if r["ct"] >= WINDOW_START]
    bots = collections.Counter(r["an"] for r in allrecs if is_bot_author(r["an"], r["ae"]))
    grp = collections.Counter((r["an"], m2i.loc[r["sha"], "group"] if r["sha"] in m2i.index else "absent")
                              for r in allrecs if is_bot_author(r["an"], r["ae"]))
    say(f"  window: {len(allrecs)} non-merge commits, m2 rows {len(m2)}; bot/agent-account authors {dict(bots)}")
    say(f"  m2 group of those commits: {dict(grp)}")
    return df


def main():
    for repo in REPOS:
        analyse(repo)
    s = pd.read_csv(os.path.join(REPO_ROOT, "llm_signals_summary.csv")).drop_duplicates("Repository")
    s = s[s.Repository.isin(REPOS)][["Repository", "CommitsSince2021", "AuthorshipCommits", "MentionOnlyCommits"]]
    say("\nllm_signals_summary.csv (all refs since 2021, different pattern list):")
    say(s.to_string(index=False))
    with open(os.path.join(HERE, "a_pair_counts_output.txt"), "w") as fh:
        fh.write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
