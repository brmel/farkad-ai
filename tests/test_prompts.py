from string import Formatter

from farkad_ai.prompts import PromptAsset, list_prompts, prompt


def test_a_prompt_is_versioned_by_its_text() -> None:
    original = prompt("extraction")
    edited = PromptAsset(name=original.name, text=original.text + " Answer in metric.")

    assert edited.version != original.version
    assert original.version != prompt("pass_one").version
    assert len(original.version) == 12


def test_every_brace_in_a_prompt_is_a_placeholder() -> None:
    for asset in list_prompts():
        for _, field, _, _ in Formatter().parse(asset.text):
            if field is None:
                continue
            assert field.isidentifier(), (
                f"{asset.name}.txt has a literal brace around {field!r}. "
                f"Write it as {{{{{field}}}}} if it is example text, not a placeholder."
            )
