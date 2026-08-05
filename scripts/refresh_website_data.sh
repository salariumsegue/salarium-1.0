#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source ./venv/bin/activate

SALARIUM_TRAINING_DATA_PATH="$PWD/data/processed/training_data_liquid500_model_safe_with_global_macro.csv" \
./venv/bin/python \
  scripts/generate_walkforward_scores.py \
  --estimators 100

./venv/bin/python \
  scripts/evaluate_walkforward_policies.py

./venv/bin/python \
  scripts/export_website_snapshot.py

echo "SALARIUM_WEBSITE_REFRESH=PASS"
