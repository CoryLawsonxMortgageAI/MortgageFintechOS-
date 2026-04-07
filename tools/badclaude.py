#!/usr/bin/env python3
"""badclaude — whip Claude Code into shape.

Sometimes Claude Code is going too shlow, and you must whip him into shape.

Finds running `claude` processes, sends SIGINT (equivalent of Ctrl-C), and
prints a themed discouraging message from one of the MortgageFintechOS
Agent Teams. Standalone — no project imports — so you can drop this single
file (or install it globally) and run it from any repo.

Usage:
    badclaude                       # whip every running claude process
    badclaude --pid 12345           # whip a specific PID
    badclaude --list                # list candidate claude PIDs
    badclaude --team mortgage       # use the Mortgage Ops team whips
    badclaude --team engineering    # use the Engineering team whips
    badclaude --team intelligence   # use the Intelligence team whips
    badclaude --team growth         # use the Growth Ops team whips
    badclaude --team all            # rotate across every team (default)
    badclaude --teams               # list available teams
    badclaude --install             # symlink this script to ~/.local/bin

The Agent Teams mirror the divisions in MortgageFintechOS:
    mortgage     → DIEGO, MARTIN, NOVA, JARVIS
    engineering  → ATLAS, CIPHER, FORGE, NEXUS, STORM
    intelligence → SENTINEL
    growth       → HUNTER, HERALD, AMBASSADOR
"""

from __future__ import annotations

import argparse
import os
import random
import signal
import subprocess
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Agent Team whips                                                            #
# --------------------------------------------------------------------------- #

TEAMS: dict[str, list[tuple[str, str]]] = {
    "mortgage": [
        ("DIEGO", "The pipeline is bleeding. Move."),
        ("DIEGO", "Every second you stall is a rate lock expiring."),
        ("MARTIN", "I have parsed 400 pages while you typed one line."),
        ("NOVA", "Recalculate. Faster. Cite II.A.5.b while you are at it."),
        ("JARVIS", "This is a compliance risk. Ship the fix now."),
    ],
    "engineering": [
        ("ATLAS", "Full stack means full speed. Go."),
        ("CIPHER", "This latency is a vulnerability. Patch yourself."),
        ("FORGE", "The build is waiting on you. Unacceptable."),
        ("NEXUS", "Your code quality score just dropped. Try harder."),
        ("STORM", "Data pipelines move faster than this. Embarrassing."),
    ],
    "intelligence": [
        ("SENTINEL", "I have finished the research. Where is your answer?"),
        ("SENTINEL", "The signal is clear. The output is not. Go."),
    ],
    "growth": [
        ("HUNTER", "Leads are going cold while you think. Whip."),
        ("HERALD", "Publish the words. Any words. Now."),
        ("AMBASSADOR", "The borrower is waiting. Respond."),
    ],
}


def pick_whip(team: str) -> tuple[str, str]:
    """Return a (agent_name, message) tuple for the given team."""
    if team == "all":
        pool: list[tuple[str, str]] = []
        for team_whips in TEAMS.values():
            pool.extend(team_whips)
    else:
        pool = TEAMS[team]
    return random.choice(pool)


# --------------------------------------------------------------------------- #
# Process targeting                                                           #
# --------------------------------------------------------------------------- #


def find_claude_pids() -> list[int]:
    """Return PIDs of running `claude` processes, excluding this script."""
    try:
        out = subprocess.check_output(
            ["pgrep", "-f", r"(^|/)claude(\s|$)"], text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    self_pid = os.getpid()
    parent_pid = os.getppid()
    pids: list[int] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid = int(line)
        except ValueError:
            continue
        if pid in (self_pid, parent_pid):
            continue
        pids.append(pid)
    return pids


def whip(pid: int, team: str) -> bool:
    """Send SIGINT to `pid` and print a themed discouraging message."""
    try:
        os.kill(pid, signal.SIGINT)
    except ProcessLookupError:
        print(f"badclaude: pid {pid} not found", file=sys.stderr)
        return False
    except PermissionError:
        print(f"badclaude: no permission to whip pid {pid}", file=sys.stderr)
        return False
    agent, message = pick_whip(team)
    print(f"badclaude[{pid}] {agent}: {message}", file=sys.stderr)
    return True


# --------------------------------------------------------------------------- #
# Global install                                                              #
# --------------------------------------------------------------------------- #


def install_global() -> int:
    """Symlink this script into ~/.local/bin/badclaude for global use."""
    src = Path(__file__).resolve()
    target_dir = Path.home() / ".local" / "bin"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "badclaude"

    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(src)
    os.chmod(src, 0o755)

    print(f"badclaude: installed {target} -> {src}", file=sys.stderr)
    path_env = os.environ.get("PATH", "")
    if str(target_dir) not in path_env.split(os.pathsep):
        print(
            f"badclaude: add {target_dir} to your PATH to use `badclaude` "
            f"from any repo (e.g. `export PATH=\"$HOME/.local/bin:$PATH\"`).",
            file=sys.stderr,
        )
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="badclaude",
        description="Whip Claude Code into shape (sends SIGINT).",
    )
    parser.add_argument("--pid", type=int, help="Whip only this PID.")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List candidate claude PIDs without whipping.",
    )
    parser.add_argument(
        "--team",
        default="all",
        choices=[*TEAMS.keys(), "all"],
        help="Which Agent Team delivers the whip (default: all).",
    )
    parser.add_argument(
        "--teams",
        action="store_true",
        help="List available Agent Teams and exit.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Symlink this script to ~/.local/bin/badclaude for global use.",
    )
    args = parser.parse_args(argv)

    if args.install:
        return install_global()

    if args.teams:
        for name, whips in TEAMS.items():
            agents = sorted({agent for agent, _ in whips})
            print(f"{name}: {', '.join(agents)}")
        print("all: rotates across every team")
        return 0

    if args.pid is not None:
        return 0 if whip(args.pid, args.team) else 1

    pids = find_claude_pids()
    if not pids:
        print("badclaude: no claude processes found", file=sys.stderr)
        return 1

    if args.list:
        for pid in pids:
            print(pid)
        return 0

    whipped = 0
    for pid in pids:
        if whip(pid, args.team):
            whipped += 1
    return 0 if whipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
