"""
Chroma client (embedded/local mode) for retrieving guardrail policy clauses.
Embeds backend/policies/ap_policy.md, split one clause per `##` heading, so
llm_service.explain_decision() can ground its plain-English explanation in
the actual written policy instead of just echoing the rule name back. This
is what the original spec's Chroma diagram was missing: a real caller.

Deliberately ephemeral (no persistent volume — see PROGRESS.md's Phase 1
"known gaps" note on this). The collection is rebuilt from ap_policy.md on
first use after every container start, which is fine for a demo: the
policy doc is small, static, and version-controlled, not runtime data.
"""
from __future__ import annotations

import os
import re
from functools import lru_cache

import chromadb
from chromadb.config import Settings

from app.config import settings

_POLICY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "policies", "ap_policy.md"
)
_COLLECTION_NAME = "ap_policy"

_HEADING_RE = re.compile(r"^##\s+(.+?)\s*(?:\(([A-Z_]+)\))?\s*$", re.MULTILINE)


def _parse_clauses(md_text: str) -> list[dict]:
    """
    Splits ap_policy.md into one clause per `##` heading. Headings that end
    in a parenthetical like `(WITHIN_TOLERANCE_AND_THRESHOLD)` are tagged
    with that exact rule_applied value for precise retrieval; the H1 title
    before the first `##` is dropped.
    """
    matches = list(_HEADING_RE.finditer(md_text))
    clauses = []
    for i, m in enumerate(matches):
        heading, rule = m.group(1).strip(), m.group(2)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        body = md_text[start:end].strip()
        clauses.append({"heading": heading, "rule": rule, "text": f"{heading}\n\n{body}"})
    return clauses


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(
        path=settings.chroma_persist_dir,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    if collection.count() == 0:
        with open(_POLICY_PATH, encoding="utf-8") as f:
            clauses = _parse_clauses(f.read())
        if clauses:
            collection.add(
                ids=[c["rule"] or f"clause-{i}" for i, c in enumerate(clauses)],
                documents=[c["text"] for c in clauses],
                metadatas=[{"rule": c["rule"] or "", "heading": c["heading"]} for c in clauses],
            )
    return collection


def get_relevant_clauses(rule_applied: str, k: int = 2) -> list[str]:
    """
    Returns up to k policy clause texts relevant to rule_applied. Tries an
    exact metadata match first (every rule_applied value policy_engine.py
    can return has a corresponding tagged heading in ap_policy.md), then
    falls back to semantic similarity search — so an unrecognized or future
    rule name still retrieves something reasonable instead of nothing.
    """
    collection = _get_collection()

    exact = collection.get(where={"rule": rule_applied})
    docs = exact.get("documents") or []
    if docs:
        return docs[:k]

    results = collection.query(query_texts=[rule_applied], n_results=k)
    return (results.get("documents") or [[]])[0]
