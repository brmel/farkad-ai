import asyncio
from collections.abc import Callable
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel

pytest.importorskip("google.genai")

import google.auth
import httpx
from google.genai import types
from google.oauth2.credentials import Credentials

from farkad_ai.models.port import (
    ModelChoice,
    ModelTier,
    ModelUnavailableError,
    PipelineStep,
    Prompt,
    Unavailability,
    Usage,
    fixed,
)
from farkad_ai.models.vertex import Retries, VertexModel

ATTEMPTS = 3
CHOSEN = "gemini-chosen"
REAL_SLEEP = asyncio.sleep
ANSWER = {
    "candidates": [{"content": {"role": "model", "parts": [{"text": '{"said": "a meal"}'}]}}],
    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
}


class Said(BaseModel):
    said: str


def answered(metadata: types.GenerateContentResponseUsageMetadata | None) -> Mock:
    return Mock(parsed={"said": "a meal"}, usage_metadata=metadata)


def counted(*, prompt: int | None, candidates: int | None, cached: int | None = None) -> Mock:
    return answered(
        types.GenerateContentResponseUsageMetadata(
            prompt_token_count=prompt,
            candidates_token_count=candidates,
            cached_content_token_count=cached,
        )
    )


async def vertex_usage(response: Mock) -> Usage:
    client = Mock()
    client.aio.models.generate_content = AsyncMock(return_value=response)
    asked = Prompt(step=PipelineStep.routing, instructions="Route", instructions_version="v1")
    completion = await VertexModel(client).complete(asked, schema=Said, tier=ModelTier.fast)
    return completion.usage


@pytest.mark.anyio
@pytest.mark.parametrize(
    "response",
    [
        answered(None),
        counted(prompt=None, candidates=800),
        counted(prompt=9_000, candidates=None),
    ],
    ids=["no usage", "no input count", "no output count"],
)
async def test_an_answer_that_does_not_count_its_tokens_is_refused(response: Mock) -> None:
    with pytest.raises(ModelUnavailableError) as refused:
        await vertex_usage(response)

    assert refused.value.because is Unavailability.usage_not_reported


@pytest.mark.anyio
async def test_a_counted_answer_reports_its_tokens() -> None:
    usage = await vertex_usage(counted(prompt=9_000, candidates=800))

    assert (usage.input_tokens, usage.cached_input_tokens, usage.output_tokens) == (9_000, 0, 800)


@pytest.mark.anyio
async def test_the_tokens_served_from_the_cache_are_reported() -> None:
    usage = await vertex_usage(counted(prompt=9_000, candidates=800, cached=7_000))

    assert usage.cached_input_tokens == 7_000


class Vertex:
    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.asked = 0
        self.paths: list[str] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        status = self._statuses[min(self.asked, len(self._statuses) - 1)]
        self.asked += 1
        self.paths.append(request.url.path)
        body = ANSWER if status == httpx.codes.OK else {"error": {"code": status}}
        return httpx.Response(status, json=body, request=request)


@pytest.fixture
def vertex_answering(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Vertex]:
    async def without_waiting(_: float) -> None:
        await REAL_SLEEP(0)

    signed_in = Credentials("token")  # type: ignore[no-untyped-call, unused-ignore]
    monkeypatch.setattr(google.auth, "default", lambda **_: (signed_in, "a-project"))
    monkeypatch.setattr(asyncio, "sleep", without_waiting)

    def answering(*statuses: int) -> Vertex:
        vertex = Vertex(list(statuses))
        monkeypatch.setattr(
            httpx.AsyncHTTPTransport, "handle_async_request", vertex.handle_async_request
        )
        return vertex

    return answering


async def ask() -> str:
    model = VertexModel.connected(
        project="a-project",
        location="europe-west1",
        retries=Retries(ATTEMPTS, timedelta(seconds=2), timedelta(seconds=8)),
    ).choosing(fixed({ModelTier.fast: ModelChoice(CHOSEN)}))
    prompt = Prompt(PipelineStep.routing, "say what was eaten", "v1", utterance="lunch")
    return (await model.complete(prompt, schema=Said, tier=ModelTier.fast)).value.said


@pytest.mark.anyio
async def test_a_busy_chosen_model_is_asked_again_and_its_answer_kept(
    vertex_answering: Callable[..., Vertex],
) -> None:
    vertex = vertex_answering(429, 200)

    assert await ask() == "a meal"
    assert vertex.asked == 2
    assert all(path.endswith(f"/models/{CHOSEN}:generateContent") for path in vertex.paths)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("status", "asked"),
    [(503, ATTEMPTS), (400, 1)],
    ids=["unavailable on every attempt", "a request the model refuses"],
)
async def test_the_model_is_given_up_on_after_the_attempts_or_at_once_when_refused(
    vertex_answering: Callable[..., Vertex], status: int, asked: int
) -> None:
    vertex = vertex_answering(status)

    with pytest.raises(ModelUnavailableError):
        await ask()
    assert vertex.asked == asked
