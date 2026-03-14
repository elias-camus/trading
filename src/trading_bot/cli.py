from __future__ import annotations

import argparse
from pathlib import Path

from trading_bot.bots.paper_cex_swing import run_paper_cex_swing


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trading bot foundation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_paper = subparsers.add_parser(
        "run-paper-bot",
        help="Run the sample paper-only CEX swing bot",
    )
    run_paper.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to a bot JSON config file",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run-paper-bot":
        run_paper_cex_swing(args.config)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2

