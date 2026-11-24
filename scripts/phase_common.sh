# Shared by run_phase2.sh, run_phase3.sh, run_phase5.sh and run_phase6_timing.sh. Source it, do not run it.
# Loads the settings of scripts/env.sh and defines the helpers that package and submit a PySpark job.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck source=scripts/env.sh
source "$REPO_ROOT/scripts/env.sh"

: "${LCD_BEELINE_URL:=jdbc:hive2://localhost:10000}"
: "${LCD_SPARK_SUBMIT_OPTS:=}"
# The driver has to run on this node: it reads config/stations.csv from the repository, and
# the cluster default (cluster mode) would start it on a worker node that has no checkout.
SPARK_SUBMIT_MODE="--master yarn --deploy-mode client"
# NYU Dataproc limits each user to 3 GB of memory on the master node, where the client-mode
# driver runs, and kills the driver outright when it goes over (Phase 5 hit this with Spark's
# 2 GB default heap). So the driver gets 1 GB and keeps a short job history. The warehouse
# folder gives new Hive databases (the Phase 6 timing ones) an HDFS location; without it Spark
# asks the metastore for ./spark-warehouse in the checkout, which the metastore cannot create.
: "${LCD_SPARK_CLUSTER_OPTS:=--driver-memory 1g --conf spark.ui.retainedJobs=50 --conf spark.ui.retainedStages=50 --conf spark.sql.ui.retainedExecutions=20 --conf spark.eventLog.enabled=false --conf spark.sql.warehouse.dir=${LCD_HDFS_ROOT}/warehouse}"

PACKAGE_ZIP=""

# Zip src/lcdweather so the executors can import it; the zip is removed when the script exits.
build_package_zip() {
  local build_dir
  build_dir="$(mktemp -d)"
  PACKAGE_ZIP="$build_dir/lcdweather.zip"
  trap 'rm -rf "$(dirname "$PACKAGE_ZIP")"' EXIT
  (cd "$REPO_ROOT/src" && python3 -m zipfile -c "$PACKAGE_ZIP" lcdweather)
}

# submit_job <job file under jobs/> [job arguments...]
submit_job() {
  local job="$1"
  shift
  # LCD_SPARK_SUBMIT_OPTS is a list of extra spark-submit flags, so it is split on spaces.
  # It comes after SPARK_SUBMIT_MODE and LCD_SPARK_CLUSTER_OPTS so that its flags win, for
  # example --master local[2] or --driver-memory 2g.
  # shellcheck disable=SC2086
  spark-submit $SPARK_SUBMIT_MODE $LCD_SPARK_CLUSTER_OPTS $LCD_SPARK_SUBMIT_OPTS --py-files "$PACKAGE_ZIP" "$REPO_ROOT/jobs/$job" "$@"
}
