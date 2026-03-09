#!/bin/bash
# MortgageFintechOS — Shared Health Check Utility
# Usage: bash scripts/check-health.sh [--json]
# Exit codes: 0 = healthy, 1 = warning, 2 = critical

JSON_MODE=false
if [ "$1" = "--json" ]; then
    JSON_MODE=true
fi

EXIT_CODE=0
WARNINGS=()
CRITICALS=()

# --- System Resources ---
RAM_TOTAL=0
RAM_FREE=0
RAM_PERCENT=0
CPU_CORES=0
DISK_FREE=""

if command -v free &>/dev/null; then
    RAM_TOTAL=$(free -m | awk '/^Mem:/ {print $2}')
    RAM_FREE=$(free -m | awk '/^Mem:/ {print $7}')
    RAM_PERCENT=$((100 - (RAM_FREE * 100 / RAM_TOTAL)))
    if [ "$RAM_FREE" -lt 4096 ]; then
        WARNINGS+=("Low RAM: ${RAM_FREE}MB free of ${RAM_TOTAL}MB")
        [ "$EXIT_CODE" -lt 1 ] && EXIT_CODE=1
    fi
    if [ "$RAM_FREE" -lt 2048 ]; then
        CRITICALS+=("Critical RAM: ${RAM_FREE}MB free")
        EXIT_CODE=2
    fi
fi

CPU_CORES=$(nproc 2>/dev/null || echo "unknown")
DISK_FREE=$(df -h . 2>/dev/null | awk 'NR==2 {print $4}')

# --- Docker Containers ---
DOCKER_RUNNING=false
CONTAINERS=()
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    DOCKER_RUNNING=true
    while IFS= read -r line; do
        CONTAINERS+=("$line")
    done < <(docker ps --format "{{.Names}}:{{.Status}}" 2>/dev/null)
fi

# --- Dashboard API ---
DASHBOARD_STATUS="unreachable"
DASHBOARD_HEALTH=""
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 3 http://localhost:8080/api/healthz 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        DASHBOARD_STATUS="healthy"
        DASHBOARD_HEALTH=$(curl -s --connect-timeout 3 http://localhost:8080/api/health 2>/dev/null)
    elif [ "$HTTP_CODE" != "000" ]; then
        DASHBOARD_STATUS="error_${HTTP_CODE}"
        WARNINGS+=("Dashboard returned HTTP ${HTTP_CODE}")
        [ "$EXIT_CODE" -lt 1 ] && EXIT_CODE=1
    fi
fi

# --- Output ---
if [ "$JSON_MODE" = true ]; then
    # JSON output for machine consumption
    CONTAINER_JSON="[]"
    if [ ${#CONTAINERS[@]} -gt 0 ]; then
        CONTAINER_JSON="["
        for i in "${!CONTAINERS[@]}"; do
            NAME=$(echo "${CONTAINERS[$i]}" | cut -d: -f1)
            STATUS=$(echo "${CONTAINERS[$i]}" | cut -d: -f2-)
            [ "$i" -gt 0 ] && CONTAINER_JSON+=","
            CONTAINER_JSON+="{\"name\":\"${NAME}\",\"status\":\"${STATUS}\"}"
        done
        CONTAINER_JSON+="]"
    fi

    cat <<ENDJSON
{
  "status": "$([ "$EXIT_CODE" -eq 0 ] && echo "healthy" || ([ "$EXIT_CODE" -eq 1 ] && echo "warning" || echo "critical"))",
  "system": {
    "ram_total_mb": ${RAM_TOTAL},
    "ram_free_mb": ${RAM_FREE},
    "ram_percent": ${RAM_PERCENT},
    "cpu_cores": "${CPU_CORES}",
    "disk_free": "${DISK_FREE}"
  },
  "docker": {
    "running": ${DOCKER_RUNNING},
    "containers": ${CONTAINER_JSON}
  },
  "dashboard": "${DASHBOARD_STATUS}",
  "warnings": $(printf '%s\n' "${WARNINGS[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]"),
  "criticals": $(printf '%s\n' "${CRITICALS[@]}" | python3 -c "import sys,json; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")
}
ENDJSON
else
    # Human-readable output
    echo "============================================"
    echo "  MortgageFintechOS — Health Check"
    echo "============================================"
    echo "  RAM:       ${RAM_FREE}MB free / ${RAM_TOTAL}MB total (${RAM_PERCENT}% used)"
    echo "  CPU:       ${CPU_CORES} cores"
    echo "  Disk:      ${DISK_FREE} free"
    echo "  Docker:    $([ "$DOCKER_RUNNING" = true ] && echo "Running (${#CONTAINERS[@]} containers)" || echo "Not running")"
    if [ "$DOCKER_RUNNING" = true ] && [ ${#CONTAINERS[@]} -gt 0 ]; then
        for c in "${CONTAINERS[@]}"; do
            echo "             - $c"
        done
    fi
    echo "  Dashboard: ${DASHBOARD_STATUS}"
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        echo "  WARNINGS:"
        for w in "${WARNINGS[@]}"; do
            echo "    ! $w"
        done
    fi
    if [ ${#CRITICALS[@]} -gt 0 ]; then
        echo "  CRITICAL:"
        for c in "${CRITICALS[@]}"; do
            echo "    !! $c"
        done
    fi
    if [ "$EXIT_CODE" -eq 0 ]; then
        echo "  Status:    HEALTHY"
    fi
    echo "============================================"
fi

exit $EXIT_CODE
