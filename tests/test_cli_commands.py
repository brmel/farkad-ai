from io import StringIO
from unittest.mock import patch

from farkad_ai.cli import main


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
