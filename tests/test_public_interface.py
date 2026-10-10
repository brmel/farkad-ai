from __future__ import annotations

import pytest

import farkad_ai
from farkad_ai import PromptAsset, Router
from farkad_ai.memory.inference import InferredFacts, MemoryInferrer
from farkad_ai.routing.pass_one import PassOne
from tests.support import Profile, Registry, ScriptedModel, Spec

OWN = PromptAsset(name="pass_one", text="Route this: {pillars}")


def test_every_public_name_imports_without_a_provider_sdk() -> None:
    assert all(hasattr(farkad_ai, name) for name in farkad_ai.__all__)


@pytest.mark.anyio
async def test_the_router_routes_with_the_prompt_it_is_given() -> None:
    model = ScriptedModel(
        PassOne(transcript="water", language="en", is_health_related=False, mentions=[])
    )
    await Router(model, Registry(Spec("water", "drinks")), instructions=OWN).route(
        Profile("water"), text="water"
    )
    assert model.asked[0].instructions.startswith("Route this: - water: drinks")
    assert model.asked[0].instructions_version == OWN.version


@pytest.mark.anyio
async def test_memory_infers_with_the_prompt_it_is_given() -> None:
    own = PromptAsset(name="memory_inference", text="Known: {known}")
    model = ScriptedModel(InferredFacts(facts=[]))
    await MemoryInferrer(model, instructions=own).infer("I'm vegan", ())
    assert model.asked[0].instructions_version == own.version
