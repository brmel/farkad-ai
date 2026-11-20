from __future__ import annotations

from collections.abc import Iterator

import pytest

from farkad_ai.eval.example import RECORDINGS
from farkad_ai.models.port import Model
from farkad_ai.models.recorded import RecordingModel
from farkad_ai.models.registry import ProviderName, connect


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--live",
        type=ProviderName,
        choices=list(ProviderName),
        default=None,
        help="Ask this provider every gold case and replace the recordings; spends money",
    )


@pytest.fixture(scope="session")
def gold_model(request: pytest.FixtureRequest) -> Iterator[Model]:
    live: ProviderName | None = request.config.getoption("--live")
    if live is None:
        yield connect(ProviderName.recorded)
        return
    recorder = RecordingModel(connect(live), RECORDINGS)
    yield recorder
    recorder.commit()
