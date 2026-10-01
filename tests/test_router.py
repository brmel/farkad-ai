from datetime import time

import pytest

from farkad_ai.routing.pass_one import Mention, PassOne, StatedTime, TimeHint
from farkad_ai.routing.router import (
    NotApplicable,
    NothingToLogReason,
    Routed,
    Router,
    RoutingOutcome,
)
from tests.support import Profile, Registry, ScriptedModel, Spec

pytestmark = pytest.mark.anyio

REGISTRY = Registry(Spec("water", "tracks water intake"), Spec("food", "logs meals and snacks"))


def heard(
    *pillars: str, is_health_related: bool = True, occurred_at_hint: TimeHint | None = None
) -> PassOne:
    return PassOne(
        transcript="I drank two glasses of water",
        language="en",
        is_health_related=is_health_related,
        mentions=[Mention(pillar=pillar, said=f"some {pillar}") for pillar in pillars],
        occurred_at_hint=occurred_at_hint,
    )


async def routed(answer: PassOne, profile: Profile) -> RoutingOutcome:
    return await Router(ScriptedModel(answer), REGISTRY).route(profile, text=answer.transcript)


class TestTheRouterDecidesRatherThanTheModel:
    async def test_a_pillar_the_user_does_not_track_is_reported_untracked(self) -> None:
        outcome = await routed(heard("water", "food"), Profile("water"))

        assert isinstance(outcome, Routed)
        assert outcome.pillars == frozenset({"water"})
        assert outcome.untracked == frozenset({"food"})

    async def test_each_tracked_pillar_is_handed_only_what_was_listed_under_it(self) -> None:
        answer = PassOne(
            transcript="a smoothie, a scoop of whey and a dose of creatine",
            language="en",
            is_health_related=True,
            mentions=[
                Mention(pillar="food", said="a smoothie"),
                Mention(pillar="water", said="a glass of water"),
                Mention(pillar="food", said="a scoop of whey"),
            ],
        )

        outcome = await routed(answer, Profile("water", "food"))

        assert isinstance(outcome, Routed)
        assert outcome.mentions == {
            "food": ("a smoothie", "a scoop of whey"),
            "water": ("a glass of water",),
        }

    async def test_what_an_untracked_pillar_was_given_is_handed_to_no_other(self) -> None:
        outcome = await routed(heard("water", "food"), Profile("water"))

        assert isinstance(outcome, Routed)
        assert outcome.mentions == {"water": ("some water",)}

    async def test_a_pillar_nobody_registered_is_dropped(self) -> None:
        outcome = await routed(heard("water", "astrology"), Profile("water"))

        assert isinstance(outcome, Routed)
        assert outcome.pillars == frozenset({"water"})
        assert outcome.untracked == frozenset()

    async def test_a_log_of_only_untracked_pillars_has_nothing_to_log(self) -> None:
        outcome = await routed(heard("food"), Profile("water"))

        assert isinstance(outcome, NotApplicable)
        assert outcome.reason is NothingToLogReason.no_enabled_pillar

    async def test_a_sentence_that_is_not_a_log_has_nothing_to_log(self) -> None:
        outcome = await routed(heard("water", is_health_related=False), Profile("water"))

        assert isinstance(outcome, NotApplicable)
        assert outcome.reason is NothingToLogReason.not_a_health_log

    async def test_a_stated_time_is_kept_as_a_day_and_a_clock(self) -> None:
        at_half_twelve = TimeHint(phrase="at 12:30", day_offset=0, clock=time(12, 30))

        outcome = await routed(heard("water", occurred_at_hint=at_half_twelve), Profile("water"))

        assert isinstance(outcome, Routed)
        assert outcome.occurred_at_hint == StatedTime(
            phrase="at 12:30", day_offset=0, clock=time(12, 30)
        )


async def test_the_model_is_told_every_pillar_the_registry_holds() -> None:
    model = ScriptedModel(heard("water"))

    await Router(model, REGISTRY).route(Profile("water"), text="I drank water")

    told = model.asked[0].instructions
    assert [spec for spec in REGISTRY if f"- {spec.pillar}: {spec.intent}" not in told] == []
