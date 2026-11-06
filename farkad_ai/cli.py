from __future__ import annotations

import argparse
import asyncio
import json
import sys
from enum import StrEnum

from farkad_ai.eval.example import RECORDINGS, evaluate_examples, report
from farkad_ai.eval.pillars import EXAMPLE_PILLARS
from farkad_ai.models.port import MissingCredentialsError, Model
from farkad_ai.models.recorded import NoRecordedResponseError, RecordedModel, RecordingModel
from farkad_ai.routing.port import NothingToLog, Routed
from farkad_ai.routing.router import Router

CLI_PILLARS = frozenset(pillar.pillar for pillar in EXAMPLE_PILLARS)


class ProviderName(StrEnum):
    vertex = "vertex"
    recorded = "recorded"


def _model_of(provider: ProviderName) -> Model:
    match provider:
        case ProviderName.vertex:
            from farkad_ai.models.vertex import VertexModel

            return VertexModel.connected()
        case ProviderName.recorded:
            return RecordedModel(RECORDINGS)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        model = _model_of(args.provider)
    except (MissingCredentialsError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    if args.command == "route":
        return _print_routing(model, args.text)
    return _print_eval(model, record=args.record)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="farkad-ai", description="The AI engine behind Farkad")
    commands = parser.add_subparsers(dest="command", required=True)

    route = commands.add_parser("route", help="Name the topics one sentence mentions")
    route.add_argument("--text", required=True, help="The sentence to route")
    _add_provider(route)

    scored = commands.add_parser(
        "eval", help="Score the example gold set: routing, fields and tokens per language"
    )
    _add_provider(scored)
    scored.add_argument(
        "--record", action="store_true", help="Replace the committed answers with this run's"
    )
    return parser


def _add_provider(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--provider",
        type=ProviderName,
        choices=list(ProviderName),
        default=ProviderName.recorded,
    )


def _print_routing(model: Model, text: str) -> int:
    try:
        outcome = asyncio.run(Router(model, EXAMPLE_PILLARS).route(CLI_PILLARS, text=text))
    except NoRecordedResponseError:
        sys.stderr.write(
            "Only the gold set's sentences are recorded: route another with --provider vertex\n"
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


def _print_eval(model: Model, *, record: bool) -> int:
    if not record:
        sys.stdout.write(report(asyncio.run(evaluate_examples(model))))
        return 0
    recorder = RecordingModel(model, RECORDINGS)
    run = asyncio.run(evaluate_examples(recorder))
    sys.stdout.write(f"{report(run)}Recorded {recorder.commit()} answers\n")
    return 0
