You are continuing an empirical software-engineering study in this repository
(jetbrains-llm-maintainability). Read README.md first, then this whole prompt
before doing anything.

## Rules (non-negotiable)

1. Everything written into code, scripts, comments, print statements, reports
   and commit messages is in English.
2. Never run `git push`. When work is ready, tell Baran; he pushes himself.
3. No AI attribution anywhere in git: no `Co-Authored-By` trailer, no
   "Generated with Claude Code" line, no AI author. Commit only as the
   repository's configured git user, with plain commit messages.
4. Work on a new local branch `within-developer`. Commit locally after each
   completed step so progress is never lost.
5. Do not modify `within_developer/ANALYSIS_PLAN.md`. It was written and hashed
   before any of its results were seen. Verify it first:
   `cd within_developer && shasum -a 256 -c ANALYSIS_PLAN.sha256`
   (the second line of that file is the timestamp, ignore it). Anything not in
   the plan is "exploratory" and is reported separately.
6. No result fishing: never add outcomes, controls or exclusions to the
   confirmatory tests after seeing results. Report null results as plainly as
   positive ones.
7. Do not delete or rewrite existing analysis files or results; add new files.
   You may append a section to README.md at the end.
8. Clones of other repositories go in `within_developer/repos/` (gitignored).
9. Keep `within_developer/PROGRESS.md` updated after every step (time, step,
   status, key numbers) so Baran can follow progress in the morning.

## State of the study

- Design 1 (date-based before/after) cannot attribute effects. In addition,
  explicit AI-authorship trailers in this sample only start in July 2025,
  after most of the "post-LLM" window, so design 1 cannot measure what it
  claims to measure.
- `llm_signals.csv` is stale: an older pattern set classified
  "Generated with [Claude Code]" commits as mention-only, which undercounts
  AI-authored commits about 2x (kotlin 485 vs 1,236 since mid-2025; ideavim
  281 vs 500). The current `llm_signal_mining.py` already matches these lines.
- New design 3 (within-developer): the same developer's AI-co-authored vs
  unlabelled production-code commits in the same months, with author and
  repo-month fixed effects. A first run on JetBrains/kotlin, intellij-scala and
  ideavim (commits 2025-06 to 2026-11): 20 developers, 5,781 commits (1,214
  AI-co-authored), SE clustered by author, Benjamini-Hochberg correction,
  leave-one-author-out sign stable 20/20:
  - commits about 1.65x larger (log lines changed +0.50, 95% CI 0.24 to 0.76)
  - comment share of added lines +5.3 percentage points (1.7 to 8.9); higher
    in 15 of 17 developers
  - complexity added to modified methods +0.13 per method (0.03 to 0.23)
  - net cyclomatic complexity per 100 added lines -42 (-69 to -16)
  - no difference: complexity of touched methods, complexity or length of new
    methods, touching tests, fix messages
  Files: `within_developer/results_2025-06/`.

## Handoff package

Unzip `~/Downloads/within_developer_handoff.zip` in the repository root so the
files land in `within_developer/` (ask Baran if the archive is elsewhere). It
contains mine_commits.py, file_history.py, analyze_pooled.py, robust_check.py,
analyze_overnight.py, exploratory.py, run_mining.sh, ANALYSIS_PLAN.md,
ANALYSIS_PLAN.sha256, results_2025-06/ and this prompt.

## Overnight tasks (in order)

Run long steps in the background with logs, and keep the Mac awake for their
duration, e.g. `caffeinate -i -w <pid>`. If a step fails, fix it and retry; if
it is blocked, record that in PROGRESS.md and continue with the next step.

0. Check free disk space (about 6 GB needed) and Python 3. Create or reuse a
   virtualenv and install: pydriller lizard pandas numpy scipy statsmodels
   matplotlib. Verify the plan hash.
1. Refresh the AI-signal mining: `python3 llm_signal_mining.py`. Commit the
   updated llm_signals.csv and llm_signals_summary.csv.
2. `cd within_developer && ./run_mining.sh > mining.log 2>&1` (clones
   ideavim, intellij-scala and kotlin with history from 2024-12-01, then writes
   fh_<repo>_*.csv and m2_<repo>.csv). kotlin is about 28k commits.
3. Pre-registered analysis:
   `python3 analyze_overnight.py ideavim intellij-scala kotlin`
   Save the full console output to `results_overnight/analysis_output.txt` and
   move the CSVs it writes (overnight_*.csv) into `results_overnight/`.
4. Exploratory: `python3 exploratory.py` (tool, Claude model family, model
   generation). Then, from the refreshed llm_signals_summary.csv, list other
   sampled repositories with at least 20 AI-authored commits; if any of them
   has developers with at least 8 AI-co-authored and 8 unlabelled production
   commits, mine them and report the results as exploratory.
5. Verification with fresh code (do not reuse the analysis functions):
   (a) count AI-co-authored commits per repository with plain `git log`;
   (b) recompute the 30-day follow-up-fix rate for unlabelled vs
       AI-co-authored commits in one repository;
   (c) re-estimate one H4 coefficient with an explicit dummy-variable
       regression instead of demeaning.
   Report agreement or disagreement with the main numbers.
6. Write `within_developer/REPORT.md`: data and window, plan hash, the
   confirmatory table (H1, H2, H3a, H3b with BH-adjusted p-values), the H4
   robustness verdicts, exploratory results clearly labelled as such,
   deviations from the plan with reasons, and limitations (AI labels are a
   lower bound, developers choose which tasks to delegate, JetBrains-only,
   lexical comment metric, lizard parsing). Add one coefficient plot (PNG)
   of the main within-developer effects with 95% CIs.
7. Append a short "Design 3: within-developer comparison" section to
   README.md that points to REPORT.md.
8. Commit locally (no attribution). Stop and write a summary for Baran: what
   was found, what is ready to push, open questions. Do not push.
