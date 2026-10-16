from datetime import time

import pytest

from farkad_ai.prompts import PromptAsset
from farkad_ai.routing.pass_one import Mention, PassOne, TimeHint
from farkad_ai.routing.port import (
    NothingToLog,
    NothingToLogReason,
    PartOfDay,
    Routed,
    RoutingOutcome,
    StatedTime,
)
from farkad_ai.routing.router import Router
from tests.support import ScriptedModel, Spec

pytestmark = pytest.mark.anyio

CATALOGUE = (Spec("water", "tracks water intake"), Spec("food", "logs meals and snacks"))


def heard(
    *pillars: str, is_health_related: bool = True, states_a_lasting_fact: bool = False
) -> PassOne:
    return PassOne(
        transcript="I drank two glasses of water",
        language="en",
        is_health_related=is_health_related,
        states_a_lasting_fact=states_a_lasting_fact,
        mentions=[Mention(pillar=pillar, said=f"some {pillar}") for pillar in pillars],
    )


async def routed(answer: PassOne, tracked: frozenset[str]) -> RoutingOutcome:
    return await Router(ScriptedModel(answer), CATALOGUE).route(tracked, text=answer.transcript)


class TestTheRouterDecidesRatherThanTheModel:
    async def test_a_pillar_the_user_does_not_track_is_reported_untracked(self) -> None:
        outcome = await routed(heard("water", "food"), frozenset({"water"}))

        assert isinstance(outcome, Routed)
        assert outcome.routes == frozenset({"water"})
        assert outcome.untracked == frozenset({"food"})

    async def test_each_tracked_pillar_is_handed_only_what_was_listed_under_it(self) -> None:
        answer = PassOne(
            transcript="a smoothie, a scoop of whey and a dose of creatine",
            language="en",
            is_health_related=True,
            states_a_lasting_fact=False,
            mentions=[
                Mention(pillar="food", said="a smoothie"),
                Mention(pillar="water", said="a glass of water"),
                Mention(pillar="food", said="a scoop of whey"),
            ],
        )

        outcome = await routed(answer, frozenset({"water", "food"}))

        assert isinstance(outcome, Routed)
        assert outcome.mentions == {
            "food": ("a smoothie", "a scoop of whey"),
            "water": ("a glass of water",),
        }

    async def test_what_an_untracked_pillar_was_given_is_handed_to_no_other(self) -> None:
        outcome = await routed(heard("water", "food"), frozenset({"water"}))

        assert isinstance(outcome, Routed)
        assert outcome.mentions == {"water": ("some water",)}

    async def test_a_pillar_nobody_registered_is_dropped(self) -> None:
        outcome = await routed(heard("water", "astrology"), frozenset({"water"}))

        assert isinstance(outcome, Routed)
        assert outcome.routes == frozenset({"water"})
        assert outcome.untracked == frozenset()

    async def test_a_log_of_only_untracked_pillars_has_nothing_to_log(self) -> None:
        outcome = await routed(heard("food"), frozenset({"water"}))

        assert isinstance(outcome, NothingToLog)
        assert outcome.reason is NothingToLogReason.no_enabled_pillar

    async def test_a_sentence_that_is_not_a_log_has_nothing_to_log(self) -> None:
        outcome = await routed(heard("water", is_health_related=False), frozenset({"water"}))

        assert isinstance(outcome, NothingToLog)
        assert outcome.reason is NothingToLogReason.not_a_health_log

    async def test_a_stated_time_dates_only_the_mention_it_was_said_about(self) -> None:
        answer = PassOne(
            transcript="a coffee at eight, and two glasses of water",
            language="en",
            is_health_related=True,
            states_a_lasting_fact=False,
            mentions=[
                Mention(
                    pillar="food",
                    said="a coffee at eight",
                    occurred_at_hint=TimeHint(phrase="at eight", day_offset=0, clock=time(8, 0)),
                ),
                Mention(pillar="water", said="two glasses of water"),
            ],
        )

        outcome = await routed(answer, frozenset({"water", "food"}))

        assert isinstance(outcome, Routed)
        assert outcome.occurred_at_hints == {
            "food": StatedTime(phrase="at eight", day_offset=0, time_of_day=time(8, 0)),
            "water": None,
        }


@pytest.mark.parametrize(
    "answer",
    [
        heard("water", states_a_lasting_fact=True),
        heard("food", states_a_lasting_fact=True),
        heard(is_health_related=False, states_a_lasting_fact=True),
    ],
)
async def test_a_lasting_fact_is_reported_whether_or_not_anything_is_logged(
    answer: PassOne,
) -> None:
    outcome = await routed(answer, frozenset({"water"}))

    assert outcome.states_a_lasting_fact


async def test_the_model_is_told_every_pillar_the_catalogue_holds() -> None:
    model = ScriptedModel(heard("water"))

    await Router(model, CATALOGUE).route(frozenset({"water"}), text="I drank water")

    told = model.asked[0].instructions
    assert [spec for spec in CATALOGUE if f"- {spec.pillar}: {spec.intent}" not in told] == []


async def test_the_router_routes_with_the_prompt_it_is_given() -> None:
    own = PromptAsset(name="pass_one", text="Route this: {pillars}")
    model = ScriptedModel(heard("water"))

    await Router(model, CATALOGUE[:1], instructions=own).route(frozenset({"water"}), text="water")

    assert model.asked[0].instructions.startswith("Route this: - water: tracks water intake")
    assert model.asked[0].instructions_version == own.version


def test_a_stated_time_names_a_day_only_when_it_is_not_today() -> None:
    assert not StatedTime(phrase="at 3pm", day_offset=0, time_of_day=time(15, 0)).names_a_day
    assert StatedTime(phrase="yesterday at 3pm", day_offset=-1, time_of_day=time(15, 0)).names_a_day


@pytest.mark.parametrize(
    ("hint", "time_of_day"),
    [
        (
            TimeHint(phrase="this afternoon", day_offset=0, part_of_day=PartOfDay.afternoon),
            PartOfDay.afternoon,
        ),
        (
            TimeHint(
                phrase="at six this evening",
                day_offset=0,
                clock=time(18, 0),
                part_of_day=PartOfDay.evening,
            ),
            time(18, 0),
        ),
        (TimeHint(phrase="yesterday", day_offset=-1), None),
    ],
)
def test_the_consumer_is_given_the_hour_said_else_the_part_of_the_day_said(
    hint: TimeHint, time_of_day: time | PartOfDay | None
) -> None:
    assert hint.stated().time_of_day == time_of_day
