#!/bin/bash
# MortgageFintechOS — Claude Code SessionStart Hook
# Validates development environment on every session start

set -e

echo "============================================"
echo "  MortgageFintechOS — Environment Check"
echo "============================================"

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

# Ensure data directory
if [ ! -d "data" ]; then
    mkdir -p data
    echo "  Data:    Created data/ directory"
else
    echo "  Data:    data/ exists"
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

# Check if Docker is running (optional)
if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
    echo "  Docker:  Running"
else
    echo "  Docker:  Not running (optional)"
fi

echo "============================================"
echo "  MortgageFintechOS environment ready"
echo "============================================"
