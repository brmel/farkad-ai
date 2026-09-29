from __future__ import annotations

from pathlib import Path

import pytest

from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.recorded import RecordedModel


def test_factory_creates_recorded_model(tmp_path: Path) -> None:
    model = create_model(ProviderName.recorded, fixtures_dir=tmp_path)
    assert isinstance(model, RecordedModel)


def test_factory_requires_fixtures_dir_for_recorded() -> None:
    with pytest.raises(ValueError):
        create_model(ProviderName.recorded, fixtures_dir=None)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        create_model("unsupported-provider")
