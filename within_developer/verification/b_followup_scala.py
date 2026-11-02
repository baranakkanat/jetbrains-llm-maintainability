"""(b) 30-day follow-up-fix outcome (H1) for intellij-scala, recomputed from git.

Population: rows of results_overnight/overnight_core_commits.csv with
repo == 'intellij-scala' (sha and group taken from the CSV, nothing else).
Eligibility and outcome are recomputed from the clone.

Run: .venv/bin/python3 within_developer/verification/b_followup_scala.py
Writes b_followup_scala_output.txt and b_followup_scala_commits.csv.
"""
import bisect
import collections
import os
import re

import pandas as pd

from common import HERE, WD, is_prod, log_records

REPO = "intellij-scala"
WIN = 30 * 86400
FIX_RE = re.compile(r"\b(fix|fixes|fixed|bug|crash|regression|broken|revert)\b", re.I)
FIX_RE_EXT = re.compile(r"\b(fix|fixes|fixed|fixing|bug|crash|regression|broken|revert|reverts)\b", re.I)
OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def load_commits(mode):
    """All non-merge commits of the clone, oldest first, with touched paths.

    mode 'M': rename detection on; a commit touches old AND new path of a rename.
    mode 'noM': --no-renames; a rename is a delete plus an add (same path sets).
    mode 'newpath': rename detection on; a rename touches only its NEW path
    (used to test whether this reproduces the CSV).
    """
    wf = "name-status-norenames" if mode == "noM" else "name-status-renames"
    recs = list(log_records(REPO, with_files=wf))
    recs.sort(key=lambda r: r["ct"])
    for r in recs:
        if mode == "newpath":
            r["paths"] = {f[2] for f in r["files"]}
        else:
            r["paths"] = {f[1] for f in r["files"]} | {f[2] for f in r["files"]}
        r["renames"] = [(f[1], f[2]) for f in r["files"] if f[0] == "R"]
    return recs


def build_index(recs):
    """path -> sorted list of (ct, idx) of commits touching the path."""
    idx = collections.defaultdict(list)
    for i, r in enumerate(recs):
        for p in r["paths"]:
            idx[p].append((r["ct"], i))
    return idx


def followup(c, recs, idx, fix_re, follow_renames=False, strict=True, inclusive=True):
    """1 if a strictly later commit (committer time) with a fix subject touches
    one of c's production files within 30 days.

    follow_renames: when an intermediate commit (after c, within the window)
    renames a tracked file, the new path is tracked too.
    """
    t0 = c["ct"]
    tracked = {p for p in c["paths"] if is_prod(p)}
    if not tracked:
        return None
    if follow_renames:
        # walk forward in time over the commits in [t0, t0+WIN], in order
        for r in recs_in_window(recs, t0):
            if r["sha"] == c["sha"]:
                continue
            if (r["ct"] > t0 if strict else r["ct"] >= t0) and r["paths"] & tracked and fix_re.search(r["subject"]):
                return 1
            for old, new in r["renames"]:
                if old in tracked:
                    tracked.add(new)
        return 0
    for p in tracked:
        for ct, i in idx.get(p, ()):
            if recs[i]["sha"] == c["sha"]:
                continue
            ok_t = (ct > t0 if strict else ct >= t0) and (ct - t0 <= WIN if inclusive else ct - t0 < WIN)
            if ok_t and fix_re.search(recs[i]["subject"]):
                return 1
    return 0


_CTS = None


def recs_in_window(recs, t0):
    global _CTS
    if _CTS is None or len(_CTS) != len(recs):
        _CTS = [r["ct"] for r in recs]
    i = bisect.bisect_left(_CTS, t0)
    j = bisect.bisect_right(_CTS, t0 + WIN)
    return recs[i:j]


def main():
    core = pd.read_csv(os.path.join(WD, "results_overnight", "overnight_core_commits.csv"))
    pop = core[core.repo == REPO][["sha", "group", "followup_fix", "followup_eligible", "prod_files"]].copy()
    say(f"population: {len(pop)} rows {pop.group.value_counts().to_dict()}")

    recs = load_commits("M")
    by_sha = {r["sha"]: r for r in recs}
    idx = build_index(recs)
    t_end = max(r["ct"] for r in recs)
    say(f"clone: {len(recs)} non-merge commits; last committer time {pd.to_datetime(t_end, unit='s', utc=True)}")
    say(f"eligibility cut-off (last ct - 30 days): {pd.to_datetime(t_end - WIN, unit='s', utc=True)}")

    missing = [s for s in pop.sha if s not in by_sha]
    say(f"population SHAs not found in clone: {len(missing)}")

    recs_n = load_commits("noM")
    by_sha_n = {r["sha"]: r for r in recs_n}
    idx_n = build_index(recs_n)

    recs_np = load_commits("newpath")
    by_sha_np = {r["sha"]: r for r in recs_np}
    idx_np = build_index(recs_np)

    rows = []
    for s, g in zip(pop.sha, pop.group):
        c = by_sha[s]
        rows.append(dict(
            sha=s, group=g, ct=c["ct"], subject=c["subject"],
            n_prod=len({p for p in c["paths"] if is_prod(p)}),
            eligible=c["ct"] <= t_end - WIN,
            fu=followup(c, recs, idx, FIX_RE),
            fu_norenames=followup(by_sha_n[s], recs_n, idx_n, FIX_RE),
            fu_newpath=followup(by_sha_np[s], recs_np, idx_np, FIX_RE),
            fu_follow=followup(c, recs, idx, FIX_RE, follow_renames=True),
            fu_ext=followup(c, recs, idx, FIX_RE_EXT),
            fu_ge=followup(c, recs, idx, FIX_RE, strict=False),
            fu_lt=followup(c, recs, idx, FIX_RE, inclusive=False),
        ))
    me = pd.DataFrame(rows)
    d = pop.merge(me, on=["sha", "group"])
    d.to_csv(os.path.join(HERE, "b_followup_scala_commits.csv"), index=False)

    say(f"prod-file count equal to CSV prod_files: {(d.n_prod == d.prod_files).sum()} / {len(d)}")
    say(f"eligibility agrees with CSV: {(d.eligible == d.followup_eligible).sum()} / {len(d)}; "
        f"fresh eligible {int(d.eligible.sum())}, CSV eligible {int(d.followup_eligible.sum())}")

    e = d[d.eligible]
    say("\nFresh follow-up-fix rate (fresh eligibility), primary definition:")
    for g, x in e.groupby("group"):
        say(f"  {g:6s} n={len(x):4d} rate={x.fu.mean():.4f} ({int(x.fu.sum())} with follow-up)")
    ce = d[d.followup_eligible]
    say("CSV follow-up-fix rate (CSV eligibility):")
    for g, x in ce.groupby("group"):
        say(f"  {g:6s} n={len(x):4d} rate={x.followup_fix.mean():.4f}")

    say("\nCommit-level agreement with CSV followup_fix (rows where CSV followup_eligible is True):")
    for col, label in [("fu", "primary (-M, path identity, >ct, <=30d)"),
                       ("fu_norenames", "--no-renames"),
                       ("fu_follow", "follow renames forward"),
                       ("fu_newpath", "renames count under new path only"),
                       ("fu_ext", "keywords + fixing, reverts"),
                       ("fu_ge", "same-second commits allowed (>=ct)"),
                       ("fu_lt", "window < 30d instead of <= 30d")]:
        agree = (ce[col] == ce.followup_fix).sum()
        f1c0 = int(((ce[col] == 1) & (ce.followup_fix == 0)).sum())
        f0c1 = int(((ce[col] == 0) & (ce.followup_fix == 1)).sum())
        rates = ce.groupby("group")[col].mean().round(4).to_dict()
        say(f"  {label:42s}: agree {agree}/{len(ce)}; fresh1/csv0 {f1c0}, fresh0/csv1 {f0c1}; rates {rates}")

    dis = ce[ce.fu != ce.followup_fix]
    say(f"\nDisagreements (primary): {len(dis)}")
    for _, r in dis.head(12).iterrows():
        say(f"  {r.sha[:10]} {r.group} fresh={r.fu} csv={r.followup_fix} ext={r.fu_ext} '{r.subject[:70]}'")
        c = by_sha[r.sha]
        for p in sorted(q for q in c["paths"] if is_prod(q)):
            for ct, i in idx.get(p, ()):
                f = recs[i]
                if 0 < ct - c["ct"] <= WIN and FIX_RE.search(f["subject"]):
                    st = [x for x in f["files"] if p in (x[1], x[2])]
                    say(f"      follow-up {f['sha'][:10]} after {(ct - c['ct']) / 86400:.1f} d, entry {st}, '{f['subject'][:60]}'")
    with open(os.path.join(HERE, "b_followup_scala_output.txt"), "w") as fh:
        fh.write("\n".join(OUT) + "\n")
    return d, recs, idx


if __name__ == "__main__":
    main()
