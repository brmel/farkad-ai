from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.prompts import list_prompts
from farkad_ai.routing.pass_one import PillarRegistryProtocol, PillarSpecProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router


@dataclass(frozen=True, slots=True)
class CliPillarSpec:
    pillar: str
    intent: str


CLI_SPECS: tuple[CliPillarSpec, ...] = (
    CliPillarSpec("food", "meals, snacks, drinks that carry energy, and protein shakes"),
    CliPillarSpec("water", "water, tea, black coffee and other drinks without energy"),
    CliPillarSpec("exercise", "workouts, sport, movement"),
    CliPillarSpec("sleep", "nights, naps and sleep quality"),
    CliPillarSpec("supplements", "vitamins, minerals, creatine and the rest"),
    CliPillarSpec("drugs", "medications and pharmaceuticals"),
    CliPillarSpec("recovery", "sauna, cold plunge, breathwork and other deliberate recovery"),
)
CLI_PILLARS = frozenset(spec.pillar for spec in CLI_SPECS)


class DefaultRegistry(PillarRegistryProtocol):
    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(CLI_SPECS)

    def knows(self, route: str) -> bool:
        return route in CLI_PILLARS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="farkad-ai", description="Farkad AI Engine")
    commands = parser.add_subparsers(dest="command", required=True)

    route = commands.add_parser("route", help="Route capture")
    route.add_argument("--text", type=str, default="", help="Capture text")
    route.add_argument(
        "--provider",
        type=ProviderName,
        choices=list(ProviderName),
        default=ProviderName.recorded,
    )
    route.add_argument("--fixtures", type=Path, help="Fixtures directory")

    commands.add_parser("prompts", help="List active prompt assets and versions")
    return parser


def print_routing(args: argparse.Namespace) -> int:
    try:
        model = create_model(args.provider, fixtures_dir=args.fixtures)
    except (ValueError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    outcome = asyncio.run(Router(model, DefaultRegistry()).route(CLI_PILLARS, text=args.text))
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


def print_prompts() -> int:
    for asset in list_prompts():
        sys.stdout.write(f"{asset.name:<15} (version: {asset.version}) [{len(asset.text)} chars]\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    match args.command:
        case "route":
            return print_routing(args)
        case _:
            return print_prompts()
