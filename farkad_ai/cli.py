from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from farkad_ai.eval.run import RECORDINGS, evaluate, replace_recordings, report
from farkad_ai.examples import EXAMPLE_PILLARS, ExampleCatalogue
from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.recorded import RecordingModel
from farkad_ai.prompts import list_prompts
from farkad_ai.routing.router import NotApplicable, Routed, Router

CLI_PILLARS = frozenset(pillar.pillar for pillar in EXAMPLE_PILLARS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="farkad-ai", description="The AI engine behind Farkad")
    commands = parser.add_subparsers(dest="command", required=True)

    route = commands.add_parser("route", help="Name the topics one sentence mentions")
    route.add_argument("--text", type=str, default="", help="The sentence to route")
    add_provider(route)
    route.add_argument("--fixtures", type=Path, help="Replay answers recorded in this directory")

    scored = commands.add_parser(
        "eval", help="Score the example gold set: routing, fields and cost per language"
    )
    add_provider(scored)
    scored.add_argument(
        "--record", action="store_true", help="Replace the committed answers with this run's"
    )

    commands.add_parser("prompts", help="List active prompt assets and versions")
    return parser


def add_provider(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--provider",
        type=ProviderName,
        choices=list(ProviderName),
        default=ProviderName.recorded,
    )


def print_routing(args: argparse.Namespace) -> int:
    try:
        model = create_model(args.provider, fixtures_dir=args.fixtures)
    except (ValueError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    outcome = asyncio.run(Router(model, ExampleCatalogue()).route(CLI_PILLARS, text=args.text))
    match outcome:
        case Routed():
            answer = {
                "applicable": True,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "pillars": sorted(outcome.pillars),
                "mentions": {pillar: list(said) for pillar, said in outcome.mentions.items()},
            }
        case NotApplicable():
            answer = {
                "applicable": False,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "reason": outcome.reason.value,
            }
    sys.stdout.write(f"{json.dumps(answer, indent=2)}\n")
    return 0


def print_eval(args: argparse.Namespace) -> int:
    try:
        model = create_model(args.provider, fixtures_dir=RECORDINGS)
    except (ValueError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    if not args.record:
        sys.stdout.write(report(asyncio.run(evaluate(model))))
        return 0
    recorder = RecordingModel(model, RECORDINGS)
    run = asyncio.run(evaluate(recorder))
    sys.stdout.write(f"{report(run)}Recorded {replace_recordings(recorder)} answers\n")
    return 0


def print_prompts() -> int:
    for asset in list_prompts():
        sys.stdout.write(f"{asset.name:<15} (version: {asset.version}) [{len(asset.text)} chars]\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    match args.command:
        case "route":
            return print_routing(args)
        case "eval":
            return print_eval(args)
        case _:
            return print_prompts()
