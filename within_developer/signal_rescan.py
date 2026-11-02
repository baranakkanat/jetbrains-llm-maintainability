"""Exploratory rescan of the 199 sampled repositories with the fuller AI-authorship patterns.

../llm_signal_mining.py does not name Junie or Codex in its authorship
patterns (Codex is caught only through an openai address). This runs that
script unchanged except for the authorship patterns, which are replaced by the
ones mine_commits.py uses for the `pair` group, and the output paths, so the
committed llm_signals*.csv stay as they are.

Outputs: results_exploratory/llm_signals_full_patterns.csv
         results_exploratory/llm_signals_full_patterns_summary.csv

Usage (from within_developer/): python signal_rescan.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.abspath(".."))
import llm_signal_mining as lsm  # noqa: E402

TOOLS = r"(copilot|chatgpt|claude|cursor|codeium|tabnine|gemini|openai|anthropic|ai-assistant|codex|junie)"
FULL_PATTERNS = {
    "coauthor_trailer": re.compile(r"co-?authored-by:[^\n]*" + TOOLS, re.I),
    "generated_with": re.compile(r"generated\s+with\s+\[?(claude|copilot|chatgpt|cursor|codex|junie)", re.I),
    "assisted_by_trailer": re.compile(r"assisted-by:[^\n]*(copilot|claude|chatgpt|codex|junie)", re.I),
}


def main():
    lsm.AUTHORSHIP_PATTERNS = FULL_PATTERNS
    lsm.SAMPLE_FILE = "../sampled_repos.json"
    lsm.DETAIL_OUT = "results_exploratory/llm_signals_full_patterns.csv"
    lsm.SUMMARY_OUT = "results_exploratory/llm_signals_full_patterns_summary.csv"
    lsm.main()


if __name__ == "__main__":
    main()
