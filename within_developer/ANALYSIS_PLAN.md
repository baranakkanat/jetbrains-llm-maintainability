# Pre-registered analysis plan — overnight run

Written 2026-11-02 04:50 CET, **before** any of the analyses below were run.
Results from the earlier run (2026-11-02 ~03:30 CET: commit size, comment
share, complexity added to modified methods, net complexity per 100 added
lines) are known and are only re-tested here as robustness checks (H4), not
as new hypotheses.

## Data

- Repositories: JetBrains/kotlin, JetBrains/intellij-scala, JetBrains/ideavim
  (the three sampled repositories with hundreds of AI-labelled commits).
- History: non-merge commits from 2025-01-01 to the clone date (2026-11-02).
- Groups: `pair` = human-authored commit with an AI co-author / "Generated
  with" trailer; `human` = unlabelled human commit; `agent` = commit authored
  by an AI bot account. Other bots are excluded.
- Production code: .kt/.kts/.java/.scala files outside test paths.
- Eligible developers (H1, H2, H4): at least 8 `pair` and 8 `human`
  production-code commits in the repository's AI-active months.

## Confirmatory hypotheses (two-sided, alpha = 0.05, Benjamini-Hochberg across H1, H2, H3a, H3b)

**H1 — Follow-up fixes.** For each production-code commit, outcome = 1 if any
later commit whose subject line matches fix keywords
(fix|fixes|fixed|bug|crash|regression|broken|revert) touches at least one of
the same production files within 30 days, else 0. Commits from the last 30
days of the data are excluded (incomplete follow-up). Model: linear
probability, `pair` + log(lines changed) + log(production files) + prior
30-day fix activity on the same files + author FE + repo-month FE; standard
errors clustered by author (Frisch-Waugh-Lovell).

**H2 — Reverts.** Outcome = 1 if a later commit reverts it (message contains
"This reverts commit <sha>" with its hash, or `Revert "<its subject>"`).
Same model as H1 without the prior-fix control; Fisher's exact test on the
pooled 2x2 table reported alongside because reverts are rare.

**H3 — Spillover (hidden AI use / learning).** Developers with at least 8
labelled commits and at least 20 production-code commits before their first
labelled commit ("adopters"), plus all other developers with at least 20
production-code commits ("non-adopters", who absorb the common time trend).
Indicator `post_unlabelled` = adopter's unlabelled commit after their first
labelled commit; `post_labelled` = adopter's labelled commit. Model:
outcome ~ post_unlabelled + post_labelled + log(lines changed) + author FE +
repo-month FE, clustered by author.
  - H3a outcome: comment share of added production lines.
  - H3b outcome: log(lines changed) (size control dropped).
  A positive `post_unlabelled` coefficient means unlabelled work drifts toward
  the labelled-AI profile after adoption.

## Robustness of the earlier findings (H4; not counted as new hypotheses)

For the four earlier outcomes, re-estimate the within-developer model with:
  (a) commit-type control (subject classified as fix / refactor / test /
      docs / build / feature / other);
  (b) same-file comparison: primary production file (most added lines) as
      an additional fixed effect;
  (c) Claude-labelled commits only as the `pair` group;
  (d) the 2025-01 → 2026-11 data (more pre-adoption human commits).
A finding is called robust if its sign is unchanged and its 95% CI excludes
zero in (a)-(d).

## Exploratory (reported separately, no confirmatory claims)

- Tool and model generation (Claude model families, Junie, Codex).
- Agent-bot commits vs human commits.
- Extension to JetBrains/intellij-community if it has enough labelled commits.

## Stopping rule

No outcomes, controls or exclusions are added to H1-H4 after results are
seen. Anything added later is listed under Exploratory with the reason.
