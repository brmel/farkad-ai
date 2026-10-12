from io import StringIO
from unittest.mock import patch

from farkad_ai.cli import main
from farkad_ai.eval.run import Language


def test_cli_prompts_lists_all_prompt_assets() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["prompts"])
    assert code == 0
    output = stdout.getvalue()
    assert "pass_one" in output
    assert "extraction" in output
    assert "memory_inference" in output


def test_the_example_eval_replays_every_language_from_its_committed_answers() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["eval"])

    assert code == 0
    table = stdout.getvalue()
    for language in Language:
        assert f"| {language} | 3 | 100% |" in table
    assert "Model: gemini-3.5-flash-lite" in table
