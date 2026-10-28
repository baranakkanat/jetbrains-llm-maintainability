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
| Average lines changed per commit | Generation tendency | PyDriller |
| Bug-fix commit ratio | Maintainability | commit message keywords |
| Cyclomatic complexity | Maintainability | lizard |
| Average function length | Cognitive load | lizard |
| Deletion/addition ratio | Authorship signal | PyDriller |

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
| `before_after.py` | design 1: date-based before/after, FDR-corrected |
| `llm_signal_mining.py` | scans commit histories for assistant authorship trailers |
| `ai_vs_human.py` | design 2: within-repository AI vs human comparison |
| `fdr_correction.py` | applies BH correction to an existing results table |
| `analysis4.py` | legacy pipeline, kept for the time-series charts |
| `sampled_repos.json` | the 199 drawn repositories |
| `population_with_ids.json` | the 411 eligible repositories with their IDs |

### Running

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python3 llm_signal_mining.py     # minutes: blobless clones, commit metadata only
python3 before_after.py          # hours: full history mining, resumable via cache
python3 ai_vs_human.py           # hours, limited to repositories with labelled commits
```

`before_after.py` caches each repository's monthly aggregates under
`cache_monthly/`, so an interrupted run resumes instead of restarting.

---

## Reference

Capiluppi et al. (2026). *From Code Velocity to Complexity: Evidence on GitHub
Copilot's Role in Developer Productivity at ABN AMRO.* EASE 2026.
