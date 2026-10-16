from io import StringIO
from unittest.mock import patch

from farkad_ai.cli import main
from farkad_ai.eval.example import Language


def run(command: str) -> tuple[int, str]:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main([command])
    return code, stdout.getvalue()


def test_prompts_lists_every_prompt_asset() -> None:
    code, output = run("prompts")

    assert code == 0
    assert "pass_one" in output
    assert "extraction" in output
    assert "memory_inference" in output


def test_the_example_eval_replays_each_language_the_same_way_every_time() -> None:
    first, second = run("eval"), run("eval")

    assert first == second
    code, table = first
    assert code == 0
    for language in Language:
        assert f"| {language} | 3 |" in table
