# JetBrains LLM Maintainability Study

An empirical study analyzing the impact of LLM tool adoption on code maintainability across JetBrains open-source repositories.

## Research Question
Do LLMs degrade the maintainability of code bases?

## Hypothesis
LLM tool adoption is associated with measurable changes in code maintainability metrics, using GitHub Copilot (Jun 2021) and ChatGPT (Nov 2022) as reference points.

## Repositories Analyzed (20)

### Group 1: Static Analysis and Code Quality
astminer, refactorinsight, kotlin-ref-miner, code-change-miner, bug-finder, buckwheat, authorship-detection, kotlinRMiner

### Group 2: AI and ML Research
reflekt, commit_message_generation, washu, codetracker, formal-lang-course

### Group 3: Developer Tools and Infrastructure
compose-multiplatform, educational-plugin, intellij-plugins, markdown, ideavim, plugin-utilities, spla

## Metrics

| Metric | Attribute | Tool |
|---|---|---|
| Comment Density | Readability | PyDriller |
| Avg Lines per Commit | LLM Generation Tendency | PyDriller |
| Bug-Fix Commit Ratio | Maintainability | PyDriller |
| Cyclomatic Complexity | Maintainability | lizard |
| Avg Function Length | Maintainability | lizard |
| Deletion/Addition Ratio | LLM Authorship Signal | PyDriller |

## Statistical Analysis
Before/after comparison using Mann-Whitney U test (p < 0.05).
Pre-LLM period: 2019 to Jun 2021
Post-LLM period: Jan 2023 to 2025

## How to Run

    python3 -m venv .venv
    source .venv/bin/activate
    pip install pydriller matplotlib pandas lizard scipy
    python3 analysis4.py
    python3 before_after_table.py

## References
Capiluppi et al. (2026). From Code Velocity to Complexity: Evidence on GitHub Copilot's Role in Developer Productivity at ABN AMRO. EASE 2026.
