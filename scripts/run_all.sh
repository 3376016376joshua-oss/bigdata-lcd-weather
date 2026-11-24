#!/usr/bin/env bash
# Run the whole study on NYU Dataproc, Phase 1 to Phase 6, one step after another.
#
#   bash scripts/run_all.sh        # every phase
#   bash scripts/run_all.sh 3      # start at Phase 3, when Phases 1-2 are already done
#
# Run it in the background, so closing the terminal does not stop it:
#   mkdir -p logs && nohup bash scripts/run_all.sh > logs/run_all.log 2>&1 &
#   tail logs/run_all.log
#
# Each step's full output goes to logs/<step>.log. The main output has one line per step
# with its start time and run time; a failed step prints the end of its log and stops the run.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

FIRST_PHASE="${1:-1}"
if [[ ! "$FIRST_PHASE" =~ ^[1-6]$ ]]; then
  echo "usage: $0 [first phase, 1-6]" >&2
  exit 2
fi
mkdir -p logs

# step <phase> <name> <command...>
step() {
  local phase="$1" name="$2"
  shift 2
  if ((phase < FIRST_PHASE)); then
    return 0
  fi
  local log="logs/$name.log" start=$SECONDS status=0
  echo "$(date '+%F %T') Phase $phase: $name (log: $log)"
  "$@" >"$log" 2>&1 || status=$?
  if ((status != 0)); then
    echo "FAILED: $name exited with $status after $((SECONDS - start)) s. End of $log:"
    tail -n 20 "$log"
    exit "$status"
  fi
  echo "    done in $((SECONDS - start)) s"
}

step 1 download_lcd python3 scripts/download_lcd.py
step 1 check_lcd python3 scripts/check_lcd.py
step 1 fetch_fivethirtyeight bash scripts/fetch_fivethirtyeight.sh
step 1 upload_hdfs bash scripts/upload_hdfs.sh
step 2 phase2_ingest bash scripts/run_phase2.sh
step 3 phase3_validate_profile bash scripts/run_phase3.sh
step 4 phase4_questions bash scripts/run_phase4.sh all
step 5 phase5_models bash scripts/run_phase5.sh
step 6 phase6_timing bash scripts/run_phase6_timing.sh
step 6 phase6_figures bash scripts/run_phase6_figures.sh

echo "$(date '+%F %T') All phases finished. Results are in results/, figures in figures/."
