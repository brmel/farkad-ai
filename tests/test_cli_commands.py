from io import StringIO
from unittest.mock import patch

from farkad_ai.cli import main


def test_cli_models_prints_all_providers() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["models"])
    assert code == 0
    output = stdout.getvalue()
    assert "gemini-2.5-flash" in output
    assert "claude-3-5-sonnet-20241022" in output
    assert "gpt-4o" in output


def test_cli_prompts_lists_all_prompt_assets() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["prompts"])
    assert code == 0
    output = stdout.getvalue()
    assert "pass_one" in output
    assert "extraction" in output
    assert "recompute" in output
    assert "demo" in output


def test_cli_eval_reports_error_on_missing_dir() -> None:
    stderr = StringIO()
    with patch("sys.stderr", stderr):
        code = main(["eval", "--fixtures", "/nonexistent/directory/12345"])
    assert code == 1
    assert "not found" in stderr.getvalue()


def test_cli_eval_passes_on_gold_fixtures() -> None:
    stdout = StringIO()
    with patch("sys.stdout", stdout):
        code = main(["eval", "--fixtures", "backend/tests/fixtures/eval/gold.json"])
    assert code == 0
    assert "54/54 passed (100.0%)" in stdout.getvalue()
