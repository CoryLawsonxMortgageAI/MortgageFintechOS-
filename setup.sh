#!/bin/bash
# MortgageFintechOS Installation Script
# Author: Cory Lawson / The Lawson Group

set -e

APP_NAME="mortgagefintechos"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
VENV_DIR="${APP_DIR}/venv"

usage() {
    echo "MortgageFintechOS Setup"
    echo ""
    echo "Usage: $0 {install|configure|start|stop|status|logs}"
    echo ""
    echo "Commands:"
    echo "  install    Install Python dependencies and create venv"
    echo "  configure  Set up systemd service"
    echo "  start      Start the service"
    echo "  stop       Stop the service"
    echo "  status     Check service status"
    echo "  logs       View service logs"
}

install() {
    echo "Installing MortgageFintechOS..."

    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is required"
        exit 1
    fi

    echo "Creating virtual environment..."
    python3 -m venv "${VENV_DIR}"

    echo "Installing dependencies..."
    "${VENV_DIR}/bin/pip" install --upgrade pip
    "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"

    if [ ! -f "${APP_DIR}/.env" ]; then
        cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
        echo "Created .env from .env.example — please update with your settings"
    fi

    echo "Installation complete."
}

configure() {
    echo "Configuring systemd service..."

    sudo cp "${APP_DIR}/docker/mortgagefintechos.service" "${SERVICE_FILE}"
    sudo sed -i "s|/opt/mortgagefintechos|${APP_DIR}|g" "${SERVICE_FILE}"
    sudo systemctl daemon-reload
    sudo systemctl enable "${APP_NAME}"

    echo "Service configured and enabled."
}

do_start() {
    echo "Starting MortgageFintechOS..."
    sudo systemctl start "${APP_NAME}"
    echo "Started. Check status with: $0 status"
}

do_stop() {
    echo "Stopping MortgageFintechOS..."
    sudo systemctl stop "${APP_NAME}"
    echo "Stopped."
}

do_status() {
    sudo systemctl status "${APP_NAME}" --no-pager || true
}

do_logs() {
    sudo journalctl -u "${APP_NAME}" -f
}

case "${1:-}" in
    install)    install ;;
    configure)  configure ;;
    start)      do_start ;;
    stop)       do_stop ;;
    status)     do_status ;;
    logs)       do_logs ;;
    *)          usage ;;
esac
