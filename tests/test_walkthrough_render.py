"""Unit tests for the walkthrough renderer's pure functions."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from render_walkthrough import escape_for_script, render  # noqa: E402


def test_escape_for_script_closes_tag() -> None:
    out = escape_for_script('{"a": "</script>"}')
    assert out == '{"a": "<\\/script>"}'
    assert "</script>" not in out


def test_escape_for_script_plain_unchanged() -> None:
    assert escape_for_script('{"a": 1}') == '{"a": 1}'


def test_render_replaces_token() -> None:
    assert render("<x>__EVIDENCE_JSON__</x>", {"a": 1}) == '<x>{"a": 1}</x>'


def test_render_missing_token_raises() -> None:
    with pytest.raises(ValueError, match="__EVIDENCE_JSON__"):
        render("<x>no token here</x>", {"a": 1})


def test_render_duplicate_token_raises() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        render("<x>__EVIDENCE_JSON__</x>__EVIDENCE_JSON__", {"a": 1})


def test_render_keeps_non_ascii_verbatim() -> None:
    out = render("<x>__EVIDENCE_JSON__</x>", {"city": "İnegöl", "country": "Türkiye"})
    assert "Türkiye" in out
    assert "İnegöl" in out
