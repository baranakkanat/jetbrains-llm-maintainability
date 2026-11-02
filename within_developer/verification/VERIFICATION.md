# Independent verification of selected within-developer numbers

Date: 2026-11-02. All code in this folder was written from scratch, using only
`ANALYSIS_PLAN.md`, the task's definitions, the CSV data files and `git` on the
three clones. None of the analysis scripts was opened or imported.

| Script | Produces |
|---|---|
| `common.py` | shared helpers: git log parsing, pair patterns, production-file rule |
| `a_pair_counts.py` | `a_pair_counts_output.txt`, `a_pair_commits_<repo>.csv` |
| `b_followup_scala.py` | `b_followup_scala_output.txt`, `b_followup_scala_commits.csv` |
| `c_dummy_regression.py` | `c_dummy_regression_output.txt` |

Run any of them with `.venv/bin/python3 within_developer/verification/<script>`.
Each one takes a few seconds.

Definitions used: the window starts at 2025-01-01 00:00:00 UTC on committer
time. Production files are `.kt/.kts/.java/.scala` outside directories named
`test, tests, testData, testdata, test-data, testSrc, testResources`, and the
file stem must not end in `Test/Tests/Spec`. Both rules are case-sensitive.

---

## (a) AI-co-authored ("pair") commit counts from plain `git log`

The count uses git's own grep (`-i -E`; the three `--grep` options are OR-ed):

```
TOOLS='(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|openai|anthropic|ai[ -]assistant|codex|junie)'
git -C repos/<repo> log --no-merges --since=2025-01-01T00:00:00Z -i -E \
  --grep="^[[:space:]]*co-authored-by:.*$TOOLS" \
  --grep="generated with \[[^]]*$TOOLS" \
  --grep="^[[:space:]]*assisted-by:.*$TOOLS" --format=%H | wc -l
```

I also ran the same grep without `--since` and filtered on `%ct` afterwards. The
counts were the same, so git's `--since` early stop did not lose any commits.
Python found the tool on the matching line. When one line names several tools,
the order is Junie > Codex > ... > Claude > OpenAI, so `Junie/Opus 5` counts as
Junie and `OpenCode with GPT-5.3 Codex <noreply@openai.com>` counts as Codex.
A commit counts as having a bot/agent author if the author name or e-mail
contains `[bot]`, or if the author name or e-mail local part is an agent name
(claude, copilot, junie, codex, cursor, ...).

### Fresh numbers

| | ideavim | intellij-scala | kotlin |
|---|---|---|---|
| git grep matches (all authors) | 500 | 358 | 1217 |
| of which bot/agent author | 174 (`claude[bot]`) | 0 | 1 (`Copilot`) |
| **pair** (match, non-bot author) | **326** | **358** | **1216** |
| pair by tool | Claude 324, Cursor 2 | Claude 228, Codex 129, Claude+Codex 1 | Claude 996, Junie 214, Codex 3, ChatGPT 3 |
| **pair touching >= 1 production file** | **151** | **239** | **864** |
| ... by tool | Claude 150, Cursor 1 | Claude 144, Codex 94, both 1 | Claude 707, Junie 155, Codex 1, ChatGPT 1 |
| which line matched | Co-authored-by 316, Co-authored-by + Generated with 184 | Co-authored-by 358 | Co-authored-by 1216, both 1 |

No commit matched only through `Assisted-by:`.

### Comparison with `m2_<repo>.csv`

| | ideavim | intellij-scala | kotlin |
|---|---|---|---|
| m2 `group == "pair"` | 326 | 361 | 1216 |
| m2 pair with `prod_files > 0` | 152 | 239 | 864 |
| pair SHAs: fresh-only / m2-only | 0 / 0 | 0 / 3 | 0 / 0 |
| pair-with-prod SHAs: fresh-only / m2-only | 0 / 1 | 0 / 0 | 0 / 0 |
| shared SHAs with a different prod-file count (old+new path / `-M` new path once) | 3 / 2 | 1 / 0 | 14 / 0 |

Why they differ, with examples:

* **intellij-scala, 3 m2-only pair commits.** None of them touches a production file.
  * `3cdab8c2d358dd687837b77449e83b3ce2375e8d` and `c6c0a408f6c88890644fc9066eb7b35cc8432266`
    have the characters `\n` typed as text in the message, so the trailer is part of
    a long line: `...builds.\n\nCo-authored-by: Codex <noreply@openai.com>`. A line-anchored
    trailer pattern cannot match. m2 is right about what the author meant; this is a
    definition edge case.
  * `ba65d98aa10f3231a0898953ea88cd7cd28aeac8` contains only the prose line "The code was
    generated with Claude Agent". This is neither a trailer nor `Generated with [<tool>]`,
    so m2's classifier is broader than the plan's definition here.
* **ideavim, `8595d53983a2584f8ae8ccdbad8c86f4fcc25fbd`**: m2 says prod_files = 1 and fresh says 0.
  The only code file is the deleted `.teamcity/patches/buildTypes/SlackNotificationTest.kts`.
  Its name ends in `Test` before the extension, so the plan calls it a test file.
  `fh_ideavim_files.csv` marks this path `prod=True`, but it marks `SlackNotificationTest.kt`
  `prod=False`. **The analysis' file-name test rule does not cover `.kts`.** In all three
  `fh_*_files.csv` files (187k distinct paths), my rule and the analysis' `prod` flag
  disagree only on this one path. `12b65fa17f32...` (5 vs 4) is the same file. Both commits
  are in `overnight_core_commits.csv`, and 8595d53983 should not be there at all, because
  it touches no production file.
* **Other prod-file count differences** (ideavim `bef0b4c32a`, intellij-scala `073bacb031`,
  14 kotlin commits) are all renames. With `--no-renames` I count both the old and the
  new path; m2 counts a rename once, under its new path. With `-M` and the new path counted
  once, every difference goes away except the `.kts` case. "Touches >= 1 production file"
  is the same either way.
* **Tool labels** on the shared SHAs agree except in 4 commits:
  * kotlin: 3 commits with `Co-authored-by: ChatGPT <noreply@openai.com>` are labelled
    `Codex` in m2.
  * ideavim: `858055c6e43c...` has only `Co-authored-by: Cursor`, but its subject is
    "Increase claude permissions..." and m2 labels it `tool=Claude, model=Cursor`. So m2
    seems to take the tool from anywhere in the message. This commit is not in the core
    sample.
  * intellij-scala: `f7cb017f23` has both a Codex and a Claude trailer; m2 labels it
    Claude.
* **Agent group (context).** m2's `agent` rows are the commits whose author is an AI
  account, whether or not they carry a trailer: ideavim 183 (`claude[bot]` 182, `Claude` 1),
  kotlin 14 (`Junie` 10, `Copilot` 3, `copilot-swe-agent[bot]` 1). My 174 and 1 count only
  the bot-authored commits that also match the trailer grep, so the two numbers measure
  different things. `jetbrains-junie[bot]` commits (2 in ideavim, 2 in intellij-scala) are
  missing from m2 altogether, as if they were "other bots", although Junie is an AI bot
  account and the plan says those commits are `agent`. This only matters for the
  exploratory agent comparison.

`llm_signals_summary.csv` (context only: all refs since 2021, narrower pattern list),
`AuthorshipCommits`: ideavim 531, intellij-scala 865, kotlin 1637. These are not expected
to match. They include history before 2025, other branches (for example intellij-scala
release-branch cherry-picks) and bot authors.

**Verdict (a): agree.** The pair SHA sets are identical in ideavim and kotlin. In
intellij-scala m2 has 3 extra pair commits: two with a literal `\n` before the trailer and
one with a free-text "generated with Claude Agent" line. None of the three touches
production code, so the pair-with-prod sets are identical there. The one real
discrepancy is the analysis treating `*Test.kts` as production code (1 path, 1 commit
wrongly in the core sample).

---

## (b) 30-day follow-up-fix rate, intellij-scala, recomputed from git

* **Population:** the 548 `intellij-scala` rows of `overnight_core_commits.csv` (human
  310, pair 238). Only `sha` and `group` were taken from the CSV; all 548 SHAs are in
  the clone.
* **Data:** all non-merge commits of the clone (4516), read with `git log --name-status -M`.
* **Eligibility:** committer time <= last committer time in the clone (2026-10-31 01:54:44 UTC)
  minus 30*86400 s, which gives a cut-off of 2026-10-01 01:54:44 UTC.
* **Outcome:** 1 if a commit with a strictly greater committer time, at most 30*86400 s
  later, whose subject matches `\b(fix|fixes|fixed|bug|crash|regression|broken|revert)\b`
  (case-insensitive), touches one of the commit's production paths.
* **Renames:** "touches" means the path appears as the old or the new side of a rename,
  or as an ordinary add, modify or delete. The commit's own production paths also
  include both sides of its renames.

| | fresh | analysis (CSV) |
|---|---|---|
| eligible, human | 285 | 285 |
| eligible, pair | 192 | 192 |
| eligibility agreement | 548 / 548 | |
| follow-up rate, human | **0.4316** (123/285) | **0.4281** (122/285) |
| follow-up rate, pair | **0.4010** (77/192) | **0.4010** (77/192) |
| commit-level agreement (CSV-eligible rows) | 476 / 477 | |

Variants (agreement with the CSV on the 477 eligible rows):

| variant | agree | fresh=1 & CSV=0 | fresh=0 & CSV=1 |
|---|---|---|---|
| primary (above) | 476 | 1 | 0 |
| `--no-renames` (a rename is a delete plus an add) | 476 | 1 | 0 |
| renames followed forward through intermediate commits | 476 | 1 | 0 |
| **a rename counts only under its new path** | **477** | 0 | 0 |
| keywords + `fixing`, `reverts` | 476 | 1 | 0 |
| same-second commits allowed (`>=` instead of `>`) | 462 | 15 | 0 |
| `< 30 d` instead of `<= 30 d` | 476 | 1 | 0 |

**The one disagreement:** `c2c1000e5229f85fee2cb69eac65ca6a4dabae7b` (human, 2026-08-10)
modifies `.../bazel/BazelScalaRunLineMarkerContributor.scala`. 2.7 days later,
`0997ac18e0cb...` ("[build] Fix compilation after the intellijVersion update to 263.3261")
renames that file to `BazelScalaRunConfigurationProducer.scala` and edits it (R063).
`fh_intellij-scala_files.csv` records that commit only under the new path, so the
analysis does not see that the fix touched the earlier commit's file. Counting renames
only under the new path reproduces the CSV exactly (477/477).

Adding `fixing` and `reverts` changes nothing. In the whole intellij-scala window only one
subject gains a match, and it is not a follow-up to any population commit. Strict `>`
on committer time matters: allowing same-second commits would add 15 follow-ups. The CSV
uses strict `>`, which matches the plan's "strictly later".

**Verdict (b): agree.** n per group and eligibility match exactly. The pair rate is
identical (0.4010). The human rate differs by one commit (0.4316 vs 0.4281) because of a
definition difference in rename handling: the analysis ignores the old path of a rename in
the follow-up commit. I think counting the old path is the more sensible reading. The
effect is tiny and would slightly widen the human-pair gap in this repository.

---

## (c) H4 base coefficients by explicit dummy-variable OLS

Data: `overnight_core_commits.csv`, rows with no missing values in the model columns.
The design is built with patsy, with full author and repo-month dummies. Authors are
nested in repositories, so treatment coding leaves 2 exactly collinear repo-month
dummies (`intellij-scala_2026-10`, `kotlin_2026-10`). I dropped them explicitly, because
statsmodels' pinv on the rank-deficient matrix gave a broken cluster SE (1221) for the
size model. Standard errors are clustered by author and were checked against a
hand-written sandwich estimator.

### `added_comment_share ~ is_pair + log_size + C(author) + C(repo_month)`

n = 4416, clusters = 19, K (rank, including dummies) = 46.

| | coef | SE | 95% CI | p |
|---|---|---|---|---|
| **fresh, CR1 = G/(G-1)*(N-1)/(N-K), K=46, t(18)** (Stata-style) | 0.051006 | 0.018718 | [0.011681, 0.090331] | 0.0139 |
| fresh, same CR1, normal | 0.051006 | 0.018718 | [0.014319, 0.087692] | 0.00643 |
| fresh, CR1 with K = 2 slope regressors only, normal | 0.051006 | 0.018624 | [0.014503, 0.087509] | 0.00616897 |
| **analysis (overnight_h4.csv, base)** | 0.051006 | 0.018624 (implied by p) | [0.014502, 0.087510] | 0.00616897 |

The coefficient difference is 3e-16.

### `log_size ~ is_pair + C(author) + C(repo_month)`

n = 4646, clusters = 19, K = 45.

| | coef | SE | 95% CI | p |
|---|---|---|---|---|
| **fresh, CR1 K=45, t(18)** | 0.505621 | 0.131352 | [0.229661, 0.781582] | 0.00117 |
| fresh, CR1 K=45, normal | 0.505621 | 0.131352 | [0.248176, 0.763067] | 0.000118 |
| fresh, CR1 with K = 1 slope regressor, normal | 0.505621 | 0.130728 | [0.249399, 0.761844] | 0.000109855 |
| **analysis (overnight_h4.csv, base)** | 0.505621 | 0.130728 (implied by p) | [0.249394, 0.761849] | 0.000109855 |

The coefficient difference is 4e-16.

To identify the analysis' SE, I compared its p-implied SE with CR0 x sqrt(G/(G-1) x
(N-1)/(N-K)). It matches when K is the number of non-absorbed slope regressors (2 and 1) and the
reference distribution is normal: the p-values agree to all printed digits. The CIs
differ only in the 6th decimal, which fits the analysis using z = 1.96 instead of
1.959964.
In other words, the cluster correction on the demeaned data does not count the absorbed
fixed effects in K. With dummies (K = 46 / 45) the SE is about 0.5% larger.

**Verdict (c): agree.** The coefficients are identical to machine precision, and n and the
clusters match. The SE differs by about 0.5% only because of the small-sample
degrees-of-freedom term.

A more important point: the analysis uses normal critical values with only 19 clusters.
With t(G-1 = 18), the usual small-G choice, the p-values roughly double:

* comment share: p 0.0062 -> 0.0139
* log size: p 0.00011 -> 0.0011

Both still exclude zero. I recomputed every `overnight_h4.csv` row under t(18) from its
implied SE. Only "Complexity added to modified methods, d_since_2025_01" flips: p 0.046 ->
0.061, and the CI then includes zero. That outcome already fails the robustness criterion
in variant (b), so no H4 robustness verdict changes. For the confirmatory hypotheses, H1
and H2 are null either way, and H3 has 114 clusters, so the reference distribution makes
no practical difference there.

---

## Issues that look like real (small) bugs rather than definition choices

1. **`*Test.kts` counts as production code.** The test-file-name rule misses `.kts`.
   This affects 1 path in ideavim (`.teamcity/patches/buildTypes/SlackNotificationTest.kts`)
   and puts 1 commit (`8595d53983`, pair) into the core sample even though it touches no
   production file. There is no effect in intellij-scala or kotlin.
2. **The old path of a renamed file is dropped** in the file-level history, so a fix
   commit that renames and edits a file does not count as touching it. This misses 1 of
   200 follow-ups in intellij-scala. It is arguably a definition choice, but it biases
   follow-up counts downward for files that get renamed.
3. **`jetbrains-junie[bot]` commits are dropped** (4 commits) instead of being labelled
   `agent`, which the plan's own definition would require. The confirmatory analyses are
   not affected.
4. Minor labelling quirks that do not change group membership: ChatGPT trailers are
   labelled Codex, and the tool is taken from a "claude" mention in the subject when the
   trailer says Cursor. The pair classifier also accepts free-text "generated with Claude
   Agent" and trailers behind a literal `\n`, which is broader than the plan's pattern
   (3 non-production commits).
