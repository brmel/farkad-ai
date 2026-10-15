from __future__ import annotations

from pathlib import Path

import pytest

from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.recorded import RecordedModel


def test_the_recorded_provider_replays_from_the_directory_given(tmp_path: Path) -> None:
    model = create_model(ProviderName.recorded, fixtures_dir=tmp_path)
    assert isinstance(model, RecordedModel)


def test_the_recorded_provider_needs_a_directory_to_replay_from() -> None:
    with pytest.raises(ValueError):
        create_model(ProviderName.recorded, fixtures_dir=None)
