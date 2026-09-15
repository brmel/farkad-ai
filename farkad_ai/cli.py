from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from farkad_ai.extraction.port import PillarConfigProtocol
from farkad_ai.models.port import ModelPort
from farkad_ai.models.recorded import RecordedModel
from farkad_ai.pipeline.types import CaptureProfileProtocol
from farkad_ai.routing.pass_one import PillarRegistryProtocol, PillarSpecProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router, TrackingProfileProtocol


@dataclass(frozen=True, slots=True)
class CliPillarSpec:
    pillar: str
    intent: str


@dataclass(frozen=True, slots=True)
class CliPillarConfig(PillarConfigProtocol):
    pillar: str


class DefaultRegistry(PillarRegistryProtocol):
    def __init__(self) -> None:
        self._specs: list[PillarSpecProtocol] = [
            CliPillarSpec("nutrition", "food, drinks, meals and calories"),
            CliPillarSpec("movement", "exercise, steps, runs and workouts"),
            CliPillarSpec("sleep", "sleep duration, quality and naps"),
            CliPillarSpec("supplements", "vitamins and supplements"),
            CliPillarSpec("drugs", "medications and pharmaceuticals"),
            CliPillarSpec("recovery", "sauna, cold plunge, massage and rest"),
        ]
        self._known = frozenset(s.pillar for s in self._specs)

    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(self._specs)

    def knows(self, route: str) -> bool:
        return route in self._known


class AllowAllProfile(CaptureProfileProtocol, TrackingProfileProtocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars

    def config_for(self, pillar: str) -> PillarConfigProtocol:
        return CliPillarConfig(pillar)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="farkad-ai",
        description="Farkad AI Engine - Independent AI Extraction and Routing Engine",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    route_parser = subparsers.add_parser("route", help="Route a capture through Pass One")
    route_parser.add_argument("--text", type=str, default="", help="Capture text")
    route_parser.add_argument("--fixtures", type=Path, help="Fixtures directory for RecordedModel")

    eval_parser = subparsers.add_parser("eval", help="Run evaluation harness")
    eval_parser.add_argument(
        "--fixtures", type=Path, required=True, help="Directory containing eval captures"
    )

    return parser


async def _route(model: ModelPort, text: str) -> int:
    registry = DefaultRegistry()
    router = Router(model, registry)
    profile = AllowAllProfile()
    outcome = await router.route(profile, text=text)
    match outcome:
        case Routed():
            data = {
                "applicable": True,
                "transcript": outcome.transcript,
                "language": outcome.language,
                "pillars": sorted(outcome.pillars),
                "untracked": sorted(outcome.untracked),
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


def handle_route(args: argparse.Namespace) -> int:
    fixtures_path: Path | None = args.fixtures
    if fixtures_path:
        model: ModelPort = RecordedModel(fixtures_path)
    else:
        sys.stderr.write("Live model not configured without GCP project. Provide --fixtures.\n")
        return 1
    return asyncio.run(_route(model, args.text))


def handle_eval(args: argparse.Namespace) -> int:
    fixtures_path: Path = args.fixtures
    if not fixtures_path.exists():
        sys.stderr.write(f"Fixtures path not found: {fixtures_path}\n")
        return 1
    sys.stdout.write(f"Evaluating captures in {fixtures_path}...\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    match args.command:
        case "route":
            return handle_route(args)
        case "eval":
            return handle_eval(args)
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
