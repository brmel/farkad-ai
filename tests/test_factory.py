from __future__ import annotations

from pathlib import Path

import pytest

from farkad_ai.models.cache import CachedModel
from farkad_ai.models.factory import ProviderName, create_model
from farkad_ai.models.recorded import RecordedModel

FIXTURES = Path(__file__).resolve().parents[2] / "backend" / "tests" / "fixtures" / "model"


def test_factory_creates_cached_recorded_model() -> None:
    model = create_model(ProviderName.recorded, fixtures_dir=FIXTURES, cached=True)
    assert isinstance(model, CachedModel)


def test_factory_creates_uncached_recorded_model() -> None:
    model = create_model(ProviderName.recorded, fixtures_dir=FIXTURES, cached=False)
    assert isinstance(model, RecordedModel)


def test_factory_requires_fixtures_dir_for_recorded() -> None:
    with pytest.raises(ValueError):
        create_model(ProviderName.recorded, fixtures_dir=None)


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError):
        create_model("unsupported-provider")
