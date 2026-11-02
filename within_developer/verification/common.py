"""Shared helpers for the independent verification (written from the plan only).

Nothing here is imported from, or copied from, the analysis scripts.
"""
import os
import re
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WD = os.path.dirname(HERE)                      # within_developer/
REPO_ROOT = os.path.dirname(WD)
REPOS = ["ideavim", "intellij-scala", "kotlin"]

# Window start: 2025-01-01 00:00:00 UTC, compared with the committer timestamp.
WINDOW_START = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())

TOOLS_RE = r"(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|openai|anthropic|ai[ -]assistant|codex|junie)"

# The three pair patterns, written in POSIX ERE so git --grep -i -E can use them
# (git ERE has no \b, so no word boundaries; leading whitespace is tolerated).
GIT_PATTERNS = [
    r"^[[:space:]]*co-authored-by:.*" + TOOLS_RE,
    r"generated with \[[^]]*" + TOOLS_RE,
    r"^[[:space:]]*assisted-by:.*" + TOOLS_RE,
]
# The same patterns in Python syntax (used to find WHICH line matched).
PY_PATTERNS = [
    re.compile(r"^\s*co-authored-by:.*" + TOOLS_RE, re.I),
    re.compile(r"generated with \[[^\]]*" + TOOLS_RE, re.I),
    re.compile(r"^\s*assisted-by:.*" + TOOLS_RE, re.I),
]

PROD_EXT = (".kt", ".kts", ".java", ".scala")
TEST_DIRS = {"test", "tests", "testData", "testdata", "test-data", "testSrc", "testResources"}


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    if any(p in TEST_DIRS for p in parts[:-1]):
        return True
    stem = parts[-1].rsplit(".", 1)[0]
    return stem.endswith(("Test", "Tests", "Spec"))


def is_prod(path: str) -> bool:
    return path.endswith(PROD_EXT) and not is_test_path(path)


def git(repo: str, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", os.path.join(WD, "repos", repo), *args],
        check=True, capture_output=True, text=True, errors="replace",
    ).stdout


def log_records(repo: str, extra_args=(), with_files: str | None = None):
    """Yield dicts for non-merge commits (all history in the shallow clone).

    with_files: None, 'name-status-norenames' or 'name-status-renames'.
    Every record has sha, ct (committer unix time), an, ae, subject, body,
    and, if requested, files = list of (status, old_path, new_path).
    """
    fmt = "%x00%H%x1f%ct%x1f%an%x1f%ae%x1f%s%x1f%B%x1e"
    args = ["log", "--no-merges", f"--format={fmt}", *extra_args]
    if with_files == "name-status-norenames":
        args += ["--name-status", "--no-renames"]
    elif with_files == "name-status-renames":
        args += ["--name-status", "-M"]
    out = git(repo, *args)
    for chunk in out.split("\x00")[1:]:
        head, _, tail = chunk.partition("\x1e")
        sha, ct, an, ae, subj, body = head.split("\x1f", 5)
        rec = dict(sha=sha, ct=int(ct), an=an, ae=ae, subject=subj, body=body)
        if with_files:
            files = []
            for line in tail.strip("\n").splitlines():
                if not line.strip():
                    continue
                f = line.split("\t")
                st = f[0]
                if st[0] in "RC":
                    files.append((st[0], f[1], f[2]))
                else:
                    files.append((st[0], f[1], f[1]))
            rec["files"] = files
        yield rec
