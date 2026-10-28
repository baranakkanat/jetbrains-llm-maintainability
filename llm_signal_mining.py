"""
Direct evidence of LLM assistance in commit history.

The before/after design uses release dates as a proxy for LLM adoption.
This script looks for explicit traces instead: commit trailers and messages
that name an AI assistant. It clones each sampled repository blobless/bare
(commit metadata only, no file contents) so it runs in minutes, not hours.

Output: llm_signals.csv  (one row per matching commit)
        llm_signals_summary.csv  (one row per repository)
"""

import csv
import json
import os
import re
import shutil
import subprocess
import tempfile

SAMPLE_FILE = "sampled_repos.json"
DETAIL_OUT = "llm_signals.csv"
SUMMARY_OUT = "llm_signals_summary.csv"
SINCE = "2021-01-01"
CLONE_TIMEOUT = 600  # seconds per repository
LOG_TIMEOUT = 300

# Two tiers, and the distinction decides what the result means.
#
# AUTHORSHIP: the commit states that an assistant took part in writing it.
# This is evidence of assistance.
#
# MENTION: the commit talks about an assistant — implementing Copilot support,
# adding an OpenAI client, renaming an "AI Assistant" action. A repository that
# builds AI tooling produces many of these and none of them mean its own code
# was written with help. Counting them as adoption would systematically
# overstate exactly the repositories most likely to be studied.
AUTHORSHIP_PATTERNS = {
    "coauthor_trailer": re.compile(
        r"co-?authored-by:[^\n]*(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|"
        r"openai|anthropic|ai-assistant)", re.I),
    "generated_with": re.compile(
        r"generated\s+with\s+\[?(claude|copilot|chatgpt|cursor)", re.I),
    "assisted_by_trailer": re.compile(
        r"assisted-by:[^\n]*(copilot|claude|chatgpt)", re.I),
}

MENTION_PATTERNS = {
    "copilot": re.compile(r"\bgithub[- ]?copilot\b|\bcopilot\b", re.I),
    "chatgpt": re.compile(r"\bchat ?gpt\b|\bopenai\b|\bgpt-?[345]\b", re.I),
    "claude": re.compile(r"\bclaude\b|\banthropic\b", re.I),
    "jetbrains_ai": re.compile(r"\bai assistant\b|\bjetbrains ai\b|\bfull line completion\b", re.I),
}

SEP = "\x1e"  # record separator unlikely to appear in a commit message


def iter_commits(repo_dir):
    """Yield (sha, iso_date, subject+body) for every commit since SINCE."""
    fmt = SEP.join(["%H", "%cI", "%s%n%b"]) + "\x1d"
    proc = subprocess.run(
        ["git", "-C", repo_dir, "log", "--all", f"--since={SINCE}", f"--pretty=format:{fmt}"],
        capture_output=True, text=True, errors="replace", timeout=LOG_TIMEOUT,
    )
    for record in proc.stdout.split("\x1d"):
        record = record.strip("\n")
        if not record:
            continue
        parts = record.split(SEP)
        if len(parts) >= 3:
            yield parts[0], parts[1], parts[2]


def main():
    with open(SAMPLE_FILE) as f:
        sample = json.load(f)

    detail_rows = []
    summary_rows = []
    workdir = tempfile.mkdtemp(prefix="llm_signal_")

    for index, repo in enumerate(sample, start=1):
        full_name = repo["name"]
        short = full_name.split("/")[-1]
        target = os.path.join(workdir, short + ".git")
        print(f"[{index}/{len(sample)}] {full_name}", flush=True)

        try:
            subprocess.run(
                ["git", "clone", "--filter=blob:none", "--bare", "--quiet",
                 f"https://github.com/{full_name}.git", target],
                check=True, capture_output=True, timeout=CLONE_TIMEOUT,
            )
        except Exception as exc:  # unreachable, renamed, or too slow
            print(f"    skipped: {type(exc).__name__}", flush=True)
            summary_rows.append({
                "Repository": short, "FullName": full_name, "Status": "clone_failed",
                "CommitsSince2021": 0, "MatchingCommits": 0, "Share%": "",
            })
            continue

        total = 0
        authored = 0
        mentioned = 0
        try:
            for sha, date, message in iter_commits(target):
                total += 1
                auth_hits = [n for n, p in AUTHORSHIP_PATTERNS.items() if p.search(message)]
                mention_hits = [n for n, p in MENTION_PATTERNS.items() if p.search(message)]
                if not auth_hits and not mention_hits:
                    continue
                if auth_hits:
                    authored += 1
                else:
                    mentioned += 1
                detail_rows.append({
                    "Repository": short,
                    "FullName": full_name,
                    "Commit": sha,
                    "Date": date,
                    "Tier": "authorship" if auth_hits else "mention",
                    "Signals": "|".join(auth_hits or mention_hits),
                    "Message": message.replace("\n", " ")[:300],
                })
            status = "ok"
        except Exception as exc:
            status = f"log_failed:{type(exc).__name__}"

        share = f"{authored / total * 100:.2f}" if total else ""
        summary_rows.append({
            "Repository": short, "FullName": full_name, "Status": status,
            "CommitsSince2021": total,
            "AuthorshipCommits": authored,
            "MentionOnlyCommits": mentioned,
            "AuthorshipShare%": share,
            # kept so downstream scripts that select candidate repositories
            # read the tier that actually means assistance
            "MatchingCommits": authored,
        })
        if authored or mentioned:
            print(f"    {authored} AI-authored, {mentioned} mention-only, of {total}", flush=True)

        shutil.rmtree(target, ignore_errors=True)

    shutil.rmtree(workdir, ignore_errors=True)

    with open(DETAIL_OUT, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Repository", "FullName", "Commit", "Date",
                           "Tier", "Signals", "Message"])
        writer.writeheader()
        writer.writerows(detail_rows)

    with open(SUMMARY_OUT, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Repository", "FullName", "Status", "CommitsSince2021",
                           "AuthorshipCommits", "MentionOnlyCommits",
                           "AuthorshipShare%", "MatchingCommits"])
        writer.writeheader()
        writer.writerows(summary_rows)

    authored_rows = [r for r in detail_rows if r["Tier"] == "authorship"]
    repos_authored = sum(1 for r in summary_rows if r["AuthorshipCommits"])
    repos_mention = sum(1 for r in summary_rows if r["MentionOnlyCommits"])
    dates = sorted(r["Date"] for r in authored_rows)

    print()
    print("=== LLM SIGNAL MINING ===")
    print(f"Repositories scanned                 : {len(summary_rows)}")
    print(f"Repositories with AI-authored commits: {repos_authored}")
    print(f"Repositories mentioning AI only      : {repos_mention}")
    print(f"AI-authored commits                  : {len(authored_rows)}")
    print(f"Mention-only commits                 : {len(detail_rows) - len(authored_rows)}")
    if dates:
        print(f"First AI-authored commit observed    : {dates[0][:10]}")
        print(f"Last AI-authored commit observed     : {dates[-1][:10]}")
        print()
        print("Note: assistant authorship trailers are a lower bound. Copilot's")
        print("inline completion leaves no trailer, so commits written with it are")
        print("counted as unassisted. Treat the 'human' group as 'unlabelled'.")
    print(f"Saved: {DETAIL_OUT}, {SUMMARY_OUT}")


if __name__ == "__main__":
    main()
