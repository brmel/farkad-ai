from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import BaseModel

from farkad_ai.memory import (
    Declined,
    Disclosure,
    Fact,
    FactSource,
    HabitBaseline,
    MemoryCategory,
    MemoryInferrer,
    Refusal,
    Superseded,
    UsualAmount,
    core_sheet,
    learn,
)
from farkad_ai.types import Completion, ModelTier, PipelineStep, Prompt, Usage

MONDAY = datetime(2026, 9, 21, 8, tzinfo=UTC)
VEGAN = Disclosure("diet", MemoryCategory.dietary, "Vegan")
MEAT = Disclosure("diet", MemoryCategory.dietary, "Eats meat again")


def test_a_newer_word_on_a_topic_replaces_the_older_unless_the_user_switched_it_off() -> None:
    spoken = Fact(VEGAN, FactSource.spoken, enabled=True, since=MONDAY)
    later = MONDAY + timedelta(days=3)

    assert learn(spoken, MEAT, at=later) == Superseded(
        Fact(MEAT, FactSource.spoken, enabled=True, since=later), replaced=spoken
    )
    switched_off = Fact(VEGAN, FactSource.spoken, enabled=False, since=MONDAY)
    assert learn(switched_off, MEAT, at=later) == Declined(MEAT, Refusal.switched_off)


def test_the_sheet_tells_constraints_first_and_leaves_out_what_is_switched_off() -> None:
    facts = [
        Fact(VEGAN, FactSource.spoken, enabled=False, since=MONDAY),
        Fact(
            Disclosure("allergy", MemoryCategory.medical, "Allergic to peanuts"),
            FactSource.entered,
            enabled=True,
            since=MONDAY,
        ),
    ]
    coffee = HabitBaseline("water", "coffee", 12, UsualAmount(250.0, "ml"), 8)

    assert core_sheet(facts, [coffee]) == (
        "About this person:\n- Allergic to peanuts\n"
        "- logs coffee 250 ml around 08:00 (12x in 28 days)"
    )


class Answering:
    async def complete[T: BaseModel](
        self, prompt: Prompt, *, schema: type[T], tier: ModelTier
    ) -> Completion[T]:
        facts = [{"subject": "Diet!", "category": "dietary", "content": "Vegan"}]
        return Completion(
            value=schema.model_validate({"facts": facts}),
            usage=Usage(
                step=PipelineStep.memory,
                model="gemini-3.5-flash-lite",
                prompt_version=prompt.instructions_version,
                input_tokens=10,
                output_tokens=5,
                latency_ms=1,
                cost_cents=Decimal("0.001"),
            ),
        )


@pytest.mark.anyio
async def test_the_inferrer_parses_the_subject_it_was_given() -> None:
    inference = await MemoryInferrer(Answering()).infer("I'm vegan", ())

    assert inference.disclosures == (VEGAN,)
