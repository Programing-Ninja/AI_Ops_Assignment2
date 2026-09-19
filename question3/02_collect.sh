#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")"
mkdir -p evidence
python collect_results.py | tee evidence/results_table.txt
mv results.json evidence/results.json
