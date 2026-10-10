from __future__ import annotations

import pytest

import farkad_ai
from farkad_ai import CaptureEngine, CaptureRequest, PromptAsset, Router
from farkad_ai.memory.inference import InferredFacts, MemoryInferrer
from farkad_ai.routing.pass_one import Mention, PassOne
from tests.support import AnswersByStep, Registry, ScriptedModel, Spec, Tracked

OWN = PromptAsset(name="pass_one", text="Route this: {pillars}")


def test_every_public_name_imports_without_a_provider_sdk() -> None:
    assert all(hasattr(farkad_ai, name) for name in farkad_ai.__all__)


@pytest.mark.anyio
async def test_the_router_routes_with_the_prompt_it_is_given() -> None:
    model = ScriptedModel(
        PassOne(transcript="water", language="en", is_health_related=False, mentions=[])
    )
    await Router(model, Registry(Spec("water", "drinks")), instructions=OWN).route(
        frozenset({"water"}), text="water"
    )
    assert model.asked[0].instructions.startswith("Route this: - water: drinks")
    assert model.asked[0].instructions_version == OWN.version


@pytest.mark.anyio
async def test_memory_infers_with_the_prompt_it_is_given() -> None:
    own = PromptAsset(name="memory_inference", text="Known: {known}")
    model = ScriptedModel(InferredFacts(facts=[]))
    await MemoryInferrer(model, instructions=own).infer("I'm vegan", ())
    assert model.asked[0].instructions_version == own.version


@pytest.mark.anyio
async def test_the_engine_extracts_with_the_prompt_it_is_given() -> None:
    own = PromptAsset(name="extraction", text="{title}: {guidance} {examples} {log}")
    model = AnswersByStep(
        routing=PassOne(
            transcript="a glass",
            language="en",
            is_health_related=True,
            mentions=[Mention(pillar="water", said="a glass")],
        ),
        extraction={"entries": []},
    )
    engine = CaptureEngine(model, Registry(Spec("water", "drinks")), extraction_prompt=own)

    await engine.capture(CaptureRequest(tracked=(Tracked("water", title="Water"),), text="x"))

    extraction = model.asked[1][0]
    assert extraction.instructions.startswith("Water: Record each item.")
    assert extraction.instructions_version == own.version
