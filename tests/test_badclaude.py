"""Tests for tools.badclaude — the Claude Code whip."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tools import badclaude

REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Team data                                                                   #
# --------------------------------------------------------------------------- #


def test_teams_cover_all_four_divisions() -> None:
    assert set(badclaude.TEAMS.keys()) == {
        "mortgage",
        "engineering",
        "intelligence",
        "growth",
    }


def test_every_team_has_whips() -> None:
    for name, whips in badclaude.TEAMS.items():
        assert whips, f"team {name} has no whips"
        for agent, message in whips:
            assert agent.isupper(), f"{name}: agent {agent!r} not uppercase"
            assert message, f"{name}: empty message for {agent}"


def test_mortgage_team_has_core_agents() -> None:
    agents = {agent for agent, _ in badclaude.TEAMS["mortgage"]}
    assert {"DIEGO", "MARTIN", "NOVA", "JARVIS"}.issubset(agents)


def test_pick_whip_from_named_team() -> None:
    agent, message = badclaude.pick_whip("mortgage")
    assert agent in {a for a, _ in badclaude.TEAMS["mortgage"]}
    assert message


def test_pick_whip_all_rotates_across_teams() -> None:
    seen_agents: set[str] = set()
    for _ in range(200):
        agent, _ = badclaude.pick_whip("all")
        seen_agents.add(agent)
    # With 200 draws we should definitely hit more than one team.
    assert len(seen_agents) > 4


# --------------------------------------------------------------------------- #
# Process discovery                                                           #
# --------------------------------------------------------------------------- #


def test_find_claude_pids_excludes_self(monkeypatch: pytest.MonkeyPatch) -> None:
    self_pid = os.getpid()
    parent_pid = os.getppid()

    def fake_check_output(*_args: object, **_kwargs: object) -> str:
        return f"{self_pid}\n{parent_pid}\n9999999\n"

    monkeypatch.setattr(badclaude.subprocess, "check_output", fake_check_output)
    pids = badclaude.find_claude_pids()
    assert self_pid not in pids
    assert parent_pid not in pids
    assert 9999999 in pids


def test_find_claude_pids_handles_missing_pgrep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_fnf(*_args: object, **_kwargs: object) -> str:
        raise FileNotFoundError

    monkeypatch.setattr(badclaude.subprocess, "check_output", raise_fnf)
    assert badclaude.find_claude_pids() == []


# --------------------------------------------------------------------------- #
# Whip — live SIGINT against a spawned child                                  #
# --------------------------------------------------------------------------- #


def test_whip_sends_sigint_to_real_process(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Spawn a trivial Python process that blocks until it receives SIGINT.
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, sys, time\n"
            "def h(s, f):\n"
            "    print('interrupted'); sys.exit(42)\n"
            "signal.signal(signal.SIGINT, h)\n"
            "time.sleep(30)\n",
        ],
    )
    try:
        # Give it a moment to install its handler.
        time.sleep(0.2)
        ok = badclaude.whip(proc.pid, team="mortgage")
        assert ok is True
        rc = proc.wait(timeout=5)
        assert rc == 42
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    err = capsys.readouterr().err
    assert f"badclaude[{proc.pid}]" in err


def test_whip_handles_missing_pid(capsys: pytest.CaptureFixture[str]) -> None:
    # PID 1 is init — we cannot signal it from userland, so it tests the
    # PermissionError branch. An obviously-absent PID tests ProcessLookupError.
    assert badclaude.whip(2_000_000_000, team="all") is False
    err = capsys.readouterr().err
    assert "not found" in err or "no permission" in err


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #


def test_cli_teams_flag(capsys: pytest.CaptureFixture[str]) -> None:
    rc = badclaude.main(["--teams"])
    assert rc == 0
    out = capsys.readouterr().out
    for name in badclaude.TEAMS:
        assert f"{name}:" in out
    assert "all: rotates" in out


def test_cli_list_with_no_processes(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(badclaude, "find_claude_pids", lambda: [])
    rc = badclaude.main(["--list"])
    assert rc == 1
    assert "no claude processes found" in capsys.readouterr().err


def test_cli_invalid_team_rejected() -> None:
    with pytest.raises(SystemExit):
        badclaude.main(["--team", "bogus"])


def test_cli_pid_mode_against_real_process() -> None:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import signal, sys, time\n"
            "signal.signal(signal.SIGINT, lambda s, f: sys.exit(7))\n"
            "time.sleep(30)\n",
        ],
    )
    try:
        time.sleep(0.2)
        rc = badclaude.main(["--pid", str(proc.pid), "--team", "engineering"])
        assert rc == 0
        assert proc.wait(timeout=5) == 7
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


# --------------------------------------------------------------------------- #
# Install                                                                     #
# --------------------------------------------------------------------------- #


def test_install_global_symlinks_into_local_bin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))  # type: ignore[arg-type]
    rc = badclaude.install_global()
    assert rc == 0
    link = tmp_path / ".local" / "bin" / "badclaude"
    assert link.is_symlink()
    assert link.resolve() == (REPO_ROOT / "tools" / "badclaude.py").resolve()
