from __future__ import annotations

import argparse
import asyncio
import json
import sys

from farkad_ai.eval.example import RECORDINGS, evaluate_examples, report
from farkad_ai.eval.pillars import EXAMPLE_PILLARS
from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.port import Model
from farkad_ai.models.provider import MissingCredentialsError
from farkad_ai.models.recorded import NoRecordedResponseError, RecordingModel
from farkad_ai.prompts import list_prompts
from farkad_ai.routing.port import NothingToLog, Routed
from farkad_ai.routing.router import Router

CLI_PILLARS = frozenset(pillar.pillar for pillar in EXAMPLE_PILLARS)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "prompts":
        return print_prompts()
    try:
        model = create_model(args.provider, fixtures_dir=RECORDINGS)
    except (MissingCredentialsError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    if args.command == "route":
        return print_routing(model, args.text)
    return print_eval(model, record=args.record)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="farkad-ai", description="The AI engine behind Farkad")
    commands = parser.add_subparsers(dest="command", required=True)

    route = commands.add_parser("route", help="Name the topics one sentence mentions")
    route.add_argument("--text", type=str, default="", help="The sentence to route")
    add_provider(route)

    scored = commands.add_parser(
        "eval", help="Score the example gold set: routing, fields and tokens per language"
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


def print_routing(model: Model, text: str) -> int:
    try:
        outcome = asyncio.run(Router(model, EXAMPLE_PILLARS).route(CLI_PILLARS, text=text))
    except NoRecordedResponseError:
        sys.stderr.write(
            "Only the gold set's sentences are recorded: route another with "
            "--provider vertex, openai or anthropic\n"
        )
        return 1
    match outcome:
        case Routed():
            answer = {
                "applicable": True,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "pillars": sorted(outcome.routes),
                "mentions": {pillar: list(said) for pillar, said in outcome.mentions.items()},
            }
        case NothingToLog():
            answer = {
                "applicable": False,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "reason": outcome.reason.value,
            }
    sys.stdout.write(f"{json.dumps(answer, indent=2)}\n")
    return 0


def print_eval(model: Model, *, record: bool) -> int:
    if not record:
        sys.stdout.write(report(asyncio.run(evaluate_examples(model))))
        return 0
    recorder = RecordingModel(model, RECORDINGS)
    run = asyncio.run(evaluate_examples(recorder))
    sys.stdout.write(f"{report(run)}Recorded {recorder.commit()} answers\n")
    return 0


def print_prompts() -> int:
    for asset in list_prompts():
        sys.stdout.write(f"{asset.name:<15} (version: {asset.version}) [{len(asset.text)} chars]\n")
    return 0
