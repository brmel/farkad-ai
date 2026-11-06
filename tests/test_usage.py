from farkad_ai.models.port import PipelineStep, Usage
from tests.support import a_usage


def test_a_stored_usage_parses_back_into_the_same_usage() -> None:
    usage = a_usage(PipelineStep.extraction)

    assert Usage.model_validate(usage.model_dump(mode="json")) == usage
