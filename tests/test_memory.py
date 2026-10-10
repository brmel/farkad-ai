from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from farkad_ai.memory.facts import (
    MAX_CONTENT_CHARACTERS,
    MAX_FACTS,
    Confirmed,
    Declined,
    Disclosure,
    EmptyFactError,
    Fact,
    FactSource,
    MemoryCategory,
    OverlongFactError,
    Refusal,
    Remembered,
    Superseded,
    learn,
    learn_all,
)
from farkad_ai.memory.habits import HabitBaseline, UsualAmount
from farkad_ai.memory.inference import NOTHING_KNOWN, MemoryInferrer, subject_named
from farkad_ai.memory.sheet import SHEET_CHARACTERS, core_sheet
from farkad_ai.types import PipelineStep
from tests.support import ScriptedModel, a_usage

MONDAY = datetime(2026, 9, 21, 8, tzinfo=UTC)
FRIDAY = MONDAY + timedelta(days=4)

VEGAN = Disclosure("diet", MemoryCategory.dietary, "Vegan")
EATS_MEAT = Disclosure("diet", MemoryCategory.dietary, "Eats meat again since September")


def known(
    disclosure: Disclosure,
    *,
    source: FactSource = FactSource.spoken,
    enabled: bool = True,
) -> Fact:
    return Fact(disclosure, source, enabled=enabled, since=MONDAY)


class TestANewerWordOnATopicReplacesTheOlder:
    def test_a_first_word_on_a_topic_is_remembered(self) -> None:
        assert learn(None, VEGAN, at=MONDAY) == Remembered(
            Fact(VEGAN, FactSource.spoken, enabled=True, since=MONDAY)
        )

    def test_vegan_then_meat_leaves_one_fact_saying_meat(self) -> None:
        learned = learn(known(VEGAN), EATS_MEAT, at=FRIDAY)

        assert learned == Superseded(
            Fact(EATS_MEAT, FactSource.spoken, enabled=True, since=FRIDAY), replaced=known(VEGAN)
        )

    def test_saying_the_same_thing_again_only_moves_its_date(self) -> None:
        again = Disclosure("diet", MemoryCategory.dietary, "  vegan ")

        assert learn(known(VEGAN), again, at=FRIDAY) == Confirmed(
            Fact(VEGAN, FactSource.spoken, enabled=True, since=FRIDAY)
        )


class TestWhatAModelReadingMayNotOverwrite:
    def test_a_fact_the_user_switched_off_stays_off(self) -> None:
        assert learn(known(VEGAN, enabled=False), EATS_MEAT, at=FRIDAY) == Declined(
            EATS_MEAT, Refusal.switched_off
        )

    def test_a_fact_the_user_typed_is_theirs(self) -> None:
        typed = known(VEGAN, source=FactSource.entered)

        assert learn(typed, EATS_MEAT, at=FRIDAY) == Declined(EATS_MEAT, Refusal.written_by_user)

    def test_a_full_memory_refuses_a_new_topic_but_still_updates_a_known_one(self) -> None:
        full = {
            f"topic_{n}": known(Disclosure(f"topic_{n}", MemoryCategory.general, f"Fact {n}"))
            for n in range(MAX_FACTS - 1)
        } | {"diet": known(VEGAN)}
        novel = Disclosure("coffee_order", MemoryCategory.preference, "Oat flat white")

        learned = learn_all(full, (novel, EATS_MEAT), at=FRIDAY)

        assert learned[0] == Declined(novel, Refusal.memory_full)
        assert isinstance(learned[1], Superseded)


class TestAFactIsOneShortSentence:
    def test_empty_and_overlong_facts_are_refused(self) -> None:
        with pytest.raises(EmptyFactError):
            Disclosure("diet", MemoryCategory.dietary, "   ")
        with pytest.raises(OverlongFactError):
            Disclosure("diet", MemoryCategory.dietary, "x" * (MAX_CONTENT_CHARACTERS + 1))


ALLERGY = Disclosure("allergy", MemoryCategory.medical, "Allergic to peanuts")
COFFEE = HabitBaseline("water", "coffee", 12, UsualAmount(250.0, "ml"), 8)


class TestTheSheetEveryCaptureIsTold:
    def test_nothing_known_tells_nothing(self) -> None:
        assert core_sheet((), ()) == ""

    def test_constraints_come_first_and_a_switched_off_fact_is_left_out(self) -> None:
        facts = [known(VEGAN, enabled=False), known(ALLERGY, source=FactSource.entered)]

        assert core_sheet(facts, [COFFEE]) == (
            "About this person:\n- Allergic to peanuts\n"
            "- logs coffee 250 ml around 08:00 (12x in 28 days)"
        )

    def test_the_sheet_stays_inside_its_budget(self) -> None:
        wordy = [
            known(Disclosure(f"topic_{n}", MemoryCategory.preference, "Prefers oat milk " * 3))
            for n in range(6)
        ]

        sheet = core_sheet([*wordy, known(ALLERGY, source=FactSource.entered)], [COFFEE])

        assert len(sheet) <= SHEET_CHARACTERS
        assert sheet.splitlines()[1] == "- Allergic to peanuts"

    def test_a_line_that_fits_is_kept_after_one_that_did_not(self) -> None:
        newest = Fact(
            Disclosure("surgery", MemoryCategory.medical, "Had surgery " * 16),
            FactSource.spoken,
            enabled=True,
            since=FRIDAY,
        )
        too_long_beside_it = known(Disclosure("insulin", MemoryCategory.medical, "Insulin " * 18))

        sheet = core_sheet([newest, too_long_beside_it, known(ALLERGY)], [])

        assert "- Allergic to peanuts" in sheet.splitlines()


def said(subject: str, content: str, category: str = "dietary") -> dict[str, str]:
    return {"subject": subject, "category": category, "content": content}


class TestASubjectIsParsedNotTrusted:
    def test_a_subject_becomes_a_lowercase_ascii_slug(self) -> None:
        assert subject_named("Coffee Order!") == "coffee_order"
        assert subject_named("  diet  ") == "diet"
        assert subject_named("قهوة") == ""

    @pytest.mark.anyio
    async def test_a_fact_without_a_usable_subject_is_dropped(self) -> None:
        model = ScriptedModel(
            {"facts": [said("قهوة", "Drinks Arabic coffee"), said("Diet", "Vegan")]}
        )

        inference = await MemoryInferrer(model).infer("I'm vegan", ())

        assert inference.disclosures == (VEGAN,)
        assert inference.usage == a_usage(PipelineStep.memory)


class TestAKnownSubjectIsReusedAsWritten:
    @pytest.mark.anyio
    async def test_a_typed_fact_keeps_its_subject_whatever_case_the_model_answers_in(
        self,
    ) -> None:
        typed = known(
            Disclosure("Xk3mPq9RtZ", MemoryCategory.dietary, "Vegetarian"),
            source=FactSource.entered,
        )
        model = ScriptedModel({"facts": [said("xk3mpq9rtz", "Eats meat again")]})

        inference = await MemoryInferrer(model).infer("eating meat again", (typed,))

        (heard,) = inference.disclosures
        assert heard.subject == "Xk3mPq9RtZ"
        assert isinstance(learn(typed, heard, at=FRIDAY), Declined)


class TestTheModelIsToldWhatIsKnown:
    @pytest.mark.anyio
    async def test_known_facts_are_listed_so_a_subject_can_be_reused(self) -> None:
        model = ScriptedModel({"facts": []})

        await MemoryInferrer(model).infer("I eat meat again", (known(VEGAN, enabled=False),))
        await MemoryInferrer(model).infer("I eat meat again", ())

        told, untold = model.asked
        assert told.step is PipelineStep.memory
        assert "- diet: Vegan" in told.instructions
        assert untold.instructions.endswith(NOTHING_KNOWN)
