import pytest
from pydantic import BaseModel

from farkad_ai.extraction.extractor import pillar_version
from farkad_ai.extraction.recompute import INSTRUCTIONS, EntryRecomputer
from farkad_ai.models.port import ModelTier, ModelUnavailableError, PipelineStep, Unavailability
from tests.support import AnswersByStep, Tracked, a_usage

pytestmark = pytest.mark.anyio


class Meal(BaseModel):
    pillar: str
    dish: str | None = None
    energy_kcal: int | None = None


FOOD = Tracked("food", title="Food", guidance="Estimate the energy.", entry_schema=Meal)
STATED = {"pillar": "food", "dish": "thé à la menthe"}


async def test_the_model_is_told_only_what_the_user_stated() -> None:
    model = AnswersByStep(recompute={"entries": [STATED]})

    await EntryRecomputer(model).recompute(FOOD, STATED)

    ((asked, tier),) = model.asked
    assert (asked.step, tier, asked.utterance, asked.media) == (
        PipelineStep.recompute,
        ModelTier.standard,
        "",
        (),
    )
    assert '{"dish": "thé à la menthe", "pillar": "food"}' in asked.instructions
    assert asked.instructions_version == pillar_version(INSTRUCTIONS, FOOD)


async def test_the_fields_that_follow_come_back_beside_the_stated_ones() -> None:
    answered = STATED | {"energy_kcal": 60}
    model = AnswersByStep(recompute={"entries": [answered]})

    recomputation = await EntryRecomputer(model).recompute(FOOD, STATED)

    assert recomputation.values == answered
    assert recomputation.usage == a_usage(PipelineStep.recompute)


@pytest.mark.parametrize("entries", [[], [{"pillar": "food"}]], ids=["no entry", "only a label"])
async def test_an_answer_that_states_nothing_is_refused(entries: list[object]) -> None:
    model = AnswersByStep(recompute={"entries": entries})

    with pytest.raises(ModelUnavailableError) as refused:
        await EntryRecomputer(model).recompute(FOOD, STATED)

    assert refused.value.because is Unavailability.output_did_not_parse
