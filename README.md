# LLM Adoption and Code Maintainability in JetBrains Repositories

An empirical study of whether the adoption of LLM coding assistants is
associated with changes in maintainability proxies across JetBrains and
JetBrains-Research open-source repositories.

It replicates the before/after design of Capiluppi et al. (EASE 2026, ABN AMRO)
on a public corpus, and extends it with a within-repository comparison that the
original design cannot make.

---

## Research question

Does LLM tool adoption degrade the maintainability of code bases?

The hypothesis is stated negatively on purpose: the task is to find evidence
that would count against it, not to accumulate evidence for it.

---

## Sampling

| Step | Count |
|---|---|
| All public repositories in `JetBrains` and `JetBrains-Research` | 1049 |
| Non-fork, created before June 2021 (so a pre-LLM period exists) | 536 |
| Written in a language the metric tooling can parse | 411 |
| Drawn at random, 95% confidence / 5% margin of error | **199** |

Every eligible repository was assigned an integer ID (1–411); 199 IDs were
drawn with `random.seed(42)`, so the draw is reproducible. The population,
the IDs and the drawn sample are committed as `filtered_population.json`,
`population_with_ids.json` and `sampled_repos.json`.

Documentation, configuration and shell repositories are excluded because the
metrics below are undefined for them — a documented inclusion criterion, not a
post-hoc filter.

---

## Metrics

Six measures, computed per file or per commit and aggregated per repository-month.

| Metric | Attribute it proxies | Source |
|---|---|---|
| Comment density | Readability / documentation | `metrics.py` |
| Average lines changed per commit | Generation tendency | `git log --numstat`, every commit |
| Bug-fix commit ratio | Maintainability | commit message keywords, every commit |
| Cyclomatic complexity | Maintainability | lizard, sampled commits |
| Average function length | Cognitive load | lizard, sampled commits |
| Deletion/addition ratio | Authorship signal | `git log --numstat`, every commit |

`mine_fast.py` computes these from git directly instead of through PyDriller,
which re-parses every file of every commit and would take days on this sample.
The three commit-level metrics use every non-merge commit since 2019. The three
file-content metrics use a seeded random sample of up to 10 commits per
repository-month (up to 15 code files each); months with fewer commits use all
of them. On ideavim the line and bug-fix figures match PyDriller's month by
month.

Two measurement bugs were found and fixed; results produced before this point
are not comparable with results produced after it.

* **Comment density ignored block comments.** Only lines beginning with `//`
  were counted in Java and Kotlin, so every Javadoc and KDoc header was
  invisible. Since those are the dominant documentation style in this corpus,
  documentation was systematically undercounted. On a short Kotlin sample the
  old code reports 0.11 where the corrected code reports 0.56.
* **Complexity was computed for Python files only.** lizard raises a
  `RecursionError` on very large generated Kotlin files, and the earlier
  workaround was to restrict the metric to `.py`. The sample is 65 Kotlin /
  61 Java / 14 Python repositories, so the two complexity metrics rested on an
  unrepresentative slice. The restriction is replaced by an explicit size guard
  (skip files over 5000 lines or 400 KB, which are generated resource tables)
  and every language lizard supports is now measured.

---

## Statistics

* Mann-Whitney U, two-sided, on monthly values.
* Cohen's d with pooled standard deviation, reported for every comparison.
* **Benjamini-Hochberg FDR correction across every test performed.** With
  199 repositories and 6 metrics the design runs on the order of a thousand
  tests; at an uncorrected α = 0.05 roughly 50 of them are expected to come
  back "significant" from chance alone. Uncorrected counts are not reported as
  findings.
* A repository/metric pair is tested only when at least 6 monthly observations
  exist on each side of the window.
* Absolute change is reported alongside percentage change. Percentage change is
  suppressed when the pre-period baseline is near zero, because a comment
  density moving from 0.0002 to 0.10 renders as "+53696%" and that number
  describes the baseline, not the effect.

### How results are counted

The denominator is the **whole sample**, not the subset that reached
significance. "87% of repositories with significant findings support the
hypothesis" is circular: it selects on the outcome and then reports a rate
within the selection. The honest statement has the form *N of 199
repositories show a significant change consistent with degradation*.

---

## Two designs

### 1. Before/after by date — `before_after.py`

Pre-LLM period 2019 – June 2021, post-LLM period January 2023 – 2025, using
the GitHub Copilot preview and the ChatGPT release as reference points.

This design cannot attribute what it finds. Everything else that changed after
2022 moves the same metrics: team turnover, project maturity, release cadence,
and above all **survivorship** — repositories still active in 2023 are not a
random subset of repositories active in 2020. Treat its output as a
description of what changed, not as an effect of LLM adoption.

### 2. AI-assisted vs human commits — `ai_vs_human.py`

Some commits state their authorship directly:

```
Co-authored-by: GitHub Copilot <...>
Co-authored-by: <AI assistant> <...>
```

`llm_signal_mining.py` scans the commit history of every sampled repository for
these trailers. Where a repository has enough labelled and unlabelled commits
in the *same months*, `ai_vs_human.py` compares them. Team, codebase and period
are then held fixed and assistance is the thing that varies — the confound the
date-based design cannot remove.

A commit that merely mentions Copilot or OpenAI is talking about AI, not
written with it; only authorship trailers are counted.

This comparison is still observational. Developers choose which work to hand to
an assistant, so it measures the code that is produced with assistance, not the
effect of assistance on arbitrary code.

---

## Results: design 1 on all 199 repositories

Corrected measurements, post-LLM window capped at December 2025.

| | |
|---|---|
| Sampled repositories | 199 |
| With any commit since 2019 | 190 |
| Testable on at least one metric (6+ active months in both periods) | 64 |
| Repository/metric pairs tested | 330 |
| False positives expected at p < 0.05 | ~16 |
| Significant, uncorrected | 92 |
| Significant after Benjamini-Hochberg | 50, in 26 repositories |

On the three maintainability proxies (bug-fix ratio, cyclomatic complexity,
function length), 19 repositories changed significantly: 10 moved only towards
degradation, 7 only towards improvement, and 2 (intellij-plugin-verifier,
sbt-idea-plugin) moved both ways on different metrics. That makes **12 of 190
active repositories (6.3%) with at least one change towards degradation** and
**9 of 190 (4.7%) with at least one change towards improvement**.
Per metric the significant changes split both ways:

| Metric | Down | Up |
|---|---|---|
| Comment density | 4 | 7 |
| Lines per commit | 3 | 5 |
| Bug-fix ratio | 6 | 9 |
| Cyclomatic complexity | 4 | 1 |
| Function length | 2 | 4 |
| Deletion/addition ratio | 3 | 2 |

The data show no consistent, sample-wide degradation after 2022. The largest
single constraint is activity: two thirds of the sample had too few active
months after 2022 to be tested at all, which is the survivorship problem in
concrete form.

Figures are in `figures/`: `heatmap.png` (every significant effect),
`direction_summary.png` (per-metric counts over all 199), `trends.png` and
`trend_*.png` (cross-repository medians over time). The AI-authorship figure
is `ai_authorship.png` in the repository root, made by `ai_authorship_counts.py`
and `ai_authorship_chart.py` from default-branch history.

---

## Known limitations

1. **No causal claim.** Neither design randomises assistance.
2. **Selection into assistance.** Labelled commits are not a random sample of
   a developer's work.
3. **Labelling is a lower bound.** Most assisted commits carry no trailer, so
   the "human" group in design 2 certainly contains assisted work. This biases
   the comparison toward the null: a difference that survives is more likely
   real than inflated.
4. **Bug-fix ratio is keyword-based**, and measures whether a commit calls
   itself a fix — not whether the code it touched later needed fixing.
5. **Ecosystem bias.** One organisation, Kotlin/Java-dominated. Generalisation
   beyond JetBrains is not supported by this data.
6. **Comment density is lexical.** Comment markers inside string literals are
   counted. The bias applies equally to both periods being compared.

---

## Files

| File | Purpose |
|---|---|
| `metrics.py` | comment density and complexity, all languages, with size guards |
| `mine_fast.py` | mines the 199 repositories into monthly aggregates (`cache_monthly/`) |
| `before_after.py` | design 1: date-based before/after, FDR-corrected |
| `make_charts.py` | every figure in `figures/` |
| `before_after_table.csv` | every test, with Cohen's d and FDR-adjusted p-values |
| `llm_signal_mining.py` | scans commit histories for assistant authorship trailers |
| `ai_vs_human.py` | design 2: within-repository AI vs human comparison |
| `analysis4.py` | legacy pipeline; its charts used both measurement defects above |
| `sampled_repos.json` | the 199 drawn repositories |
| `population_with_ids.json` | the 411 eligible repositories with their IDs |

### Running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 llm_signal_mining.py     # minutes: blobless clones, commit metadata only
python3 mine_fast.py             # about an hour: shallow clones since 2019
python3 before_after.py          # seconds once cache_monthly/ is filled
python3 make_charts.py           # writes figures/
python3 ai_vs_human.py           # hours, limited to repositories with labelled commits
```

Both miners cache per repository, so an interrupted run resumes instead of
restarting.

---

## Reference

Capiluppi et al. (2026). *From Code Velocity to Complexity: Evidence on GitHub
Copilot's Role in Developer Productivity at ABN AMRO.* EASE 2026.

---

## Design 3: within-developer comparison

Design 2 compares labelled and unlabelled commits within a repository. Design 3
narrows that to the **same developer in the same months**: each developer's
AI-co-authored production-code commits against their own unlabelled ones, with
author and repository-month fixed effects and standard errors clustered by
author. It runs on the three sampled repositories with hundreds of labelled
commits (JetBrains/kotlin, intellij-scala, ideavim; 19 developers, 4,646
commits in the AI-active months December 2025 to October 2026, 1,204 of them
AI-co-authored). The analysis plan (`within_developer/ANALYSIS_PLAN.md`) was
fixed and hashed before H1-H3 were run.

In short: no detectable difference in follow-up fixes or reverts, though the
follow-up-fix interval is wide and reverts are rare; AI-co-authored commits
are about 1.66x larger, and that holds in every robustness variant (on the
same commits, so this is robustness to specification, not a replication);
their higher comment share and complexity differences lose significance in a
same-file comparison; and after adopting an assistant, developers'
unlabelled commits are smaller than the common trend predicts, which is
consistent with, but does not show, handing the larger tasks to the
assistant.

Data, confirmatory tests, robustness checks, exploratory results, deviations
from the plan and limitations: [`within_developer/REPORT.md`](within_developer/REPORT.md).
