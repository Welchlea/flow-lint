"""Command line entry point."""

from __future__ import annotations

import argparse

from .diagram import to_mermaid
from .lint import ERROR, has_errors, lint
from .model import load_flow
from .simulate import simulate


def _cmd_check(args) -> int:
    flow = load_flow(args.flow)
    issues = lint(flow, max_message_words=args.max_words)
    for issue in issues:
        print(issue)
    errors = sum(1 for i in issues if i.level == ERROR)
    warnings = len(issues) - errors
    if issues:
        print()
    print(f"{flow.name}: {len(flow.steps)} steps, {errors} errors, {warnings} warnings")
    if errors or (args.strict and warnings):
        return 1
    return 0


def _cmd_run(args) -> int:
    flow = load_flow(args.flow)
    transcript = simulate(flow, args.say or [])
    print(transcript.as_text())
    return 1 if transcript.outcome.startswith("broken") else 0


def _cmd_diagram(args) -> int:
    print(to_mermaid(load_flow(args.flow)))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flow-lint", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="find problems in a flow")
    check.add_argument("flow")
    check.add_argument("--strict", action="store_true", help="treat warnings as errors")
    check.add_argument("--max-words", type=int, default=40, help="word limit for one message")
    check.set_defaults(func=_cmd_check)

    run = sub.add_parser("run", help="walk through a flow with scripted answers")
    run.add_argument("flow")
    run.add_argument("--say", action="append", help="a user answer. Repeat for each question")
    run.set_defaults(func=_cmd_run)

    diagram = sub.add_parser("diagram", help="print the flow as a Mermaid diagram")
    diagram.add_argument("flow")
    diagram.set_defaults(func=_cmd_diagram)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
