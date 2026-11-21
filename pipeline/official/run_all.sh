#!/usr/bin/env bash
# Rebuild the official dataset from the raw PDFs/JSON in data/raw/. Stops at the first failure.
# Usage: bash pipeline/official/run_all.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
for step in extract_national extract_regional extract_motorcycle extract_causes map_regions \
            extract_estimates extract_census build_official publish_official; do
  echo "== $step"
  uv run -q python "pipeline/official/$step.py" | tail -3
done
