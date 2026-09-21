from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from farkad_ai.eval.replay import replay_fixtures
from farkad_ai.extraction.port import (
    ExtractionContext,
    ExtractionResult,
    Finding,
    PillarConfigProtocol,
    PillarExtractionPort,
)
from farkad_ai.logging import configure_logging
from farkad_ai.models.port import ModelPort
from farkad_ai.models.pricing import PRICES
from farkad_ai.models.recorded import RecordedModel
from farkad_ai.pipeline.observer import TraceObserver
from farkad_ai.pipeline.two_pass import build_pipeline
from farkad_ai.pipeline.types import CaptureProfileProtocol, CaptureRequest, Logged, NothingToLog
from farkad_ai.prompts import list_prompts
from farkad_ai.routing.pass_one import PillarRegistryProtocol, PillarSpecProtocol
from farkad_ai.routing.router import NotApplicable, Routed, Router, TrackingProfileProtocol
from farkad_ai.types import PipelineStep, Usage


@dataclass(frozen=True, slots=True)
class CliPillarSpec:
    pillar: str
    intent: str


@dataclass(frozen=True, slots=True)
class CliPillarConfig(PillarConfigProtocol):
    pillar: str


CLI_SPECS: tuple[CliPillarSpec, ...] = (
    CliPillarSpec("nutrition", "food, drinks, meals and calories"),
    CliPillarSpec("movement", "exercise, steps, runs and workouts"),
    CliPillarSpec("sleep", "sleep duration, quality and naps"),
    CliPillarSpec("supplements", "vitamins and supplements"),
    CliPillarSpec("drugs", "medications and pharmaceuticals"),
    CliPillarSpec("recovery", "sauna, cold plunge, massage and rest"),
)


class DefaultRegistry(PillarRegistryProtocol):
    def __init__(self) -> None:
        self._known = frozenset(s.pillar for s in CLI_SPECS)

    def __iter__(self) -> Iterator[PillarSpecProtocol]:
        return iter(CLI_SPECS)

    def knows(self, route: str) -> bool:
        return route in self._known


class AllowAllProfile(CaptureProfileProtocol, TrackingProfileProtocol):
    def restrict(self, pillars: frozenset[str]) -> frozenset[str]:
        return pillars

    def config_for(self, pillar: str) -> PillarConfigProtocol:
        return CliPillarConfig(pillar)


class CliExtractor(PillarExtractionPort):
    async def extract(self, context: ExtractionContext) -> ExtractionResult:
        usage = Usage(
            step=PipelineStep.extraction,
            model="cli-mock",
            prompt_version="v1",
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            cost_cents=Decimal("0.0"),
        )
        return ExtractionResult(
            pillar=context.config.pillar,
            entries=({"raw": context.transcript},),
            findings=(Finding(field="raw", reason="cli-pass"),),
            usage=usage,
        )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="farkad-ai", description="Farkad AI Engine")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")
    p.add_argument("--json-logs", action="store_true", help="Format logs as JSON")
    sub = p.add_subparsers(dest="command", required=True)

    for cmd, h in [("route", "Route capture"), ("extract", "Run two-pass pipeline")]:
        cp = sub.add_parser(cmd, help=h)
        cp.add_argument("--text", type=str, default="", help="Capture text")
        cp.add_argument(
            "--provider", choices=["recorded", "google", "anthropic", "openai"], default="recorded"
        )
        cp.add_argument("--fixtures", type=Path, help="Fixtures directory")

    eval_p = sub.add_parser("eval", help="Run evaluation harness over fixture captures")
    eval_p.add_argument(
        "--fixtures", type=Path, required=True, help="Directory or file containing eval captures"
    )
    sub.add_parser("models", help="List supported models and pricing")
    sub.add_parser("prompts", help="List active prompt assets and versions")
    return p


def resolve_model(args: argparse.Namespace) -> ModelPort:
    provider = getattr(args, "provider", "recorded")
    match provider:
        case "recorded":
            fixtures = getattr(args, "fixtures", None)
            if not fixtures:
                raise ValueError("Provider 'recorded' requires --fixtures <path>")
            return RecordedModel(Path(fixtures))
        case "google":
            from google import genai

            from farkad_ai.models.vertex import VertexModel

            return VertexModel(genai.Client())
        case "anthropic":
            import anthropic  # type: ignore[import-not-found]

            from farkad_ai.models.anthropic import AnthropicModel

            return AnthropicModel(anthropic.AsyncAnthropic())
        case "openai":
            import openai  # type: ignore[import-not-found]

            from farkad_ai.models.openai import OpenAIModel

            return OpenAIModel(openai.AsyncOpenAI())
        case _:
            raise ValueError(f"Unknown provider: {provider}")


def handle_route(args: argparse.Namespace) -> int:
    try:
        model = resolve_model(args)
    except Exception as error:
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


def handle_extract(args: argparse.Namespace) -> int:
    try:
        model = resolve_model(args)
    except Exception as error:
        sys.stderr.write(f"Error initializing model: {error}\n")
        return 1
    pipe = build_pipeline(model, DefaultRegistry(), CliExtractor(), observer=TraceObserver())
    outcome = asyncio.run(pipe.run(CaptureRequest(profile=AllowAllProfile(), text=args.text)))
    match outcome:
        case Logged():
            data = {
                "logged": True,
                "routes": sorted(outcome.routes),
                "extracted": [e.pillar for e in outcome.extracted],
            }
        case NothingToLog():
            data = {"logged": False, "reason": outcome.reason.value}
    sys.stdout.write(f"{json.dumps(data, indent=2)}\n")
    return 0


def handle_eval(args: argparse.Namespace) -> int:
    try:
        passed, total = replay_fixtures(args.fixtures)
    except (FileNotFoundError, ValueError) as error:
        sys.stderr.write(f"{error}\n")
        return 1
    pct = (passed / total) * 100.0 if total else 0.0
    sys.stdout.write(f"Eval completed: {passed}/{total} passed ({pct:.1f}%)\n")
    return 0


def handle_models(args: argparse.Namespace) -> int:
    sys.stdout.write(f"{'Model':<30} {'Input ($/M)':<12} {'Output ($/M)':<12} {'Retires':<12}\n")
    sys.stdout.write(f"{'-' * 30} {'-' * 12} {'-' * 12} {'-' * 12}\n")
    for name, price in sorted(PRICES.items()):
        retires = str(price.retires_on) if price.retires_on else "None"
        sys.stdout.write(
            f"{name:<30} {price.input_usd_per_million!s:<12} "
            f"{price.output_usd_per_million!s:<12} {retires:<12}\n"
        )
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
        case "extract":
            return handle_extract(args)
        case "eval":
            return handle_eval(args)
        case "models":
            return handle_models(args)
        case "prompts":
            return handle_prompts(args)
        case _:
            parser.print_help()
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
