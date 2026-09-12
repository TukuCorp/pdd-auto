"""Ranked precedent selection with self-exclusion and a normative channel.

Implements Specification S-1 (deterministic similarity scoring), S-2
(methodology text through a separate normative channel) and S-3
(self-exclusion of the project's own registered PDD).
"""

from __future__ import annotations

import re
import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence

from pdd_agent.retrieval.index import RetrievalIndex, get_retrieval_index, load_corpus_config
from pdd_agent.retrieval.search import (
    RetrievalResult,
    _warn_no_index_once,
    get_section_heading_examples,
)

logger = structlog.get_logger()

TECHNOLOGY_KEYWORDS: dict[str, list[str]] = {
    "combined_wte_ad": ["anaerobic digestion", "biomethan", "biogas", "refuse derived", "rdf"],
    "anaerobic_digestion": ["anaerobic digestion", "biogas", "digester"],
    "incineration_with_energy_recovery": [
        "incinerat",
        "waste-to-energy",
        "mass burn",
        "combustion",
    ],
    "landfill_gas_capture": ["landfill gas", "lfg", "flare"],
    "refuse_derived_fuel": ["refuse derived", "rdf"],
    "mechanical_biological_treatment": ["mechanical biological", "mbt"],
}

_COUNTRY_ALIAS_GROUPS: tuple[tuple[str, ...], ...] = (
    ("türkiye", "turkey"),
    ("viet nam", "vietnam"),
)

_DAMAGED_RATIO_THRESHOLD = 0.005

_NORMATIVE_STOP_WORDS: frozenset[str] = frozenset(
    {
        "with",
        "from",
        "that",
        "this",
        "these",
        "those",
        "have",
        "has",
        "will",
        "would",
        "should",
        "could",
        "into",
        "upon",
        "over",
        "under",
        "between",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "about",
        "such",
        "other",
        "which",
        "their",
        "there",
        "then",
        "than",
        "also",
        "within",
        "without",
        "section",
        "chapter",
        "annex",
    }
)


@dataclass(frozen=True)
class ProjectProfile:
    """The project facts that drive ranked grounding selection."""

    family: str
    technology_type: str
    methodology_ids: tuple[str, ...]
    country: str
    vcs_id: str


@dataclass
class Grounding:
    """Everything retrieved for one section: precedent, normative, exclusions."""

    precedent: list[RetrievalResult] = field(default_factory=list)
    normative: list[RetrievalResult] = field(default_factory=list)
    excluded_documents: list[str] = field(default_factory=list)
    from_fallback_family: bool = False


def profile_from_project(project_input: Any | None) -> ProjectProfile:
    """Build the ranking profile for a project input (None yields defaults)."""
    if project_input is None:
        return ProjectProfile("wte", "other", (), "", "")
    from pdd_agent.agent.section_orchestrator import family_slug_for

    technology = getattr(project_input, "technology", None)
    location = getattr(project_input, "location", None)
    project = getattr(project_input, "project", None)
    methodology_ids = tuple(str(m) for m in (getattr(technology, "methodology_ids", None) or ()))
    family = family_slug_for(methodology_ids)
    technology_type = str(getattr(technology, "technology_type", None) or "other")
    country = str(getattr(location, "country", None) or "")
    vcs_raw = getattr(project, "project_id_vcs", None) or ""
    vcs_id = re.sub(r"\D", "", str(vcs_raw))
    return ProjectProfile(family, technology_type, methodology_ids, country, vcs_id)


def exclusion_set(project_vcs_id: str | None, registry_ids: dict[str, str]) -> frozenset[str]:
    """Return the document stems registered under the project's VCS id (S-3)."""
    digits = re.sub(r"\D", "", project_vcs_id or "")
    if not digits:
        return frozenset()
    return frozenset(s for s, v in (registry_ids or {}).items() if str(v) == digits)


def _country_terms(country: str) -> list[str]:
    """Return the FTS terms matching a project country, including aliases."""
    if not country or not str(country).strip():
        return []
    original = str(country).strip()
    lowered = original.lower()
    for group in _COUNTRY_ALIAS_GROUPS:
        if lowered in group:
            return list(group)
    return [original]


def score_chunk(
    text: str,
    document_name: str,
    profile: ProjectProfile,
    families: dict[str, str],
    country_hit: bool,
    bm25_norm: float,
) -> tuple[float, list[str]]:
    """Score one candidate chunk (S-1) and return its fired feature labels."""
    labels: list[str] = []
    score = 0.0
    if families.get(document_name) == profile.family:
        score += 3.0
        labels.append(f"family:{profile.family}")
    lowered = text.lower()
    tech_hit = ""
    for keyword in TECHNOLOGY_KEYWORDS.get(profile.technology_type, []):
        if keyword.lower() in lowered:
            tech_hit = keyword
            break
    if tech_hit:
        score += 2.0
        labels.append(f"tech:{tech_hit}")
    if country_hit:
        score += 1.0
        labels.append(f"country:{profile.country}")
    method_hit = ""
    for methodology_id in profile.methodology_ids:
        if methodology_id and methodology_id.lower() in lowered:
            method_hit = methodology_id
            break
    if method_hit:
        score += 1.0
        labels.append(f"methodology:{method_hit}")
    if bm25_norm > 0:
        score += bm25_norm
        labels.append(f"bm25:{bm25_norm:.2f}")
    if text and text.count("�") / len(text) > _DAMAGED_RATIO_THRESHOLD:
        score -= 2.0
        labels.append("damaged-text")
    return score, labels


def _quote_fts(term: str) -> str:
    """Quote an FTS query term when it holds anything beyond [A-Za-z0-9]."""
    term = str(term).strip().replace('"', '""')
    if re.search(r"[^A-Za-z0-9]", term):
        return f'"{term}"'
    return term


def _bm25_query(keywords: Sequence[str], methodology_ids: Sequence[str]) -> str:
    """Join technology keywords and methodology ids into one FTS OR query."""
    parts = []
    for keyword in keywords:
        keyword = str(keyword).strip()
        if keyword:
            parts.append(_quote_fts(keyword))
    for methodology_id in methodology_ids:
        methodology_id = str(methodology_id).strip()
        if methodology_id:
            parts.append(_quote_fts(methodology_id))
    return " OR ".join(parts)


def select_precedent(
    section_id: str,
    sub_section_id: str | None,
    profile: ProjectProfile,
    k: int,
    index: RetrievalIndex,
    excluded: frozenset[str],
    methodology_documents: frozenset[str],
    families: dict[str, str],
) -> list[RetrievalResult]:
    """Select up to k precedent chunks by deterministic similarity score (S-1)."""
    excluded = frozenset(excluded)
    method_docs = frozenset(methodology_documents)

    def _pool(document_family: str | None) -> list[dict[str, Any]]:
        return [
            row
            for row in index.get_section_examples(
                section_id,
                sub_section_id=sub_section_id,
                document_family=document_family,
                k=50,
            )
            if row["document_name"] not in excluded and row["document_name"] not in method_docs
        ]

    from_fallback = False
    pool = _pool(profile.family)
    if not pool:
        logger.warning("retrieval_family_fallback", family=profile.family, section_id=section_id)
        pool = _pool(None)
        from_fallback = True
    query = _bm25_query(
        TECHNOLOGY_KEYWORDS.get(profile.technology_type, []), profile.methodology_ids
    )
    ranks: dict[tuple[str, int], float] = {}
    if query:
        hits = index.search(query, section_id=section_id, k=50)
        total = len(hits)
        for rank, hit in enumerate(hits):
            ranks[(hit["document_name"], hit.get("chunk_index", 0))] = 1.0 - rank / total

    country_terms = _country_terms(profile.country)
    country_cache: dict[str, bool] = {}
    scored: list[tuple[float, str, int, dict[str, Any], list[str]]] = []
    for row in pool:
        document_name = row["document_name"]
        if document_name not in country_cache:
            country_cache[document_name] = (
                index.document_mentions(document_name, country_terms) if country_terms else False
            )
        chunk_index = row.get("chunk_index", 0)
        bm25_norm = ranks.get((document_name, chunk_index), 0.0)
        score, labels = score_chunk(
            row.get("text", ""),
            document_name,
            profile,
            families,
            country_cache[document_name],
            bm25_norm,
        )
        scored.append((score, document_name, chunk_index, row, labels))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))

    chosen: list[tuple[float, dict[str, Any], list[str]]] = []
    seen_documents: set[str] = set()
    for score, document_name, _chunk_index, row, labels in scored:
        if len(chosen) >= k:
            break
        if document_name in seen_documents:
            continue
        seen_documents.add(document_name)
        chosen.append((score, row, labels))
    if len(chosen) < k:
        chosen_keys = {(row["document_name"], row.get("chunk_index", 0)) for _, row, _ in chosen}
        for score, document_name, chunk_index, row, labels in scored:
            if len(chosen) >= k:
                break
            if (document_name, chunk_index) in chosen_keys:
                continue
            chosen_keys.add((document_name, chunk_index))
            chosen.append((score, row, labels))

    return [
        RetrievalResult(
            section_id=row.get("section_id") or section_id,
            sub_section_id=row.get("sub_section_id") or "",
            document_name=row["document_name"],
            canonical_heading=row.get("canonical_heading", ""),
            text=row.get("text", ""),
            content_class=row.get("content_class") or "",
            review_sensitivity=row.get("review_sensitivity") or "",
            score=score,
            matched_terms=labels,
            from_fallback_family=from_fallback,
        )
        for score, row, labels in chosen
    ]


def _normative_query(heading: str, methodology_ids: Sequence[str]) -> str:
    """Build the normative FTS query from heading words plus methodology ids."""
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", (heading or "").lower())
        if len(word) >= 4 and word not in _NORMATIVE_STOP_WORDS
    ]
    parts = [f'"{word}"' for word in words]
    parts.extend(
        _quote_fts(methodology_id)
        for methodology_id in methodology_ids
        if str(methodology_id).strip()
    )
    return " OR ".join(parts)


def select_normative(
    heading: str,
    profile: ProjectProfile,
    index: RetrievalIndex,
    methodology_documents: Sequence[str],
    k: int = 3,
) -> list[RetrievalResult]:
    """Retrieve methodology chunks for a section heading (S-2)."""
    method_docs = list(methodology_documents or [])
    if not method_docs:
        return []
    query = _normative_query(heading, profile.methodology_ids)
    if not query:
        return []
    hits = index.search(query, document_names=method_docs, k=k)
    total = len(hits)
    results = []
    for rank, hit in enumerate(hits):
        text = hit.get("text", "")
        lowered = text.lower()
        methods = [m for m in profile.methodology_ids if m and m.lower() in lowered]
        results.append(
            RetrievalResult(
                section_id=hit.get("section_id") or "",
                sub_section_id=hit.get("sub_section_id") or "",
                document_name=hit["document_name"],
                canonical_heading=hit.get("canonical_heading", ""),
                text=text,
                content_class=hit.get("content_class") or "",
                review_sensitivity=hit.get("review_sensitivity") or "",
                score=(1.0 - rank / total) if total else 0.0,
                matched_terms=[f"methodology:{m}" for m in methods] or ["normative"],
                channel="normative",
            )
        )
    return results


def ground_section(
    section_id: str,
    sub_section_id: str | None,
    heading: str,
    project_input: Any | None,
    k: int = 5,
    index: RetrievalIndex | None = None,
    exclude_documents: Sequence[str] | None = None,
    config_path: Path | None = None,
) -> Grounding:
    """Ground one section on ranked precedent plus normative methodology hits."""
    if index is None:
        index = get_retrieval_index()
    if not index.is_built():
        _warn_no_index_once()
        return Grounding([], [], [], False)
    families, registry_ids, methodology_documents = load_corpus_config(config_path)
    profile = profile_from_project(project_input)
    if exclude_documents is None:
        excluded = exclusion_set(profile.vcs_id, registry_ids)
    else:
        excluded = frozenset(exclude_documents)
    excluded_documents = sorted(excluded)
    for stem in excluded_documents:
        logger.info("grounding_self_excluded", document=stem, section_id=section_id)
    precedent = select_precedent(
        section_id,
        sub_section_id,
        profile,
        k,
        index,
        excluded,
        frozenset(methodology_documents),
        families,
    )
    from_fallback = any(result.from_fallback_family for result in precedent)
    if len(precedent) < 2:
        seen = {(result.document_name, result.canonical_heading) for result in precedent}
        cap = min(3, k)
        added = 0
        for extra in get_section_heading_examples(heading or "", k=cap, index=index):
            if added >= cap:
                break
            if extra.document_name in excluded:
                continue
            if (extra.document_name, extra.canonical_heading) in seen:
                continue
            seen.add((extra.document_name, extra.canonical_heading))
            extra.score = 0.0
            extra.matched_terms = ["heading-fallback"]
            precedent.append(extra)
            added += 1
    normative = select_normative(heading or "", profile, index, methodology_documents, k=3)
    return Grounding(precedent, normative, excluded_documents, from_fallback)
