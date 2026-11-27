#!/usr/bin/env python3
"""Personal AI Workforce v9 — Interactive Agent CLI Launcher Entrypoint."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from demo import run_demo_simulation
from harness.env_loader import load_dotenv_file
from launcher import AGENT_PROFILES, launch_agent, validate_agent_available

try:
    from rich.console import Console
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

MENU_ROWS = [
    ("1", "opencode", "OpenCode CLI", "Open-source AI coding agent"),
    ("2", "claude", "Claude CLI", "Anthropic official CLI"),
    ("3", "qwen", "Qwen-CLI", "Alibaba Qwen coding agent"),
    ("4", "agy", "Agy (Antigravity)", "Antigravity CLI agent"),
    ("5", "demo", "Demo Simulation", "Local 4-Tier workflow demo"),
    ("q", "quit", "Quit", "Exit launcher"),
]


def show_menu() -> str:
    if HAS_RICH:
        console = Console()
        table = Table(title="Personal AI Workforce v9 — Agent CLI Launcher")
        table.add_column("#", style="bold cyan")
        table.add_column("Agent CLI", style="bold green")
        table.add_column("Status")
        table.add_column("Description")
        for key, slug, label, desc in MENU_ROWS:
            if slug in AGENT_PROFILES:
                ok = validate_agent_available(AGENT_PROFILES[slug])
                status = "[green]Installed[/]" if ok else "[yellow]Not Found[/]"
            else:
                status = "[cyan]Built-in[/]"
            table.add_row(key, label, status, desc)
        console.print(table)
        return console.input("[bold yellow]ရွေးချယ်ပါ (1-5/q): [/]").strip().lower()

    print("\n=== Personal AI Workforce v9 — Agent CLI Launcher ===")
    for key, slug, label, desc in MENU_ROWS:
        if slug in AGENT_PROFILES:
            status = "Installed" if validate_agent_available(AGENT_PROFILES[slug]) else "Not Found"
        else:
            status = "Built-in"
        print(f"  [{key}] {label:<18} ({status:<9}) — {desc}")
    return input("ရွေးချယ်ပါ (1-5/q): ").strip().lower()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Personal AI Workforce v9 CLI Launcher")
    parser.add_argument("--agent", choices=list(AGENT_PROFILES.keys()))
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Target existing project directory (Pattern B zero-pollution mode)",
    )
    parser.add_argument(
        "--create-branch",
        default=None,
        help="Optional new git branch to create in target workspace before launch",
    )
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).parent.resolve()
    load_dotenv_file(root / ".env")
    ws_root = args.workspace.resolve() if args.workspace else None

    if args.demo:
        return run_demo_simulation(root)
    if args.agent:
        return launch_agent(
            AGENT_PROFILES[args.agent],
            root,
            workspace_root=ws_root,
            create_branch=args.create_branch,
            dry_run=args.dry_run,
        )
    if os.getenv("AUTO_LAUNCH", "false").lower() == "true":
        default_agent = os.getenv("DEFAULT_AGENT", "opencode").lower()
        if default_agent in AGENT_PROFILES:
            return launch_agent(
                AGENT_PROFILES[default_agent],
                root,
                workspace_root=ws_root,
                create_branch=args.create_branch,
                dry_run=args.dry_run,
            )

    mapping = {"1": "opencode", "2": "claude", "3": "qwen", "4": "agy"}
    while True:
        choice = show_menu()
        if choice == "q":
            return 0
        if choice in mapping:
            return launch_agent(
                AGENT_PROFILES[mapping[choice]],
                root,
                workspace_root=ws_root,
                create_branch=args.create_branch,
                dry_run=args.dry_run,
            )
        if choice == "5":
            return run_demo_simulation(root)
        print("[!] မမှန်ကန်သော ရွေးချယ်မှု။ 1 မှ 5 သို့မဟုတ် q ကို ရွေးပါ။")


if __name__ == "__main__":
    sys.exit(main())
