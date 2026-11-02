# Overnight progress log

Branch: `within-developer` (local only, not pushed). Times are CET.

| Time | Step | Status | Key numbers / notes |
|---|---|---|---|
| 2026-11-02 04:58 | 0. Environment | done | 154 GiB free; Python 3.14.7; fresh `.venv` in the repository root with pydriller 2.12, lizard 1.24.3, pandas 3.1.0, numpy 2.5.4, scipy 1.18.1, statsmodels 0.15.0, matplotlib 3.11.2. `shasum -a 256 -c ANALYSIS_PLAN.sha256`: `ANALYSIS_PLAN.md: OK` (the warning about the timestamp line is expected). |
| 2026-11-02 05:00 | 1 + 2 started | running | Steps 1 and 2 are independent (step 1 reads only `sampled_repos.json`, step 2 only GitHub), so both run in the background at the same time under `caffeinate -i`. They are still committed in order. Logs: `within_developer/signal_mining.log`, `within_developer/mining.log`. |
| 2026-11-02 05:08 | 1. AI-signal refresh | done | 199/199 repositories scanned, all `ok`. AI-authored commits since 2021 (all refs): 3,336 (was 1,277); 28 repositories with any (was 24). kotlin 1,637 (was 485), intellij-scala 865 (was 386), ideavim 531 (was 281), intellij-community 95 (was 24), sbt-ide-settings 25, kotlin-web-site 24. First AI-authored commit 2025-07-10, last 2026-11-01. Mention-only fell from 2,507 to 593 as the "Generated with" lines moved to the authorship tier. Note: the script's authorship patterns do not name Junie or Codex, so trailers such as `Co-authored-by: Junie` are not counted here (Codex is caught through `openai` in its address); see step 5a. |
| 2026-11-02 05:08 | 2. Mining, attempt 1 | failed at kotlin | ideavim (2,288 commits mined in 67 s) and intellij-scala (4,388 in 162 s) done. kotlin clone fetched but checkout failed: the global git config names an LFS filter and `git-lfs` is not installed. Fix: in `repos/kotlin` only, set the LFS filter to pass-through in the local config and restore the checkout (kotlin's only LFS pattern is `*.jpg`, so no source file is affected). Log kept as `mining_attempt1.log`. |
| 2026-11-02 05:12 | 2. Mining, attempt 2 | running | `run_mining.sh` rerun from the start; existing clones are reused, ideavim and intellij-scala are re-mined from the same clones. |

## Script vs. plan, recorded before any result was seen (2026-11-02 05:00)

Reading `analyze_overnight.py` against `ANALYSIS_PLAN.md` before running it:

1. **H2 controls.** The plan says H2 uses "the same model as H1 without the
   prior-fix control", i.e. `pair + log(lines changed) + log(production files)`.
   The script controls for `log(lines changed)` only.
2. **H4 verdict.** The plan calls a finding robust if its sign is unchanged and
   its 95% CI excludes zero in variants (a)-(d). The script also requires the
   base variant to exclude zero and compares signs with the base variant
   rather than with the earlier run.
3. **Fix keywords.** The plan lists `fix|fixes|fixed|bug|crash|regression|broken|revert`;
   `file_history.py` also matches `fixing` and `reverts` (a superset).
4. **Winsorizing** of the two complexity outcomes at the 1st/99th percentile
   within repository is not in the plan; it is inherited from the earlier run.
5. **AI-active months** are the months with a labelled (`pair`) production
   commit; agent-bot commits do not define them (the earlier run used both).
6. **Inference** uses the normal approximation with about 20 clusters, which is
   somewhat anti-conservative.

Decision, fixed now: the script's output is reported as the confirmatory table
(as the handoff instructs). Next to it, H2 is re-estimated exactly as the plan
words it (with `log(production files)`), BH is recomputed for that family, and
the H4 verdict is also computed as the plan words it. If the two versions
disagree, the disagreement is reported; neither is chosen afterwards.
Items 3-6 are listed as deviations in the report without re-estimation.
