import pytest
from pydantic import BaseModel

from farkad_ai.extraction.recompute import INSTRUCTIONS, EntryRecomputer
from farkad_ai.models.port import ModelTier, PipelineStep
from farkad_ai.prompts import PromptAsset
from tests.support import AnswersByStep, Tracked, a_usage

pytestmark = pytest.mark.anyio


class Meal(BaseModel):
    pillar: str
    dish: str | None = None
    energy_kcal: int | None = None


FOOD = Tracked("food", title="Food", guidance="Estimate the energy.", entry_schema=Meal)
STATED = {"pillar": "food", "dish": "thé à la menthe"}


async def test_the_model_is_told_only_what_the_user_stated() -> None:
    model = AnswersByStep(recompute={"entries": []})

    await EntryRecomputer(model).recompute(FOOD, STATED)

    ((asked, tier),) = model.asked
    assert (asked.step, tier, asked.utterance, asked.media) == (
        PipelineStep.recompute,
        ModelTier.standard,
        "",
        (),
    )
    assert '{"dish": "thé à la menthe", "pillar": "food"}' in asked.instructions
    assert asked.instructions_version == INSTRUCTIONS.version


async def test_the_fields_that_follow_come_back_beside_the_stated_ones() -> None:
    answered = STATED | {"energy_kcal": 60}
    model = AnswersByStep(recompute={"entries": [answered]})

    recomputation = await EntryRecomputer(model).recompute(FOOD, STATED)

    assert recomputation.values == answered
    assert recomputation.usage == a_usage(PipelineStep.recompute)


@pytest.mark.parametrize("entries", [[], [{"pillar": "food"}]])
async def test_an_answer_that_states_nothing_fills_nothing(entries: list[object]) -> None:
    model = AnswersByStep(recompute={"entries": entries})

    recomputation = await EntryRecomputer(model).recompute(FOOD, STATED)

    assert recomputation.values == {}


async def test_an_entry_is_recomputed_with_the_prompt_it_is_given() -> None:
    own = PromptAsset(name="recompute", text="{title} from {stated}")
    model = AnswersByStep(recompute={"entries": []})

    await EntryRecomputer(model, instructions=own).recompute(FOOD, {"dish": "rice"})

    ((asked, _),) = model.asked
    assert asked.instructions == 'Food from {"dish": "rice"}'
    assert asked.instructions_version == own.version
