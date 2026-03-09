#!/bin/bash
# MortgageFintechOS — Claude Code SessionStart Hook
# Validates development environment on every session start

set -e

echo "============================================"
echo "  MortgageFintechOS — Environment Check"
echo "============================================"

# OS Detection
OS_TYPE="unknown"
case "$(uname -s)" in
    Linux*)
        if grep -qi microsoft /proc/version 2>/dev/null; then
            OS_TYPE="WSL"
        else
            OS_TYPE="Linux"
        fi
        ;;
    Darwin*) OS_TYPE="macOS" ;;
    MINGW*|MSYS*|CYGWIN*) OS_TYPE="Windows" ;;
esac
echo "  OS:      $OS_TYPE ($(uname -m))"

# Check Python
if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1)
    echo "  Python:  $PYVER"
elif command -v python &>/dev/null; then
    PYVER=$(python --version 2>&1)
    echo "  Python:  $PYVER"
else
    echo "  WARNING: Python not found in PATH"
fi

# Check .env
if [ -f ".env" ]; then
    echo "  Config:  .env found"
else
    echo "  WARNING: No .env file — run: cp .env.example .env"
fi

# Ensure data directories
for DIR in data data/health-alerts data/github-monitor data/quality-reports data/weekly-reviews; do
    [ -d "$DIR" ] || mkdir -p "$DIR"
done
echo "  Data:    data/ ready (4 report subdirectories)"

# RAM Check
if command -v free &>/dev/null; then
    RAM_FREE=$(free -m | awk '/^Mem:/ {print $7}')
    RAM_TOTAL=$(free -m | awk '/^Mem:/ {print $2}')
    RAM_PERCENT=$((100 - (RAM_FREE * 100 / RAM_TOTAL)))
    if [ "$RAM_FREE" -lt 4096 ]; then
        echo "  RAM:     WARNING — ${RAM_FREE}MB free / ${RAM_TOTAL}MB (${RAM_PERCENT}% used)"
    else
        echo "  RAM:     ${RAM_FREE}MB free / ${RAM_TOTAL}MB (${RAM_PERCENT}% used)"
    fi
fi

# Check key tools
if command -v ruff &>/dev/null; then
    echo "  Ruff:    $(ruff --version 2>&1)"
else
    echo "  Ruff:    Not installed (run: pip install ruff)"
fi

if command -v pytest &>/dev/null; then
    echo "  Pytest:  $(pytest --version 2>&1 | head -1)"
else
    echo "  Pytest:  Not installed (run: pip install pytest)"
fi

# Check git status
BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "  Branch:  $BRANCH"

# Check Docker and container status
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    CONTAINER_COUNT=$(docker ps -q 2>/dev/null | wc -l)
    echo "  Docker:  Running ($CONTAINER_COUNT containers)"
    # Check specific containers if any are running
    if [ "$CONTAINER_COUNT" -gt 0 ]; then
        for NAME in mortgagefintechos postgres redis; do
            STATUS=$(docker ps --filter "name=$NAME" --format "{{.Status}}" 2>/dev/null)
            if [ -n "$STATUS" ]; then
                echo "           - $NAME: $STATUS"
            fi
        done
    fi
else
    echo "  Docker:  Not running (optional)"
fi

# Check dashboard reachability
if command -v curl &>/dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 http://localhost:8080/api/healthz 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ]; then
        echo "  API:     Dashboard healthy (localhost:8080)"
    elif [ "$HTTP_CODE" != "000" ]; then
        echo "  API:     Dashboard returned HTTP $HTTP_CODE"
    else
        echo "  API:     Dashboard not reachable (optional)"
    fi
fi

echo "============================================"
echo "  MortgageFintechOS environment ready"
echo "============================================"
