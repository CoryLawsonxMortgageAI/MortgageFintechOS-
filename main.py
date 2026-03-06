#!/usr/bin/env python3
"""MortgageFintechOS — 24/7 Autonomous AI Operating System.

Entry point for the mortgage lending AI operating system.
Manages DIEGO, MARTIN, NOVA, and JARVIS agents.

Usage:
    python main.py start       Start the autonomous system
    python main.py status      Show system status
    python main.py health      Run health checks
    python main.py schedule    View scheduled tasks
    python main.py agents      List registered agents

Author: Cory Lawson / The Lawson Group
"""

import asyncio
import json
import sys

import click
import structlog

from config.settings import Settings
from core.orchestrator import Orchestrator

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
)

logger = structlog.get_logger()

# Shared orchestrator instance
_orchestrator: Orchestrator | None = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(Settings())
    return _orchestrator


@click.group()
@click.version_option(version="1.0.0", prog_name="MortgageFintechOS")
def cli():
    """MortgageFintechOS — 24/7 Autonomous AI Operating System for Mortgage Lending."""
    pass


@cli.command()
def start():
    """Start the autonomous AI operating system."""
    click.echo("=" * 60)
    click.echo("  MortgageFintechOS — Autonomous AI Operating System")
    click.echo("  Version 1.0.0 | Cory Lawson / The Lawson Group")
    click.echo("=" * 60)
    click.echo()
    click.echo("  Agents: DIEGO | MARTIN | NOVA | JARVIS")
    click.echo("  Mode:   24/7 Autonomous Operation")
    click.echo()
    click.echo("  Starting system...")
    click.echo()

    orchestrator = _get_orchestrator()

    try:
        asyncio.run(orchestrator.start())
    except KeyboardInterrupt:
        click.echo("\nShutdown requested. Stopping gracefully...")
        asyncio.run(orchestrator.stop())
        click.echo("System stopped.")


@cli.command()
def status():
    """Show current system status."""
    orchestrator = _get_orchestrator()
    orchestrator._register_default_agents()
    data = orchestrator.get_status()

    click.echo("=" * 60)
    click.echo("  MortgageFintechOS — System Status")
    click.echo("=" * 60)
    click.echo(f"  Running: {data['running']}")
    click.echo(f"  Uptime:  {data['uptime'] or 'Not started'}")
    click.echo()

    click.echo("  Queue:")
    for key, val in data.get("queue", {}).items():
        click.echo(f"    {key}: {val}")
    click.echo()

    click.echo("  Agents:")
    for name, info in data.get("agents", {}).items():
        click.echo(f"    {name}: {info['status']} | tasks={info['tasks_completed']} errors={info['error_count']}")


@cli.command()
def health():
    """Run health checks on all agents."""
    orchestrator = _get_orchestrator()
    orchestrator._register_default_agents()
    data = orchestrator.get_health()

    click.echo("=" * 60)
    click.echo("  MortgageFintechOS — Health Report")
    click.echo("=" * 60)
    click.echo(f"  Overall: {data.get('overall', 'unknown')}")
    click.echo()

    click.echo("  Agents:")
    for name, info in data.get("agents", {}).items():
        click.echo(f"    {name}: {info['status']}")
    click.echo()

    system = data.get("system", {})
    if system:
        click.echo("  System Metrics:")
        for key, val in system.items():
            click.echo(f"    {key}: {val}")


@cli.command()
def schedule():
    """View scheduled tasks."""
    orchestrator = _get_orchestrator()
    orchestrator._setup_schedule()
    jobs = orchestrator._scheduler.list_jobs()

    click.echo("=" * 60)
    click.echo("  MortgageFintechOS — Scheduled Tasks")
    click.echo("=" * 60)
    for job in jobs:
        schedule_str = ""
        if job.get("interval_minutes"):
            schedule_str = f"Every {job['interval_minutes']} minutes"
        elif job.get("day_of_week") is not None:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            schedule_str = f"{days[job['day_of_week']]} at {job['run_time']}"
        else:
            schedule_str = f"Daily at {job['run_time']}"

        status = "enabled" if job["enabled"] else "disabled"
        click.echo(f"  {job['name']:30s} {schedule_str:30s} [{status}]")


@cli.command()
def agents():
    """List all registered agents."""
    orchestrator = _get_orchestrator()
    orchestrator._register_default_agents()
    agent_list = orchestrator.list_agents()

    click.echo("=" * 60)
    click.echo("  MortgageFintechOS — Registered Agents")
    click.echo("=" * 60)
    click.echo()

    descriptions = {
        "DIEGO": "Pipeline Orchestration — loan triage, workflow management",
        "MARTIN": "Document Intelligence — OCR, classification, fraud detection",
        "NOVA": "Income & DTI — W-2 dual-method, Schedule C, risk scoring",
        "JARVIS": "Condition Resolution — LOE drafting, compliance citations",
    }

    for agent in agent_list:
        name = agent["name"]
        click.echo(f"  {name}")
        click.echo(f"    Role:   {descriptions.get(name, 'Unknown')}")
        click.echo(f"    Status: {agent['status']}")
        click.echo(f"    Tasks:  {agent['tasks_completed']} completed")
        click.echo(f"    Errors: {agent['error_count']}")
        click.echo()


if __name__ == "__main__":
    cli()
