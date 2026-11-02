#!/bin/sh
# Sensitivity run with the fixed mining code (*Test.kts as test code, old paths
# of renamed files kept, jetbrains-junie[bot] as agent, rename detection pinned).
# Reuses the clones in repos/ and writes everything to results_sensitivity/;
# results_overnight/ and the m2_/fh_ files next to this script are not touched.
set -e
cd "$(dirname "$0")"
mkdir -p results_sensitivity
cd results_sensitivity
for r in ideavim intellij-scala kotlin; do
  echo "$(date +%T) file history $r"
  python3 ../file_history.py "../repos/$r" "$r" 2025-01-01
  echo "$(date +%T) code metrics $r"
  python3 ../mine_commits.py "../repos/$r" "$r" "m2_$r.csv" 2025-01-01
done
echo "$(date +%T) analysis"
python3 ../analyze_overnight.py ideavim intellij-scala kotlin > analysis_output.txt 2>&1
echo "$(date +%T) SENSITIVITY DONE"
