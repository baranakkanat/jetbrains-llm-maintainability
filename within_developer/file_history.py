"""File-level commit history for the follow-up-fix (H1) and revert (H2) outcomes.

Reads `git log --numstat` (no file contents, so it runs in seconds) and writes:
  fh_<repo>_commits.csv : sha, date, author, subject, fix subject, reverted-by
  fh_<repo>_files.csv   : sha, path, added, deleted, production flag, rename_old
                          (a renamed file also gets a zero-line row for its old path)

Usage: python file_history.py <repo_path> <repo_name> [since]
"""

import re
import subprocess
import sys

import pandas as pd

CODE_EXT = (".kt", ".kts", ".java", ".scala")
TEST_PATH = re.compile(r"(^|/)(test|tests|testData|testdata|test-data|testSrc|testResources)(/|$)"
                       r"|Test[s]?\.(kt|kts|java|scala)$|Spec\.(kt|kts|scala)$")
FIX_SUBJECT = re.compile(r"\b(fix|fixes|fixed|fixing|bug|crash|regression|broken|revert|reverts)\b",
                         re.I)
REVERTS_SHA = re.compile(r"This reverts commit ([0-9a-f]{40})", re.I)
REVERT_SUBJECT = re.compile(r'^Revert "(.+)"\s*$')
START, BODY, END = "\x01", "\x02", "\x03"


def split_rename(path):
    """Resolve rename notation ('a/{x => y}/b' or 'x => y') to (old path, new path).

    The old path is None when the line is not a rename."""
    if " => " not in path:
        return None, path
    if "{" in path:
        old = re.sub(r"\{([^{}]*?) => [^{}]*?\}", r"\1", path).replace("//", "/")
        new = re.sub(r"\{[^{}]*? => ([^{}]*?)\}", r"\1", path).replace("//", "/")
        return old, new
    old, new = path.split(" => ", 1)
    return old, new


def main(repo_path, repo_name, since="2025-01-01"):
    fmt = f"{START}%H{BODY}%cI{BODY}%an{BODY}%B{END}"
    # Rename detection is pinned so the result does not depend on the global git config.
    # A date without a time makes git use the current time of day, so midnight is explicit.
    out = subprocess.run(["git", "-C", repo_path, "-c", "diff.renames=true",
                          "-c", "diff.renameLimit=1000", "log", "--no-merges", "-M",
                          f"--since={since} 00:00:00", "--numstat", f"--pretty=format:{fmt}"],
                         capture_output=True, text=True, errors="replace", check=True).stdout
    commits, files = [], []
    for block in out.split(START)[1:]:
        header, _, numstat = block.partition(END)
        parts = header.split(BODY, 3)
        if len(parts) != 4 or not re.fullmatch(r"[0-9a-f]{40}", parts[0]):
            # a control character inside a commit message split the record;
            # the remainder belongs to the previous commit and is skipped
            continue
        sha, date, author, message = parts
        subject = message.strip().splitlines()[0] if message.strip() else ""
        commits.append({"sha": sha, "date": date, "author": author, "subject": subject,
                        "fix_subject": bool(FIX_SUBJECT.search(subject)),
                        "reverts_sha": ";".join(REVERTS_SHA.findall(message)),
                        "reverts_subject": (REVERT_SUBJECT.match(subject).group(1)
                                            if REVERT_SUBJECT.match(subject) else "")})
        for line in numstat.strip().splitlines():
            parts = line.split("\t")
            if len(parts) != 3:
                continue
            added, deleted, path = parts
            old, path = split_rename(path)
            prod = path.endswith(CODE_EXT) and not TEST_PATH.search(path)
            files.append({"sha": sha, "path": path,
                          "added": int(added) if added.isdigit() else 0,
                          "deleted": int(deleted) if deleted.isdigit() else 0,
                          "prod": prod, "rename_old": False})
            if old is not None:
                # a rename touches the old path too; zero lines keep it out of the primary-file choice
                files.append({"sha": sha, "path": old, "added": 0, "deleted": 0,
                              "prod": old.endswith(CODE_EXT) and not TEST_PATH.search(old),
                              "rename_old": True})
    c = pd.DataFrame(commits)
    # Who reverted whom: by full hash, then by exact subject (unique earlier match).
    reverted_by = {}
    for _, r in c[c.reverts_sha != ""].iterrows():
        for target in r.reverts_sha.split(";"):
            reverted_by[target] = r.sha
    subj_index = c.groupby("subject").sha.apply(list).to_dict()
    for _, r in c[c.reverts_subject != ""].iterrows():
        targets = subj_index.get(r.reverts_subject, [])
        if len(targets) == 1 and targets[0] not in reverted_by:
            reverted_by[targets[0]] = r.sha
    c["reverted_by"] = c.sha.map(reverted_by).fillna("")
    c.to_csv(f"fh_{repo_name}_commits.csv", index=False)
    pd.DataFrame(files).to_csv(f"fh_{repo_name}_files.csv", index=False)
    print(f"[{repo_name}] {len(c)} commits, {len(files)} file rows, "
          f"{(c.reverted_by != '').sum()} reverted commits, {c.fix_subject.sum()} fix subjects")


if __name__ == "__main__":
    main(*sys.argv[1:])
