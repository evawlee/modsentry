from __future__ import annotations
import re

# Limit submitted content to ~8 000 characters (≈ 2 000 tokens at avg 4 chars/token).
_MAX_CONTENT_CHARS: int = 8_000

# Matches HTML/XML tags.
_HTML_TAG_RE = re.compile(r"<[^>]{0,500}>")

# Null bytes and non-printable ASCII control chars (except tab, LF, CR).
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class InputSanitizer:
    """
    Cleans text before it is forwarded to the LLM.

    Responsibilities
    ----------------
    * Strip HTML markup (prevents tag injection into prompts).
    * Remove non-printable control characters that could confuse tokenizers.
    * Truncate overlong inputs to ``_MAX_CONTENT_CHARS``.

    Intentionally *out of scope*:
    * Escaping Python ``str.format`` metacharacters (``{``, ``}``).
      Callers are responsible for using the sanitized value only where it is
      treated as data, not as a format template.
    * Removing newline characters — legitimate content (e.g. code, poetry,
      multi-paragraph text) must preserve line structure.
    """

    def clean(self, text: str) -> str:
        """Return a sanitized copy of *text*."""
        if not text:
            return ""
        result = _HTML_TAG_RE.sub("", text)
        result = _CONTROL_CHAR_RE.sub("", result)
        if len(result) > _MAX_CONTENT_CHARS:
            result = result[:_MAX_CONTENT_CHARS]
        return result
