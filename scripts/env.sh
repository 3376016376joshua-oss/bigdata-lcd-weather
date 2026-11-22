# Shared defaults for the Bash scripts. Source it, do not run it:
#   source "$(dirname "${BASH_SOURCE[0]}")/env.sh"
# Each value can be set in the environment beforehand, for example LCD_NETID=yw9614.
# src/lcdweather/config.py reads the same variables with the same defaults.

: "${LCD_NETID:=wl3564}"
: "${LCD_HDFS_ROOT:=hdfs:///user/${LCD_NETID}_nyu_edu/lcd}"
: "${LCD_HIVE_DB:=${LCD_NETID}_nyu_edu}"
: "${LCD_FIRST_YEAR:=2010}"
: "${LCD_LAST_YEAR:=2025}"
: "${LCD_BASE_URL:=https://www.ncei.noaa.gov/oa/local-climatological-data/v2/access}"
: "${LCD_LOCAL_RAW_DIR:=data/raw}"
: "${LCD_FIVETHIRTYEIGHT_DIR:=data/fivethirtyeight}"
: "${LCD_MANIFESTS_DIR:=manifests}"
: "${LCD_RESULTS_DIR:=results}"
: "${LCD_FIGURES_DIR:=figures}"

LCD_HDFS_ROOT="${LCD_HDFS_ROOT%/}"
LCD_BASE_URL="${LCD_BASE_URL%/}"

export LCD_NETID LCD_HDFS_ROOT LCD_HIVE_DB LCD_FIRST_YEAR LCD_LAST_YEAR LCD_BASE_URL
export LCD_LOCAL_RAW_DIR LCD_FIVETHIRTYEIGHT_DIR LCD_MANIFESTS_DIR LCD_RESULTS_DIR LCD_FIGURES_DIR
