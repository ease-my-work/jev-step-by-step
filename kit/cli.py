"""Command-line flags shared by every step's run.py."""

import argparse


def parse_args(title: str, argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="run.py",
        description=f"Step {title} — JEV vs LLM-only on customer-support messages.",
        epilog="With no flags: pick a message from a list and watch both sides answer it.",
    )
    parser.add_argument("--mode", choices=["both", "jev", "llm"], default="both", help="which side(s) to run")
    parser.add_argument("--query", metavar="qNN", help="run one message by id, skipping the picker (e.g. q02)")
    parser.add_argument("--all", action="store_true", help="run every message for this step and print a summary")
    parser.add_argument("--replay", action="store_true", help="use recorded answers from fixtures/ (no API keys)")
    parser.add_argument("--record", action="store_true", help="save live answers to fixtures/ (maintainers)")
    parser.add_argument("--json", action="store_true", help="machine-readable output (with --query or --all)")
    args = parser.parse_args(argv)
    if args.replay and args.record:
        parser.error("--replay and --record can't be used together")
    if args.json and not (args.query or args.all):
        parser.error("--json needs --query or --all")
    return args
