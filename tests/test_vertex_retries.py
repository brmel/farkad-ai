import asyncio
from collections.abc import Callable
from datetime import timedelta

import pytest
from pydantic import BaseModel

pytest.importorskip("google.genai")

import google.auth
import httpx
from google.oauth2.credentials import Credentials

from farkad_ai.models.port import ModelTier, ModelUnavailableError, PipelineStep, Prompt
from farkad_ai.models.vertex import Retries, VertexModel

ATTEMPTS = 3
REAL_SLEEP = asyncio.sleep
ANSWER = {
    "candidates": [{"content": {"role": "model", "parts": [{"text": '{"said": "a meal"}'}]}}],
    "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
}


class Said(BaseModel):
    said: str


class Vertex:
    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.asked = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        status = self._statuses[min(self.asked, len(self._statuses) - 1)]
        self.asked += 1
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
    )
    prompt = Prompt(PipelineStep.routing, "say what was eaten", "v1", utterance="lunch")
    return (await model.complete(prompt, schema=Said, tier=ModelTier.fast)).value.said


@pytest.mark.anyio
async def test_a_busy_model_is_asked_again_and_its_answer_kept(
    vertex_answering: Callable[..., Vertex],
) -> None:
    vertex = vertex_answering(429, 200)

    assert await ask() == "a meal"
    assert vertex.asked == 2


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
