"""
Build the anonymised replication package for the within-developer study
(design 3) and the corrected before/after analysis (design 1).

Writes replication_package/ and replication_package.zip, both git-ignored.

People are pseudonymised. Every author name, and every human co-author name
found in the commits of the analysed repositories, becomes a stable ID
(dev_0001, dev_0002, ...). IDs are ordered by an HMAC of the name under a
random key kept next to the mapping, so they are stable across rebuilds but
cannot be computed from a guessed name. Automation and AI agent accounts (AUTOMATION_ACCOUNTS) keep
their names: they are tools, not people. E-mail addresses, commit message
text other than the subject line, and co-author trailer lines are dropped.
Commit SHAs and repository names are kept. The name-to-ID mapping is written
only to the file given with --map, which must lie outside the repository.

Inputs that are not in git are rebuilt or required first:
  * per-file histories (fh_<repo>_files.csv) are regenerated from the
    committed commit lists (fh_<repo>_commits.csv) and clones in
    within_developer/repos/ (cloned if missing), with the path rules of the
    run that produced each result folder;
  * cache_monthly/ must exist (python3 mine_fast.py).

The package is then verified:
  (a) no real author name, author or co-author e-mail, or identifying string in
      any file of the package, code, binaries and file names included;
  (b) the confirmatory analysis and the H4 table rerun from the package data
      reproduce results_overnight/; design 1 is rerun from cache_monthly/ and
      compared with the published before_after_table.csv cell by cell (the
      published table is kept either way);
  (c) size and file list.

Usage:
    python3 build_replication_package.py --map /path/outside/the/repo/pseudonym_map.csv
"""

import argparse
import contextlib
import hashlib
import hmac
import secrets
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib
from datetime import datetime
from pathlib import Path, PurePosixPath

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
WD = ROOT / "within_developer"
PKG = ROOT / "replication_package"
ZIP = ROOT / "replication_package.zip"
AS_RUN_COMMIT = "24d7497"  # mining code that produced within_developer/results_overnight/

# Tool accounts keep their names; everything else in an author field is a person.
AUTOMATION_ACCOUNTS = {
    "Claude", "Copilot", "IdeaVim Bot", "Junie", "Junie Live CLI IntelliJ bot",
    "PyCharm Automation Bot", "TeamCity", "claude[bot]", "copilot-swe-agent[bot]",
    "dependabot[bot]", "jetbrains-junie[bot]", "junie-eap[bot]",
}

# Design 1 and shared inputs at the repository root
ROOT_FILES = [
    "mine_fast.py", "before_after.py", "metrics.py", "make_charts.py", "before_after_table.csv",
    "sampled_repos.json", "population_with_ids.json", "filtered_population.json",
    "llm_signal_mining.py", "llm_signals.csv", "llm_signals_summary.csv",
    "ai_authorship_counts.py", "ai_authorship_chart.py", "ai_authorship_commits.csv",
    "ai_authorship_repos.csv", "ai_authorship.png",
]
ROOT_DIRS = ["figures", "cache_monthly"]
WD_EXCLUDE = {"within_developer/CLAUDE_CODE_PROMPT.md", "within_developer/PROGRESS.md",
              "within_developer/.gitignore"}
VERBATIM = {"within_developer/ANALYSIS_PLAN.md", "within_developer/ANALYSIS_PLAN.sha256"}

# (repository, shallow-since of its clone, commit list, per-file history, path rules,
#  rows printed by the original run)
FILE_HISTORIES = [
    ("ideavim", "2024-12-01", "fh_ideavim_commits.csv", "fh_ideavim_files.csv", "as_run", 10323),
    ("intellij-scala", "2024-12-01", "fh_intellij-scala_commits.csv",
     "fh_intellij-scala_files.csv", "as_run", 74315),
    ("kotlin", "2024-12-01", "fh_kotlin_commits.csv", "fh_kotlin_files.csv", "as_run", 387561),
    ("intellij-community", "2025-08-01", "fh_intellij-community_commits.csv",
     "fh_intellij-community_files.csv", "as_run", 686275),
    ("ideavim", "2024-12-01", "results_sensitivity/fh_ideavim_commits.csv",
     "results_sensitivity/fh_ideavim_files.csv", "fixed", 10575),
    ("intellij-scala", "2024-12-01", "results_sensitivity/fh_intellij-scala_commits.csv",
     "results_sensitivity/fh_intellij-scala_files.csv", "fixed", 87754),
    ("kotlin", "2024-12-01", "results_sensitivity/fh_kotlin_commits.csv",
     "results_sensitivity/fh_kotlin_files.csv", "fixed", 423354),
]
ANALYSED = ["ideavim", "intellij-scala", "kotlin"]

AUTHOR_COLUMNS = {"author", "Author"}
REPO_COLUMNS = {"repo", "Repository", "FullName"}  # repository names are kept as they are
DROP_COLUMNS = {"Message", "email", "matched"}  # message text, e-mails, trailer lines
HASH_COLUMNS = {"sha", "Commit", "reverted_by", "reverts_sha"}
# Subject lines name people who are not authors and carry branch names with logins; the
# analysis uses them only through the commit-type rule of analyze_overnight.py, so each is
# replaced by a label that the rule maps to the same type.
SUBJECT_COLUMNS = {"subject"}
SUBJECT_LABELS = {"revert": "revert", "fix": "fix", "test": "test", "refactor": "refactor",
                  "docs": "docs", "build": "build", "feature": "feature: add", "other": "other"}
CLEARED_COLUMNS = {"reverts_subject"}  # only used to build reverted_by, which is kept
# File paths can name people (per-user IDE dictionaries) and would show which author
# string a replaced path word came from; the analysis compares paths only for equality.
PATH_COLUMNS = {"path", "primary_file"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
GITHUB_USER_RE = re.compile(r"github\.com/(?!JetBrains/|JetBrains-Research/)[A-Za-z0-9_.-]+"
                            r"(?:/[A-Za-z0-9_.-]+)?", re.I)
LOCAL_PATH_RE = re.compile(r"(?:/Users|/home|/private/tmp|/tmp)/[^\s'\"`)]+")
WARNING_RE = re.compile(r"^\S+\.py:\d+: \w*Warning:.*\n(?:[ \t]+.*\n)?", re.M)
NUMERIC_RE = re.compile(r"-?[0-9.eE+-]+")
CO_AUTHOR_RE = re.compile(r"^\s*co-?authored-by:\s*(.+?)\s*<([^>]*)>", re.I | re.M)
IDENTIFYING_STRINGS = ["baranakkanat", "Akkanat", "rug.nl"]
TEXT_SUFFIXES = {".csv", ".txt", ".md", ".py", ".sh", ".json", ".sha256"}


def run(cmd, **kwargs):
    return subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=True,
                          **kwargs).stdout


def git_ls(path):
    return [p for p in run(["git", "-C", str(ROOT), "ls-files", path]).splitlines() if p]


# ---------------------------------------------------------------------------
# 1. Rebuild the per-file histories
# ---------------------------------------------------------------------------
def ensure_clone(repo, since):
    target = WD / "repos" / repo
    if not target.exists():
        print(f"  cloning {repo} (since {since})", flush=True)
        target.parent.mkdir(exist_ok=True)
        run(["git", "-c", "filter.lfs.process=", "-c", "filter.lfs.smudge=cat",
             "-c", "filter.lfs.required=false", "clone", "--quiet", "--no-checkout",
             f"--shallow-since={since}", f"https://github.com/JetBrains/{repo}", str(target)])
    return target


def as_run_module(name):
    """The mining module as it was when results_overnight/ was produced."""
    source = run(["git", "-C", str(ROOT), "show", f"{AS_RUN_COMMIT}:within_developer/{name}.py"])
    namespace = {"__name__": f"{name}_as_run"}
    exec(compile(source, f"{name}_as_run.py", "exec"), namespace)
    return namespace, source


def regenerate_file_history(repo_dir, commits_csv, out_csv, rules, expected):
    """numstat for exactly the commits of commits_csv, in their order, with the run's path rules.

    The record format and its parsing are those of file_history.py, including its
    one quirk: a commit whose message contains the record marker keeps its row in
    the commit list but loses its file rows (one ideavim commit)."""
    shas = pd.read_csv(commits_csv, usecols=["sha"], dtype=str)["sha"].tolist()
    start, body, end = "\x01", "\x02", "\x03"
    cmd = ["git", "-C", str(repo_dir)]
    if rules == "fixed":
        cmd += ["-c", "diff.renames=true", "-c", "diff.renameLimit=1000"]
    cmd += ["log", "--no-walk=unsorted", "--stdin", "--numstat",
            f"--pretty=format:{start}%H{body}%cI{body}%an{body}%B{end}"]
    if rules == "fixed":
        cmd.append("-M")
    out = run(cmd, input="\n".join(shas) + "\n")
    if rules == "as_run":
        fh, _ = as_run_module("file_history")
        code_ext, test_path = fh["CODE_EXT"], fh["TEST_PATH"]
    else:
        sys.path.insert(0, str(WD))
        import file_history as fh_fixed
        code_ext, test_path = fh_fixed.CODE_EXT, fh_fixed.TEST_PATH
    rows = []
    for block in out.split(start)[1:]:
        header, _, numstat = block.partition(end)
        parts = header.split(body, 3)
        if len(parts) != 4 or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            continue
        sha = parts[0]
        for line in numstat.strip().splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            row = {"sha": sha.strip(), "added": int(added) if added.isdigit() else 0,
                   "deleted": int(deleted) if deleted.isdigit() else 0}
            if rules == "as_run":
                path = fh["normalize_path"](path)
                rows.append({"sha": row["sha"], "path": path, "added": row["added"],
                             "deleted": row["deleted"],
                             "prod": path.endswith(code_ext) and not test_path.search(path)})
            else:
                old, path = fh_fixed.split_rename(path)
                rows.append({"sha": row["sha"], "path": path, "added": row["added"],
                             "deleted": row["deleted"],
                             "prod": path.endswith(code_ext) and not test_path.search(path),
                             "rename_old": False})
                if old is not None:
                    rows.append({"sha": row["sha"], "path": old, "added": 0, "deleted": 0,
                                 "prod": old.endswith(code_ext) and not test_path.search(old),
                                 "rename_old": True})
    pd.DataFrame(rows).to_csv(out_csv, index=False)
    status = "matches the original run" if len(rows) == expected else f"original run: {expected}"
    print(f"  {out_csv.relative_to(ROOT)}: {len(shas)} commits, {len(rows)} rows ({status})",
          flush=True)
    return len(rows) == expected


def rebuild_inputs():
    print("Rebuilding per-file histories", flush=True)
    ok = True
    for repo, since, commits, out, rules, expected in FILE_HISTORIES:
        repo_dir = ensure_clone(repo, since)
        ok &= regenerate_file_history(repo_dir, WD / commits, WD / out, rules, expected)
    if not (ROOT / "cache_monthly").is_dir() or not any((ROOT / "cache_monthly").glob("*.csv")):
        sys.exit("cache_monthly/ is missing: run `python3 mine_fast.py` first.")
    return ok


# ---------------------------------------------------------------------------
# 2. Pseudonyms
# ---------------------------------------------------------------------------
def source_csvs():
    files = [ROOT / f for f in ROOT_FILES if f.endswith(".csv")]
    files += [ROOT / p for p in git_ls("within_developer") if p.endswith(".csv")]
    return files


def collect_people():
    """Author names from every packaged table, and human co-authors from the clones."""
    sys.path.insert(0, str(WD))
    from mine_commits import AI_TRAILER
    authors, emails = set(), set()
    for path in source_csvs():
        frame = pd.read_csv(path, dtype=str, keep_default_na=False)
        for column in AUTHOR_COLUMNS & set(frame.columns):
            authors |= set(frame[column]) - {""}
        if "email" in frame.columns:
            emails |= {e for e in frame["email"] if "@" in e}
    co_authors = set()
    for repo, _, commits, *_ in FILE_HISTORIES[:4]:
        repo_dir = WD / "repos" / repo
        shas = pd.read_csv(WD / commits, usecols=["sha"], dtype=str)["sha"].tolist()
        out = run(["git", "-C", str(repo_dir), "log", "--no-walk=unsorted", "--stdin",
                   "--format=%x1e%an%x1f%ae%x1f%B"], input="\n".join(shas) + "\n")
        for record in out.split("\x1e")[1:]:
            name, email, message = (record.split("\x1f", 2) + ["", ""])[:3]
            if name in authors and "@" in email:  # some accounts carry a bare word here
                emails.add(email.strip())
            for line in message.splitlines():
                hit = CO_AUTHOR_RE.match(line)
                if hit and not AI_TRAILER.search(line):
                    co_authors.add(hit.group(1).strip())
                    if "@" in hit.group(2):
                        emails.add(hit.group(2).strip())
    people = (authors | co_authors) - AUTOMATION_ACCOUNTS
    return people, sorted(co_authors - authors - AUTOMATION_ACCOUNTS), emails


def pseudonym_key(map_path):
    """Random key that orders the IDs; it lives next to the mapping, outside the repository."""
    path = Path(map_path).expanduser().resolve().with_suffix(".key")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(secrets.token_hex(32), encoding="utf-8")
        path.chmod(0o600)
    return bytes.fromhex(path.read_text(encoding="utf-8").strip())


def assign_ids(people, key):
    # an unkeyed hash would let anyone compute a guessed name's ID
    ordered = sorted(people, key=lambda n: hmac.new(key, n.encode("utf-8"), "sha256").hexdigest())
    width = max(3, len(str(len(ordered))))
    return {name: f"dev_{i:0{width}d}" for i, name in enumerate(ordered, start=1)}


def check_outside_repo(path):
    path = Path(path).expanduser().resolve()
    main_repo = Path(run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute",
                          "--git-common-dir"]).strip()).parent
    for forbidden in (ROOT, main_repo, PKG):
        if path == forbidden or forbidden in path.parents:
            sys.exit(f"--map must lie outside the repository and the package: {path}")
    return path


def write_map(mapping, co_author_only, path):
    path = check_outside_repo(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"id": i, "name": n, "kind": "co-author" if n in co_author_only else "author"}
                  for n, i in sorted(mapping.items(), key=lambda kv: kv[1])]
                 ).to_csv(path, index=False)
    print(f"Pseudonym map: {len(mapping)} people -> {path}", flush=True)


def trie_pattern(words):
    """A regex alternation of `words` that prefers the longest match."""
    trie = {}
    for word in words:
        node = trie
        for ch in word:
            node = node.setdefault(ch, {})
        node[""] = {}

    def build(node):
        alternatives = [re.escape(ch) + build(child) for ch, child in sorted(node.items()) if ch]
        if not alternatives:
            return ""
        body = alternatives[0] if len(alternatives) == 1 else "(?:" + "|".join(alternatives) + ")"
        return f"(?:{body})?" if "" in node else body

    return build(trie)


class Scrubber:
    def __init__(self, mapping, repository_names):
        self.mapping = mapping
        # a person named like a repository cannot be replaced in free text without
        # renaming the repository; such names stay for the leak check to report
        self.unreplaceable = sorted(set(mapping) & repository_names)
        names = [n for n in mapping if not NUMERIC_RE.fullmatch(n) and n not in repository_names]
        numeric = [n for n in mapping if NUMERIC_RE.fullmatch(n)]
        self.names_re = re.compile(r"(?<![A-Za-z0-9_])(" + trie_pattern(names) + r")(?![A-Za-z0-9_])")
        self.numeric_re = (re.compile(r"(?<![A-Za-z0-9_.])(" + "|".join(map(re.escape, numeric))
                                      + r")(?![A-Za-z0-9_.])") if numeric else None)
        self.replacements = {}  # (file, name) -> count, reviewed after the build

    def names(self, text, where, numeric=False):
        def swap(match):
            key = (where, match.group(1))
            self.replacements[key] = self.replacements.get(key, 0) + 1
            return self.mapping[match.group(1)]
        text = self.names_re.sub(swap, text)
        if numeric and self.numeric_re is not None:
            text = self.numeric_re.sub(swap, text)
        return text

    def free_text(self, text, where, numeric_names=False, local_paths=False):
        text = EMAIL_RE.sub("<email removed>", text)
        text = GITHUB_USER_RE.sub("github.com/<removed>", text)
        if local_paths:  # prose and console output only, never data cells
            text = LOCAL_PATH_RE.sub("<local path>", text)
        return self.names(text, where, numeric_names)

    def author(self, name):
        if name == "" or name in AUTOMATION_ACCOUNTS:
            return name
        return self.mapping[name]

    def subject(self, text):
        if not hasattr(self, "_commit_type"):
            sys.path.insert(0, str(WD))
            from analyze_overnight import commit_type
            for kind, label in SUBJECT_LABELS.items():
                assert commit_type(label) == kind, (kind, label)
            self._commit_type = commit_type
        return SUBJECT_LABELS[self._commit_type(text)]


def hashed_path(path):
    """A stable 64-bit hash of the path, with its extension kept."""
    if path == "":
        return path
    suffix = PurePosixPath(path).suffix
    suffix = suffix if re.fullmatch(r"\.[A-Za-z0-9]{1,10}", suffix) else ""
    return f"f_{hashlib.sha256(path.encode('utf-8')).hexdigest()[:16]}{suffix}"


# ---------------------------------------------------------------------------
# 3. Copy and transform
# ---------------------------------------------------------------------------
def transform_csv(src, dst, scrub):
    frame = pd.read_csv(src, dtype=str, keep_default_na=False)
    frame = frame.drop(columns=[c for c in frame.columns if c in DROP_COLUMNS])
    for column in frame.columns:
        if column in AUTHOR_COLUMNS:
            frame[column] = frame[column].map(scrub.author)
        elif column in SUBJECT_COLUMNS:
            frame[column] = frame[column].map(scrub.subject)
        elif column in CLEARED_COLUMNS:
            frame[column] = ""
        elif column in PATH_COLUMNS:
            frame[column] = frame[column].map(hashed_path)
        elif column not in HASH_COLUMNS | REPO_COLUMNS | {"_order"}:
            values = frame[column].unique()
            cleaned = {v: v if (v == "" or NUMERIC_RE.fullmatch(v))
                       else scrub.free_text(v, str(dst.relative_to(PKG)), numeric_names=True)
                       for v in values}
            if any(k != v for k, v in cleaned.items()):
                frame[column] = frame[column].map(cleaned)
    authors = [c for c in frame.columns if c in AUTHOR_COLUMNS]
    if authors and not HASH_COLUMNS & set(frame.columns):
        # one row per author, sorted by the real names: sort by ID within the table's groups
        groups = [c for c in ("repo", "Repository", "analysis", "outcome") if c in frame.columns]
        keys = [frame[g].map({v: i for i, v in enumerate(dict.fromkeys(frame[g]))}) for g in groups]
        frame = (frame.assign(**{f"_g{i}": k for i, k in enumerate(keys)})
                 .sort_values([f"_g{i}" for i in range(len(keys))] + authors, kind="stable")
                 .drop(columns=[f"_g{i}" for i in range(len(keys))]))
        print(f"  {dst.relative_to(PKG)}: author rows sorted by ID", flush=True)
    frame.to_csv(dst, index=False)


def transform_text(src, dst, scrub, names=True, prose=True):
    text = src.read_text(encoding="utf-8", errors="replace")
    if prose:  # documents and console output: drop warning lines and local paths
        text = WARNING_RE.sub("", text)
    if names:
        text = scrub.free_text(text, str(dst.relative_to(PKG)), local_paths=prose)
    else:
        text = EMAIL_RE.sub("<email removed>", text)
    dst.write_text(text, encoding="utf-8")


def copy_file(rel, scrub, src_root=ROOT):
    src, dst = src_root / rel, PKG / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if rel in VERBATIM or src.suffix not in TEXT_SUFFIXES:
        shutil.copy2(src, dst)
    elif src.suffix == ".csv":
        transform_csv(src, dst, scrub)
    elif src.suffix in {".md", ".txt"}:
        transform_text(src, dst, scrub)
    elif src.suffix == ".json":  # repository metadata only; names would rename repositories
        transform_text(src, dst, scrub, names=False, prose=False)
    else:  # code: names are replaced too (every replacement is listed after the build)
        transform_text(src, dst, scrub, prose=False)


PACKAGE_EDITS = {
    "within_developer/REPORT.md": [
        ("Overnight run of 2026-11-02.", "Run of 2026-11-02."),
        ("and six differences were recorded in `PROGRESS.md` and committed\n"
         "(commit 62864e9, 05:01 CET), together with `plan_conformance.py`, which",
         "and six differences were recorded and committed to version control before\n"
         "the analysis was run, together with `plan_conformance.py`, which"),
        ("Written by a separate agent that worked only from the plan's definitions, the\n"
         "CSV data and `git` on the clones, without opening any of the analysis\nscripts.",
         "Written independently of the analysis code: the verification scripts were\n"
         "developed from the plan's definitions, the CSV data and `git` on the clones,\n"
         "without reference to the analysis scripts."),
        ("`results_overnight/` (the mining scripts as of commit 24d7497), it has four",
         "`results_overnight/` (the mining scripts in `mining_as_run/`), it has four"),
        ("as the handoff specifies.", "as the study protocol specifies."),
        ("8. **Order of work**: steps 1 and 2 of the handoff ran at the same time, and\n"
         "   the step 4 screen started before step 3 because it only needs step 1. No\n"
         "   result depends on the order.",
         "8. **Order of work**: the AI-signal refresh and the mining ran at the same\n"
         "   time, and the screen of other repositories started before the main\n"
         "   analysis because it needs only the refreshed signals. No result depends\n"
         "   on the order."),
        ("9. **kotlin checkout**: `git-lfs` is not installed but the global git config\n"
         "   names it, so the kotlin checkout failed;",
         "9. **kotlin checkout**: the kotlin checkout failed because an LFS filter was\n"
         "   configured without `git-lfs` being installed;"),
        ("    step-3 results existed (05:15-05:22 vs 05:40); its analysis ran after.",
         "    main results existed (05:15-05:22 vs 05:40); its analysis ran after."),
        ("were fixed in the code after the main run (commits 305f43a and\n"
         "    7c462bc). The confirmatory",
         "were fixed in the code after the main run. The confirmatory"),
        ("    rule in `mine_commits.py` matches \"robot\" anywhere in an author name, so\n"
         "    one intellij-community developer whose surname contains it was dropped as\n"
         "    a bot. They have 127 commits in the mined window (from 2025-09), 114 of\n"
         "    them touching production code, and none AI-co-authored. With no\n"
         "    AI-co-authored commit they could not have been an eligible developer\n"
         "    (>= 8 of each; in the AI-active months they have 80 unlabelled production\n"
         "    commits), and they define no AI-active month.",
         "    rule in `mine_commits.py` matches bot keywords anywhere in an author name,\n"
         "    so one intellij-community developer was dropped as a bot. None of their\n"
         "    commits is AI-co-authored, so they could not have been an eligible\n"
         "    developer (>= 8 of each), and they define no AI-active month."),
        ("| `PROGRESS.md` | time-stamped log of the night, including the pre-results deviation note |\n",
         ""),
        ("| mining (step 2); the two Python files now contain the fixes, and the versions "
         "that produced `results_overnight/` are those of commit 24d7497 |",
         "| mining; the two Python files now contain the fixes, and the versions that "
         "produced `results_overnight/` are in `mining_as_run/` |"),
        ("| the plan's tests H1-H4 (step 3) |", "| the plan's tests H1-H4 |"),
        ("| step 4 screen and intellij-community extension |",
         "| screen of other repositories and intellij-community extension |"),
        ("| step 5, written independently of the analysis code |",
         "| independent re-implementation of three checks |"),
        ("| console output and CSVs of steps 3-4, the figure |",
         "| console output and CSVs of the main and exploratory analyses, the figure |"),
        ("| mined data; `fh_<repo>_files.csv` is regenerated by `file_history.py` |",
         "| mined data; `fh_<repo>_files.csv` is regenerated from the commit list (included) |"),
        ("produced with (`git checkout 24d7497 -- file_history.py mine_commits.py`\n"
         "inside `within_developer/`).",
         "produced with (copy `mining_as_run/file_history.py` and\n"
         "`mining_as_run/mine_commits.py` over the current ones)."),
    ],
    "within_developer/verification/VERIFICATION.md": [
        ("`ANALYSIS_PLAN.md`, the task's definitions, the CSV data files",
         "`ANALYSIS_PLAN.md`, the study's definitions, the CSV data files"),
        ("so the trailer is part of\n"
         "    a long line: `...builds.\\n\\nCo-authored-by: Codex <<email removed>>`. A line-anchored\n"
         "    trailer pattern cannot match.",
         "so the trailer is part of\n"
         "    a longer line and a line-anchored trailer pattern cannot match."),
        ("contains only the prose line \"The code was\n"
         "    generated with Claude Agent\". This is neither",
         "contains only a prose sentence saying that the code was\n"
         "    generated with a Claude agent. This is neither"),
        ("one with a free-text \"generated with Claude Agent\" line.",
         "one with a free-text note that the code was AI-generated."),
    ],
    "within_developer/bot_filter_check.py": [
        ('"""Defect found after the main run: the other-bot rule matches "robot" inside surnames.',
         '"""Defect found after the main run: the other-bot rule matches bot keywords inside names.'),
        ("(mine_commits.py as of commit 24d7497,", "(mine_commits.py as in mining_as_run/,"),
        ("mine_commits.py drops every author whose name matches OTHER_BOT, which includes\n"
         "the substring \"robot\". For each author the rule matched in the main run, this",
         "mine_commits.py drops every author whose name matches OTHER_BOT. For each author\n"
         "the rule matched in the main run, this"),
    ],
    "within_developer/plan_conformance.py": [
        ("Written before the overnight results were seen (see PROGRESS.md, 05:00).",
         "Written before the overnight results were seen."),
    ],
    "within_developer/mine_selected.py": [
        ('"""Exploratory extension (step 4): mine only', '"""Exploratory extension: mine only'),
    ],
    "within_developer/other_repos_check.py": [
        ('"""Step 4 screen: which other', '"""Screen: which other'),
    ],
}
# commit records quoted with their message text (timestamp|author|e-mail|message)
REGEX_EDITS = {
    "within_developer/verification/a_pair_counts_output.txt": [
        (re.compile(r"'\d{9,}\|[^']*'( lines=\[.*\])?$", re.M), "<commit message removed>"),
    ],
}


def apply_edits():
    for rel, edits in PACKAGE_EDITS.items():
        path = PKG / rel
        text = path.read_text(encoding="utf-8")
        for old, new in edits:
            if text.count(old) != 1:
                sys.exit(f"{rel}: edit not applicable ({text.count(old)} matches): {old[:70]!r}")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
    for rel, edits in REGEX_EDITS.items():
        path = PKG / rel
        text = path.read_text(encoding="utf-8")
        for pattern, new in edits:
            text, n = pattern.subn(new, text)
            if n == 0:
                sys.exit(f"{rel}: pattern found no match: {pattern.pattern}")
        path.write_text(text, encoding="utf-8")


REGENERATED = [  # console output printed with real names; rerun on the pseudonymised data
    ("results_overnight/exploratory_counts.txt", ["exploratory_counts.py"], ""),
    ("results_exploratory/intellij_community_output.txt", ["exploratory_intellij_community.py"], ""),
    ("results_sensitivity/comparison.txt", ["sensitivity_compare.py"], ""),
]
# The earlier run's output came from another environment and its statistics do not rerun
# to the same digits, so only its developer table (plain counts) is rebuilt and spliced in.
POOLED = "results_2025-06/pooled_results.txt"
POOLED_TABLE = ("import sys; sys.path.insert(0, '..'); "
                "from analyze_pooled import load, eligible_authors; "
                "d = load(['m_ideavim.csv', 'm_intellij-scala.csv', 'm_kotlin.csv']); "
                "a = eligible_authors(d); "
                "print(d[d.author.isin(a)].groupby(['repo', 'author', 'group']).size()"
                ".unstack(fill_value=0).to_string())")


def comparable_lines(text):
    """Lines without layout. pandas prints a repository index level only on the first row of
    each group, and that row changes when rows are sorted by ID, so a leading repository
    name is dropped."""
    text = WARNING_RE.sub("", LOCAL_PATH_RE.sub("<local path>", text))
    lines = []
    for line in text.splitlines():
        tokens = line.split()
        if tokens and tokens[0] in ANALYSED + ["intellij-community"]:
            tokens = tokens[1:]
        if tokens:
            lines.append(" ".join(tokens))
    return sorted(lines)


def regenerate_outputs(scrub):
    """Tables printed from real names keep each name's padding, which gives away its length.
    Rerun their scripts on the pseudonymised data and keep the new output only if it has the
    same lines as the original (rows may come in a different order, sorted by ID)."""
    wd = PKG / "within_developer"
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp) / "within_developer"
        shutil.copytree(wd, tmp)
        for _, _, _, out, _, _ in FILE_HISTORIES:  # real paths: one diagnostic sorts by path
            shutil.copy2(WD / out, tmp / out)
        for rel, cmd, cwd in REGENERATED:
            new = run([sys.executable, *cmd], cwd=tmp / cwd)
            new = scrub.free_text(WARNING_RE.sub("", new), rel, local_paths=True)
            old = (wd / rel).read_text(encoding="utf-8")
            if comparable_lines(new) != comparable_lines(old):
                extra = sorted(set(comparable_lines(new)) ^ set(comparable_lines(old)))[:6]
                sys.exit(f"regenerated {rel} differs from the original: {extra}")
            (wd / rel).write_text(new, encoding="utf-8")
            print(f"  regenerated {rel} (same lines as the original)", flush=True)
        table = run([sys.executable, "-c", POOLED_TABLE], cwd=tmp / "results_2025-06").rstrip("\n")
        text = (wd / POOLED).read_text(encoding="utf-8")
        start = text.index("\n", text.index("Authors with >= 8 AI-paired")) + 1
        end = text.index("\n\n=== WITHIN-DEVELOPER", start)
        if comparable_lines(table) != comparable_lines(text[start:end]):
            sys.exit(f"rebuilt developer table of {POOLED} differs from the original")
        (wd / POOLED).write_text(text[:start] + table + text[end:], encoding="utf-8")
        print(f"  rebuilt the developer table of {POOLED} (same rows as the original)", flush=True)
    with contextlib.chdir(WD):  # the bot-filter table needs the real names to apply the rule
        sys.path.insert(0, str(WD))
        import bot_filter_check
        frame = bot_filter_check.table()
    frame["rule match"] = [m if a in AUTOMATION_ACCOUNTS else "(bot keyword)"
                           for a, m in zip(frame["author"], frame["rule match"])]
    frame["author"] = frame["author"].map(scrub.author)
    (wd / "bot_filter_check.txt").write_text(
        "Authors dropped by the other-bot rule in the main run (fh_<repo>_commits.csv windows)\n"
        + frame.to_string(index=False) + "\n", encoding="utf-8")
    print("  regenerated bot_filter_check.txt (keyword of the person masked)", flush=True)


def package_readme(mapping, design1_note):
    # every installed distribution with its exact version: the environment the checks ran in
    installed = {d.metadata["Name"]: d.version for d in importlib.metadata.distributions()}
    (PKG / "requirements.txt").write_text(
        f"# Python {sys.version.split()[0]}; exact versions of the environment the package was checked in\n"
        + "".join(f"{name}=={installed[name]}\n" for name in sorted(installed, key=str.lower)),
        encoding="utf-8")
    width = len(next(iter(mapping.values()))) - 4
    (PKG / "README.md").write_text(f"""# Replication package

Two analyses of LLM-assisted development in a random sample of 199 public
JetBrains repositories:

* **Design 3, within-developer comparison** (`within_developer/`): each
  developer's AI-co-authored production commits against their own unlabelled
  commits in the same months. The analysis plan (`ANALYSIS_PLAN.md`, with its
  SHA-256 in `ANALYSIS_PLAN.sha256`) was fixed and hashed before H1-H3 were
  run. The full write-up is `within_developer/REPORT.md`.
* **Design 1, corrected before/after comparison** (repository root): monthly
  maintainability proxies before (2019 - May 2021) and after (2023 - 2025) the
  release of LLM coding assistants, Mann-Whitney U with Benjamini-Hochberg
  correction (`before_after.py`, `before_after_table.csv`, `figures/`).

## Pseudonymisation

* Every person's name in the data (commit authors, and human co-authors named
  in commit trailers) is replaced by a stable ID of the form `dev_{"0" * (width - 1)}1`.
  The same person has the same ID in every file.
* Automation and AI agent accounts keep their account names, e.g. `claude[bot]`,
  `jetbrains-junie[bot]`, `dependabot[bot]`, `TeamCity`.
* Commit messages are not included. Subject lines, which can name other people
  and carry branch names with logins, are replaced by the commit-type category
  that the analysis derives from them (`fix`, `test`, `refactor`, `docs`,
  `build`, `feature: add`, `revert`, `other`; H4 variant (a) uses nothing else).
  E-mail addresses and co-author lines are removed. The documents quote a few
  subject lines and file paths that name no one.
* File paths (`fh_<repo>_files.csv`, `primary_file`) are replaced by a stable
  hash with the file extension kept, because some paths name people. The
  analysis only compares paths for equality, so every result is unchanged; the
  one exception is the tie-break diagnostic in `sensitivity_compare.py`, which
  sorts paths alphabetically and gives different numbers when rerun from the
  hashed paths (the published `results_sensitivity/comparison.txt` used the
  real paths).
* Console tables that listed developers were regenerated from the
  pseudonymised data, so that column widths do not reflect the length of the
  original names; their content was checked to be the same.
* Commit SHAs and repository names are kept, so every commit can be looked up
  in the public repositories.

## Layout

| Path | Content |
|---|---|
| `within_developer/` | design 3: mining and analysis scripts, mined data (`m2_<repo>.csv`, `fh_<repo>_commits.csv`, `fh_<repo>_files.csv`), `ANALYSIS_PLAN.md`, `REPORT.md` |
| `within_developer/results_overnight/` | the confirmatory and robustness results (H1-H4), exploratory tables, figure |
| `within_developer/results_sensitivity/` | the rerun with the fixed mining code |
| `within_developer/results_exploratory/` | intellij-community extension and signal rescan |
| `within_developer/results_2025-06/` | the earlier run on 2025-06 to 2026-11 data |
| `within_developer/verification/` | independent re-implementation of three checks |
| `within_developer/mining_as_run/` | the mining code exactly as it produced `results_overnight/` |
| `cache_monthly/` | design 1 mined data: monthly aggregates per repository |
| `before_after_table.csv`, `figures/` | design 1 results |
| `ai_authorship_*.csv`, `ai_authorship.png` | AI-co-authored and agent commits on each default branch |
| `llm_signals*.csv` | per-commit AI-authorship signals (all refs), message text removed |
| `PACKAGE_CHECKS.txt`, `MANIFEST.txt` | checks run when the package was built; file list with SHA-256 |

## Rerunning the analyses

Python 3.12 or later with the packages in `requirements.txt`
(`python3 -m pip install -r requirements.txt`).

Design 3, from the included mined data:

```bash
cd within_developer
python3 analyze_overnight.py ideavim intellij-scala kotlin   # H1-H4; compare overnight_*.csv with results_overnight/
python3 plan_conformance.py                                  # plan-exact H2 and H4 verdict
(cd results_overnight && python3 ../exploratory.py)          # E1-E3
python3 coef_plot.py                                         # figure
```

Design 1, from the included monthly aggregates:

```bash
python3 before_after.py    # writes before_after_table.csv (rename the published one first to compare)
python3 make_charts.py     # writes figures/
```

{design1_note}

## Mining from scratch

The mining scripts clone the public repositories, so their output contains
the real author names of the public git history.

* Design 3: `within_developer/run_mining.sh` (ideavim, intellij-scala, kotlin
  since 2025-01-01). The current `file_history.py` and `mine_commits.py`
  contain later fixes (see REPORT.md, "Sensitivity"); the versions that
  produced `results_overnight/` are in `within_developer/mining_as_run/`.
  `fh_<repo>_files.csv` in this package were regenerated for exactly the
  commits listed in `fh_<repo>_commits.csv`, with the path rules of the run
  that produced each result folder.
* Design 1: `python3 mine_fast.py` (shallow clones since 2018-12, about an
  hour), then `python3 before_after.py`.
* AI-authorship counts: `python3 ai_authorship_counts.py`, then
  `python3 ai_authorship_chart.py`.
""", encoding="utf-8")


def build(mapping):
    if PKG.exists():
        shutil.rmtree(PKG)
    PKG.mkdir()
    sample = json.loads((ROOT / "sampled_repos.json").read_text(encoding="utf-8"))
    scrub = Scrubber(mapping, {r["name"].split("/")[-1] for r in sample})
    for rel in ROOT_FILES:
        copy_file(rel, scrub)
    for directory in ROOT_DIRS:
        for src in sorted((ROOT / directory).glob("*")):
            if src.is_file() and not src.name.endswith(".tmp"):  # mine_fast.py's partial writes
                copy_file(f"{directory}/{src.name}", scrub)
    for rel in git_ls("within_developer"):
        if rel not in WD_EXCLUDE:
            copy_file(rel, scrub)
    for _, _, _, out, _, _ in FILE_HISTORIES:
        copy_file(f"within_developer/{out}", scrub)
    as_run_dir = PKG / "within_developer" / "mining_as_run"
    as_run_dir.mkdir()
    for name in ["file_history", "mine_commits"]:
        _, source = as_run_module(name)
        src = as_run_dir / f".{name}.src"
        src.write_text(source, encoding="utf-8")
        transform_text(src, as_run_dir / f"{name}.py", scrub, prose=False)
        src.unlink()
    regenerate_outputs(scrub)
    apply_edits()
    remove_empty_directories()
    return scrub


def remove_empty_directories():
    for directory in sorted((p for p in PKG.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(directory.iterdir()):
            directory.rmdir()


# ---------------------------------------------------------------------------
# 4. Verification
# ---------------------------------------------------------------------------
def png_text(data):
    """Text stored in a PNG's tEXt, zTXt and iTXt chunks."""
    out, pos = [], 8
    while pos + 8 <= len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        kind, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        if kind == b"tEXt":
            out.append(body.replace(b"\0", b" ").decode("latin-1"))
        elif kind == b"zTXt":
            key, _, rest = body.partition(b"\0")
            out.append(key.decode("latin-1") + " " + zlib.decompress(rest[1:]).decode("latin-1"))
        elif kind == b"iTXt":
            key, _, rest = body.partition(b"\0")
            compressed, rest = rest[0], rest[2:]
            _, _, rest = rest.partition(b"\0")      # language tag
            _, _, text = rest.partition(b"\0")      # translated keyword
            text = zlib.decompress(text) if compressed else text
            out.append(key.decode("latin-1") + " " + text.decode("utf-8", "replace"))
        pos += 12 + length
    return "\n".join(out)


def check_identifiers(mapping, emails, files=None):
    """(a) Every file of the package, code and binaries included.

    Text files and PNG metadata: whole-word search for every pseudonymised name
    (also across line breaks), substring search for the author and co-author
    e-mail addresses and the authors' identifying strings, and a search for any
    e-mail address; purely numeric names are ignored inside numeric CSV cells.
    Raw bytes of binary files: substring search for the multi-word names, the
    e-mail addresses and the identifying strings (short names would match
    compressed data by chance). File names are searched too."""
    names = [n for n in mapping if not NUMERIC_RE.fullmatch(n)]
    numeric = [n for n in mapping if NUMERIC_RE.fullmatch(n)]
    name_re = re.compile(r"(?<![A-Za-z0-9_])(" + trie_pattern(names) + r")(?![A-Za-z0-9_])")
    distinctive = [n for n in names if len(n) >= 8 and (" " in n or "." in n)]
    needles = [s.lower() for s in sorted(emails) + IDENTIFYING_STRINGS if s]
    hits = {"names": [], "numeric names": [], "e-mails / identifying strings": [],
            "any e-mail address": [], "binary contents": [], "file names": [],
            "own repository commit hashes": []}
    own = run(["git", "-C", str(ROOT), "rev-list", "--all"]).split()
    own_prefixes = {h[:k] for h in own for k in range(7, 41)}
    files = files if files is not None else [p for p in sorted(PKG.rglob("*")) if p.is_file()]
    for path in files:
        rel = str(path.relative_to(PKG))
        hits["file names"] += [(rel, m.group(1)) for m in name_re.finditer(rel)]
        if path.suffix in TEXT_SUFFIXES:
            text = path.read_text(encoding="utf-8", errors="replace")
        else:
            data = path.read_bytes()
            hits["binary contents"] += [(rel, n) for n in distinctive if n.encode() in data]
            hits["binary contents"] += [(rel, s) for s in needles if s.encode() in data.lower()]
            text = png_text(data) if path.suffix == ".png" else ""
        found = {(rel, m.group(1)) for m in name_re.finditer(text)}
        found |= {(rel, m.group(1)) for m in name_re.finditer(re.sub(r"\s+", " ", text))}
        hits["names"] += sorted(found)
        low = text.lower()
        hits["e-mails / identifying strings"] += [(rel, s) for s in needles if s in low]
        hits["any e-mail address"] += [(rel, m.group(0)) for m in EMAIL_RE.finditer(text)]
        hits["own repository commit hashes"] += [
            (rel, t) for t in set(re.findall(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", text))
            if t in own_prefixes]
        for n in numeric:
            for m in re.finditer(r"(?<![A-Za-z0-9_.])" + re.escape(n) + r"(?![A-Za-z0-9_.])", text):
                start = max(text.rfind(",", 0, m.start()), text.rfind("\n", 0, m.start())) + 1
                ends = [i for i in (text.find(",", m.end()), text.find("\n", m.end())) if i != -1]
                cell = text[start:min(ends) if ends else len(text)]
                if not (path.suffix == ".csv" and NUMERIC_RE.fullmatch(cell.strip('"'))):
                    hits["numeric names"].append((rel, n))
    return hits, len(files)


def compare_tables(new, old, keys):
    a, b = pd.read_csv(new), pd.read_csv(old)
    numeric = [c for c in b.columns if c not in keys and pd.api.types.is_numeric_dtype(b[c])]
    merged = a.merge(b, on=keys, suffixes=("_new", "_old"))
    if len(merged) != len(b) or len(a) != len(b):
        return False, float("nan"), f"{len(a)} vs {len(b)} rows"
    diff = max(float(np.nanmax(np.abs(merged[f"{c}_new"] - merged[f"{c}_old"]))) for c in numeric)
    same_nan = all((merged[f"{c}_new"].isna() == merged[f"{c}_old"].isna()).all() for c in numeric)
    return bool(diff == 0 and same_nan), diff, f"{len(b)} rows, columns {', '.join(numeric)}"


def cell_difference(x, y):
    """'' if equal, 'noise' if equal to 1e-9 relative (floating-point precision), else 'real'."""
    if x == y:
        return ""
    try:
        a, b = float(x), float(y)
    except ValueError:
        return "real"
    if a == b or (np.isnan(a) and np.isnan(b)):
        return ""
    return "noise" if abs(a - b) <= 1e-9 * max(abs(a), abs(b)) else "real"


def design1_cells(rerun_csv, published_csv):
    """Cell-by-cell comparison of the rerun design 1 table with the published one."""
    keys = ["Repository", "Metric"]
    pub = pd.read_csv(published_csv, dtype=str, keep_default_na=False)
    new = pd.read_csv(rerun_csv, dtype=str, keep_default_na=False)
    merged = pub.merge(new, on=keys, how="outer", suffixes=("", "_rerun"), indicator=True)
    both = merged[merged["_merge"] == "both"]
    columns = [c for c in pub.columns if c not in keys]
    real, noise, rows, mean_rows = {}, {}, set(), set()
    for c in columns:
        kinds = [cell_difference(x, y) for x, y in zip(both[c], both[f"{c}_rerun"])]
        real[c], noise[c] = kinds.count("real"), kinds.count("noise")
        for key, kind in zip(both[keys].values.tolist(), kinds):
            if kind:
                rows.add(tuple(key))
            if kind == "real" and c in ("Pre-LLM Mean", "Post-LLM Mean"):
                mean_rows.add(tuple(key))
    rel = []
    for c in ("Pre-LLM Mean", "Post-LLM Mean"):
        a = pd.to_numeric(both[c], errors="coerce")
        b = pd.to_numeric(both[f"{c}_rerun"], errors="coerce")
        rel += list(((a - b).abs() / a.abs()).replace([np.inf], np.nan).dropna())
    tested = both[both["Tested"] == "yes"]
    dp = (pd.to_numeric(tested["p-value"], errors="coerce")
          - pd.to_numeric(tested["p-value_rerun"], errors="coerce")).abs()
    flips = both[(both["Significant_FDR"] != both["Significant_FDR_rerun"])
                 | (both["Tested"] != both["Tested_rerun"])]
    return {"rows": len(pub), "rows only in one table": int((merged["_merge"] != "both").sum()),
            "cells": len(both) * len(columns),
            "cells differing": sum(real.values()) + sum(noise.values()),
            "cells differing beyond floating-point precision": sum(real.values()),
            "real per column": {c: n for c, n in real.items() if n},
            "noise per column": {c: n for c, n in noise.items() if n},
            "rows differing": len(rows), "rows with a changed mean": len(mean_rows),
            "repositories with a changed mean": len({r for r, _ in mean_rows}),
            "max relative change of a mean": max(rel) if rel else 0.0,
            "tested p-values changed": int((dp > 1e-9).sum()),
            "max p-value change": float(dp.max()) if len(dp) else 0.0,
            "significance changes": [f"{r.Repository} / {r.Metric}: {r.Significant_FDR or 'not tested'}"
                                     f" -> {r.Significant_FDR_rerun or 'not tested'}"
                                     for r in flips.itertuples()]}


def check_rerun():
    """(b) rerun analyze_overnight.py and before_after.py on copies of the package data."""
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        wd = PKG / "within_developer"
        for name in ["analyze_overnight.py"] + [f"{kind}_{r}{suffix}" for r in ANALYSED
                                                for kind, suffix in [("m2", ".csv"),
                                                                     ("fh", "_commits.csv"),
                                                                     ("fh", "_files.csv")]]:
            shutil.copy2(wd / name, tmp / name)
        run([sys.executable, "analyze_overnight.py", *ANALYSED], cwd=tmp)
        for table, keys in [("overnight_confirmatory.csv", ["hypothesis", "term"]),
                            ("overnight_h4.csv", ["outcome", "variant"])]:
            results[table] = compare_tables(tmp / table, WD / "results_overnight" / table, keys)

        # before_after.py mines any repository without a cache file, for hours: never let it
        sample = json.loads((PKG / "sampled_repos.json").read_text(encoding="utf-8"))
        missing = [r["name"] for r in sample
                   if not (PKG / "cache_monthly" / f"{r['name'].split('/')[-1]}.csv").exists()]
        if missing:
            sys.exit(f"cache_monthly/ lacks {len(missing)} repositories (e.g. {missing[:3]}): "
                     "run `python3 mine_fast.py` until it reports no failures.")
        d1 = tmp / "design1"
        d1.mkdir()
        for name in ["before_after.py", "metrics.py", "sampled_repos.json"]:
            shutil.copy2(PKG / name, d1 / name)
        shutil.copytree(PKG / "cache_monthly", d1 / "cache_monthly")
        run([sys.executable, "before_after.py"], cwd=d1)
        design1 = design1_cells(d1 / "before_after_table.csv", ROOT / "before_after_table.csv")
    return results, design1


def design1_note(design1):
    mined = datetime.fromtimestamp(min(p.stat().st_mtime for p in (ROOT / "cache_monthly").glob("*.csv")))
    if design1["cells differing"] == 0 and design1["rows only in one table"] == 0:
        return ("Running `before_after.py` on `cache_monthly/` reproduces the published "
                "`before_after_table.csv` cell for cell (checked when the package was built; "
                f"`cache_monthly/` was re-mined in {mined:%B %Y} with the versions in `requirements.txt`).")
    return (f"`cache_monthly/` was re-mined in {mined:%B %Y} with the versions in `requirements.txt`. "
            "Running `before_after.py` on it does not reproduce the published `before_after_table.csv` "
            f"exactly. {design1['rows with a changed mean']} of {design1['rows']} repository/metric rows "
            f"(in {design1['repositories with a changed mean']} repositories) have a different pre- or "
            f"post-period mean, by at most {design1['max relative change of a mean']:.1%} of the mean; "
            f"{design1['tested p-values changed']} tested p-values move, by at most "
            f"{design1['max p-value change']:.2f}; {len(design1['significance changes'])} tests change "
            "significance after Benjamini-Hochberg or testability. Other differing cells differ only "
            "at floating-point precision (details in `PACKAGE_CHECKS.txt`). `before_after_table.csv` "
            "and `figures/` are the published results and are kept unchanged.")


def write_manifest():
    lines = []
    for path in sorted(PKG.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.txt":
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            lines.append(f"{digest}  {path.stat().st_size:>10}  {path.relative_to(PKG)}")
    (PKG / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_zip():
    if ZIP.exists():
        ZIP.unlink()
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(PKG.rglob("*")):
            if path.is_file():
                archive.write(path, Path("replication_package") / path.relative_to(PKG))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--map", required=True,
                        help="where to write the name-to-ID mapping (outside the repository)")
    args = parser.parse_args()

    histories_match = rebuild_inputs()
    people, co_author_only, emails = collect_people()
    check_outside_repo(args.map)
    mapping = assign_ids(people, pseudonym_key(args.map))
    write_map(mapping, co_author_only, args.map)
    print("Building replication_package/", flush=True)
    scrub = build(mapping)
    plan_ok = run(["shasum", "-a", "256", "-c", "ANALYSIS_PLAN.sha256"],
                  cwd=PKG / "within_developer").splitlines()[0]

    print("\n(b) rerun from the package data", flush=True)
    rerun, design1 = check_rerun()
    for table, (identical, diff, detail) in rerun.items():
        print(f"  {table}: {'identical' if identical else 'DIFFERS'} (max abs difference {diff}; {detail})")
    print("  design 1 rerun vs published before_after_table.csv:")
    for key, value in design1.items():
        print(f"    {key}: {value}")
    print(f"  per-file histories match the original row counts: {histories_match}; plan hash: {plan_ok}")
    package_readme(mapping, design1_note(design1))

    print("\n(a) identifying information", flush=True)
    hits, n_files = check_identifiers(mapping, emails)
    print(f"  searched all {n_files} files for {len(mapping)} names ({len(co_author_only)} human "
          f"co-authors only), {len(emails)} author/co-author e-mails and {IDENTIFYING_STRINGS}")
    for kind, found in hits.items():
        print(f"  {kind}: {len(found)} hits" + (f", e.g. {found[:5]}" if found else ""))
    if scrub.unreplaceable:
        print(f"  names equal to a repository name, not replaced in free text: {scrub.unreplaceable}")
    print("  name replacements outside CSV files (file: name x count):")
    for (where, name), count in sorted(scrub.replacements.items()):
        if not where.endswith(".csv"):
            print(f"    {where}: {name} x{count}")

    passed_a = all(not found for found in hits.values())
    d3_ok = all(ok for ok, _, _ in rerun.values())
    (PKG / "PACKAGE_CHECKS.txt").write_text(
        "Checks run when this package was built\n\n"
        "Pseudonymisation: author names replaced by keyed IDs, commit subjects replaced by "
        "their commit-type label, file paths replaced by hashes, developer tables regenerated "
        "from the pseudonymised data (see README.md).\n\n"
        f"(a) Identifying information. All {n_files} data, code and document files were searched "
        "(the two check files were scanned afterwards): whole-word search for "
        f"the {len(mapping)} pseudonymised names (text files, code and PNG metadata), substring "
        f"search for {len(emails)} author and co-author e-mail addresses and the authors' "
        "identifying strings, a search for any e-mail address, and the file names. Result: "
        f"{'no hits' if passed_a else 'HITS FOUND'}.\n\n"
        "(b) Reruns from the package data.\n"
        "  within_developer/analyze_overnight.py against the published results_overnight/ tables:\n"
        + "".join(f"    {t}: {'identical' if ok else 'differs'} (max abs difference {d})\n"
                  for t, (ok, d, _) in rerun.items())
        + "  before_after.py on the re-mined cache_monthly/ against the published "
        "before_after_table.csv (the published table is kept):\n"
        f"    cells differing: {design1['cells differing']} of {design1['cells']}, of which "
        f"{design1['cells differing beyond floating-point precision']} beyond floating-point "
        f"precision (relative 1e-9)\n"
        f"    beyond precision, per column: {design1['real per column'] or 'none'}\n"
        f"    at floating-point precision only, per column: {design1['noise per column'] or 'none'}\n"
        f"    repository/metric rows with a different pre- or post-period mean: "
        f"{design1['rows with a changed mean']} of {design1['rows']} "
        f"({design1['repositories with a changed mean']} repositories; at most "
        f"{design1['max relative change of a mean']:.1%} of the mean)\n"
        f"    tested p-values that move: {design1['tested p-values changed']} "
        f"(at most {design1['max p-value change']:.3f})\n"
        f"    rows in only one table: {design1['rows only in one table']}\n"
        f"    changes in significance after Benjamini-Hochberg or in testability: "
        f"{'; '.join(design1['significance changes']) or 'none'}\n\n"
        f"ANALYSIS_PLAN.sha256: {plan_ok}\n"
        "Per-file histories regenerated from the commit lists match the row counts of the "
        f"original runs: {'yes' if histories_match else 'no'}\n", encoding="utf-8")
    write_manifest()
    final, _ = check_identifiers(mapping, emails, [PKG / "PACKAGE_CHECKS.txt", PKG / "MANIFEST.txt"])
    print(f"  final scan of PACKAGE_CHECKS.txt and MANIFEST.txt: "
          f"{sum(len(v) for v in final.values())} hits")
    make_zip()

    files = [p for p in PKG.rglob("*") if p.is_file()]
    total = sum(p.stat().st_size for p in files)
    print(f"\n(c) {len(files)} files, {total / 1e6:.1f} MB unpacked, "
          f"{ZIP.stat().st_size / 1e6:.1f} MB zipped -> {ZIP.relative_to(ROOT)}")
    by_dir = {}
    for p in files:
        top = str(p.relative_to(PKG).parent)
        by_dir.setdefault(top, [0, 0])
        by_dir[top][0] += 1
        by_dir[top][1] += p.stat().st_size
    for top, (n, size) in sorted(by_dir.items()):
        print(f"  {top:<45} {n:>4} files  {size / 1e6:8.2f} MB")
    passed_final = all(not v for v in final.values())
    return 0 if passed_a and passed_final and d3_ok else 1


if __name__ == "__main__":
    sys.exit(main())
