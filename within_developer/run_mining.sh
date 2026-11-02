#!/bin/sh
# Clone (if needed) and mine the three repositories for the pre-registered analysis.
# Outputs in this folder: fh_<repo>_commits.csv, fh_<repo>_files.csv, m2_<repo>.csv
set -e
cd "$(dirname "$0")"
mkdir -p repos
for r in ideavim intellij-scala kotlin; do
  if [ ! -d "repos/$r" ]; then
    echo "$(date +%T) cloning $r"
    git clone --quiet --shallow-since=2024-12-01 "https://github.com/JetBrains/$r" "repos/$r"
  fi
  echo "$(date +%T) file history $r"
  python3 file_history.py "repos/$r" "$r" 2025-01-01
  echo "$(date +%T) code metrics $r"
  python3 mine_commits.py "repos/$r" "$r" "m2_$r.csv" 2025-01-01
done
echo "$(date +%T) ALL MINING DONE"
