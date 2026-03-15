from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_bot.bots.paper_cex_swing import run_paper_cex_swing
from trading_bot.research.summary import summarize_records, write_summary


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

    summarize = subparsers.add_parser(
        "summarize-records",
        help="Summarize recorder output for a bot",
    )
    summarize.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Path to the records root directory",
    )
    summarize.add_argument(
        "--bot",
        required=True,
        help="Bot name under the records root",
    )
    summarize.add_argument(
        "--date",
        action="append",
        dest="dates",
        help="Date to summarize in YYYY-MM-DD format; repeatable",
    )
    summarize.add_argument(
        "--output",
        type=Path,
        help="Optional output path; prints JSON to stdout when omitted",
    )
    summarize.add_argument(
        "--format",
        choices=("json", "csv"),
        default="json",
        help="Output format when --output is provided",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run-paper-bot":
        run_paper_cex_swing(args.config)
        return 0
    if args.command == "summarize-records":
        result = summarize_records(args.root, args.bot, args.dates)
        if args.output is None:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        else:
            write_summary(result, args.output, args.format)
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
