import textwrap


def clean_text(text: str) -> str:
    """Clean text by removing extra indentation and leading/trailing whitespace."""
    return textwrap.dedent(text).strip()
