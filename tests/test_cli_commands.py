import gc
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from farkad_ai.cli import main
from farkad_ai.eval.example import Language


def run(command: str) -> tuple[int, str]:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main([command])
    return code, stdout.getvalue()


def test_the_example_eval_replays_each_language_the_same_way_every_time() -> None:
    first, second = run("eval"), run("eval")

    assert first == second
    code, table = first
    assert code == 0
    for language in Language:
        assert f"| {language} | 3 |" in table


@pytest.mark.parametrize(
    ("text", "code", "said"),
    [
        ("I drank 500 ml of water", 0, '"water"'),
        ("a sentence nobody recorded", 1, "--provider"),
    ],
)
def test_route_replays_the_gold_set_and_names_the_flag_for_any_other_sentence(
    text: str, code: int, said: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["route", "--text", text]) == code
    assert said in "".join(capsys.readouterr())


CREDENTIAL_VARIABLES = (
    "GOOGLE_APPLICATION_CREDENTIALS",
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
)


def test_vertex_without_credentials_names_what_to_set_in_one_line(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("google.genai")
    for variable in CREDENTIAL_VARIABLES:
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("CLOUDSDK_CONFIG", str(tmp_path))
    monkeypatch.setenv("NO_GCE_CHECK", "True")

    assert main(["eval", "--provider", "vertex"]) == 1
    # google-genai's client finaliser schedules aclose() on whichever event loop is running when
    # it is collected, and fails there when construction failed (google/genai/_api_client.py).
    gc.collect()
    error = capsys.readouterr().err
    assert "GOOGLE_CLOUD_PROJECT" in error
    assert error.count("\n") == 1
