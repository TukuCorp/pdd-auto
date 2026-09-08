"""Render the walkthrough page by injecting the evidence bundle into the template.

Reads ``reports/walkthrough/template.html`` and
``reports/walkthrough/inegol-evidence.json``, replaces the single
``__EVIDENCE_JSON__`` token with the escaped bundle, and writes
``reports/walkthrough/pdd-walkthrough.html``. Deterministic: same inputs
always produce byte-identical output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import structlog

logger = structlog.get_logger()

TOKEN = "__EVIDENCE_JSON__"


def escape_for_script(payload: str) -> str:
    """Escape a JSON payload so it cannot terminate the host script element."""
    return payload.replace("</", "<\\/")


def render(template_text: str, evidence: dict[str, Any]) -> str:
    """Inject the serialized evidence into the template at the single token."""
    if template_text.count(TOKEN) != 1:
        raise ValueError(f"template must contain {TOKEN} exactly once")
    payload = escape_for_script(json.dumps(evidence, ensure_ascii=False))
    return template_text.replace(TOKEN, payload)


def main() -> int:
    """Render the page; return 1 when an input is missing or the token is absent."""
    parser = argparse.ArgumentParser(description="Render the walkthrough HTML page")
    parser.add_argument("--template", default="reports/walkthrough/template.html")
    parser.add_argument("--evidence", default="reports/walkthrough/inegol-evidence.json")
    parser.add_argument("--output", default="reports/walkthrough/pdd-walkthrough.html")
    args = parser.parse_args()

    template_path = REPO_ROOT / args.template
    evidence_path = REPO_ROOT / args.evidence
    if not template_path.exists():
        logger.error("walkthrough_render_missing", path=str(template_path))
        return 1
    if not evidence_path.exists():
        logger.error("walkthrough_render_missing", path=str(evidence_path))
        return 1
    template_text = template_path.read_text(encoding="utf-8")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    try:
        page = render(template_text, evidence)
    except ValueError as exc:
        logger.error("walkthrough_render_failed", error=str(exc))
        return 1
    out = REPO_ROOT / args.output
    out.write_text(page, encoding="utf-8")
    logger.info("walkthrough_page_written", path=str(out), bytes=len(page.encode("utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
