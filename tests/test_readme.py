import re
import runpy
from pathlib import Path

import pytest

README = Path(__file__).parent.parent / "README.md"


def test_the_readmes_example_runs_offline_and_logs_the_water(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    example = re.search(r"```python\n(.*?)```", README.read_text(encoding="utf-8"), re.DOTALL)
    assert example is not None
    script = tmp_path / "example.py"
    script.write_text(example.group(1), encoding="utf-8")

    runpy.run_path(str(script))

    assert "'volume_ml': 500.0" in capsys.readouterr().out
