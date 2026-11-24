#!/usr/bin/env bash
# Phase 6: draw every figure from the result CSVs in results/ into figures/.
#
#   bash scripts/run_phase6_figures.sh
#
# Questions 1-6 write a PNG and an interactive HTML page per figure; questions 7-8, k-means
# and the run-time scaling write PNGs. Plotly and seaborn are installed for the current user
# when missing (the NYU Dataproc image has no Plotly).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/env.sh
source "$REPO_ROOT/scripts/env.sh"
cd "$REPO_ROOT"

if ! python3 -c "import plotly, seaborn" 2>/dev/null; then
  python3 -m pip install --user --quiet "plotly>=5.15" "seaborn>=0.12"
fi

FIGURE_SCRIPTS=(
  viz/q1_anomaly.py
  viz/q2_extremes.py
  viz/q3_balance.py
  viz/q4_cycles.py
  viz/q5_precipitation.py
  viz/q6_volatility.py
  viz/ml_regression.py
  viz/ml_classification.py
  viz/ml_kmeans.py
  viz/timing_scaling.py
)

mkdir -p "$LCD_FIGURES_DIR"
for script in "${FIGURE_SCRIPTS[@]}"; do
  echo "==> $script"
  python3 "$script" --results-dir "$LCD_RESULTS_DIR" --figures-dir "$LCD_FIGURES_DIR"
done
