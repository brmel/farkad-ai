from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from farkad_ai.logging import configure_logging
from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.prompts import list_prompts
from farkad_ai.routing.pass_one import PillarRegistryProtocol, PillarSpecProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router, TrackingProfileProtocol


@dataclass(frozen=True, slots=True)
class CliPillarSpec:
    pillar: str
    intent: str


CLI_SPECS: tuple[CliPillarSpec, ...] = (
    CliPillarSpec("food", "meals, snacks and drinks that carry energy"),
    CliPillarSpec("water", "water, tea, black coffee and other drinks without energy"),
    CliPillarSpec("exercise", "workouts, sport, movement"),
    CliPillarSpec("sleep", "nights, naps and sleep quality"),
    CliPillarSpec("supplements", "vitamins, minerals, protein, creatine and the rest"),
    CliPillarSpec("drugs", "medications and pharmaceuticals"),
    CliPillarSpec("recovery", "sauna, cold plunge, breathwork and other deliberate recovery"),
)


class DefaultRegistry(PillarRegistryProtocol):
    def __init__(self) -> None:
        self._known = frozenset(s.pillar for s in CLI_SPECS)

    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(CLI_SPECS)

    def knows(self, route: str) -> bool:
        return route in self._known


class AllowAllProfile(TrackingProfileProtocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="farkad-ai", description="Farkad AI Engine")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")
    p.add_argument("--json-logs", action="store_true", help="Format logs as JSON")
    sub = p.add_subparsers(dest="command", required=True)

    route = sub.add_parser("route", help="Route capture")
    route.add_argument("--text", type=str, default="", help="Capture text")
    route.add_argument(
        "--provider",
        choices=[provider.value for provider in ProviderName],
        default=ProviderName.recorded,
    )
    route.add_argument("--fixtures", type=Path, help="Fixtures directory")

    sub.add_parser("prompts", help="List active prompt assets and versions")
    return p


def handle_route(args: argparse.Namespace) -> int:
    try:
        model = create_model(args.provider, fixtures_dir=args.fixtures)
    except (ValueError, ImportError) as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    outcome = asyncio.run(Router(model, DefaultRegistry()).route(AllowAllProfile(), text=args.text))
    match outcome:
        case Routed():
            data = {
                "applicable": True,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "pillars": sorted(outcome.pillars),
            }
        case NotApplicable():
            data = {
                "applicable": False,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "reason": outcome.reason.value,
            }
    sys.stdout.write(f"{json.dumps(data, indent=2)}\n")
    return 0


def handle_prompts(args: argparse.Namespace) -> int:
    for asset in list_prompts():
        sys.stdout.write(f"{asset.name:<15} (version: {asset.version}) [{len(asset.text)} chars]\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    log_level = logging.DEBUG if args.verbose else logging.INFO
    configure_logging(level=log_level, json_format=args.json_logs)
    match args.command:
        case "route":
            return handle_route(args)
        case "prompts":
            return handle_prompts(args)
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
