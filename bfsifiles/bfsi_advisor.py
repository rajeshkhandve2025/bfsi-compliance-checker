"""
bfsi_advisor.py
================
Python loader and enforcement helper for the BFSI Public Advisor schema.

Features:
    * Load and validate bfsi_sources.yaml against bfsi_schema.json
    * Resolve topic/subtopic -> primary source(s)
    * Build citations in multiple styles (formal / inline / chatbot / footnote)
    * Enforce policy:
        - every answer must cite a primary source
        - red-flag phrases must not appear in bot answers
        - disclaimer injection by topic
    * Live-data helper for AMFI NAV (free public feed, no auth)

Dependencies:
    pip install pyyaml jsonschema requests
"""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validate as jsonschema_validate
from jsonschema import ValidationError


# ------------------------------------------------------------------ exceptions

class SchemaError(Exception):
    """Raised when the schema YAML fails structural validation."""


class PolicyViolation(Exception):
    """Raised when an answer violates enforcement policy."""


class TopicNotFound(Exception):
    """Raised when a requested topic/subtopic is not in the taxonomy."""


# ---------------------------------------------------------------- data classes

@dataclass
class Source:
    id: str
    name: str
    authority_type: str
    trust_level: str
    base_url: str
    domains: list[str]
    citation_templates: dict[str, str] = field(default_factory=dict)
    data_endpoints: list[dict] = field(default_factory=list)
    key_pages: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def is_primary(self) -> bool:
        return self.trust_level == "primary"


@dataclass
class Citation:
    source_id: str
    source_name: str
    document_title: str
    url: str
    trust_level: str
    access_date: str

    def render(self, style: str, template: str | None = None) -> str:
        """Render this citation using one of the configured templates."""
        if template is None:
            raise ValueError("Template must be supplied explicitly")
        return template.format(
            document_title=self.document_title,
            url=self.url,
            access_date=self.access_date,
            year=self.access_date.split("-")[0],
        )


# ---------------------------------------------------------------- main catalog

class SourceCatalog:
    """Loads, validates and exposes the BFSI source catalog."""

    def __init__(self, yaml_path: str | Path, schema_path: str | Path | None = None):
        self.yaml_path = Path(yaml_path)
        self.schema_path = Path(schema_path) if schema_path else None
        self.raw: dict[str, Any] = {}
        self.sources: dict[str, Source] = {}
        self.topics: dict[str, dict] = {}
        self.policy: dict[str, Any] = {}
        self._load()

    # -- loading --

    def _load(self) -> None:
        with self.yaml_path.open("r", encoding="utf-8") as f:
            self.raw = yaml.safe_load(f)

        if self.schema_path:
            self._validate_against_schema()

        self._build_sources()
        self.topics = self.raw["topics"]
        self.policy = self.raw["policy"]
        self._validate_references()

    def _validate_against_schema(self) -> None:
        with self.schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        try:
            jsonschema_validate(instance=self.raw, schema=schema)
        except ValidationError as e:
            raise SchemaError(
                f"Schema validation failed at {list(e.absolute_path)}: {e.message}"
            ) from e

    def _build_sources(self) -> None:
        for sid, s in self.raw["sources"].items():
            self.sources[sid] = Source(
                id=sid,
                name=s["name"],
                authority_type=s["authority_type"],
                trust_level=s["trust_level"],
                base_url=s["base_url"],
                domains=s["domains"],
                citation_templates=s.get("citation_templates", {}),
                data_endpoints=s.get("data_endpoints", []),
                key_pages=s.get("key_pages", {}),
                raw=s,
            )

    def _validate_references(self) -> None:
        """Cross-check: every topic's primary_source must exist in sources catalog."""
        for topic_id, topic in self.topics.items():
            for src_id in topic.get("primary_sources", []):
                if src_id not in self.sources:
                    raise SchemaError(
                        f"topics.{topic_id}.primary_sources references "
                        f"unknown source '{src_id}'"
                    )
            for subtopic_id, subtopic in topic.get("subtopics", {}).items():
                ps = subtopic.get("primary_source")
                if ps and ps not in self.sources:
                    raise SchemaError(
                        f"topics.{topic_id}.subtopics.{subtopic_id}"
                        f".primary_source references unknown source '{ps}'"
                    )

    # -- lookups --

    def get_source(self, source_id: str) -> Source:
        if source_id not in self.sources:
            raise KeyError(f"Unknown source: {source_id}")
        return self.sources[source_id]

    def get_topic(self, topic_id: str) -> dict:
        if topic_id not in self.topics:
            raise TopicNotFound(f"Unknown topic: {topic_id}")
        return self.topics[topic_id]

    def get_subtopic(self, topic_id: str, subtopic_id: str) -> dict:
        topic = self.get_topic(topic_id)
        st = topic.get("subtopics", {}).get(subtopic_id)
        if not st:
            raise TopicNotFound(f"Unknown subtopic: {topic_id}.{subtopic_id}")
        return st

    def primary_sources_for(self, topic_id: str, subtopic_id: str | None = None) -> list[Source]:
        """Return primary source(s) authoritative for a topic or subtopic."""
        if subtopic_id:
            st = self.get_subtopic(topic_id, subtopic_id)
            return [self.get_source(st["primary_source"])]
        return [self.get_source(sid) for sid in self.get_topic(topic_id)["primary_sources"]]

    def data_endpoints_for(self, topic_id: str, subtopic_id: str) -> list[dict]:
        """Look up any declared data endpoints for a subtopic (e.g. AMFI NAV feed)."""
        st = self.get_subtopic(topic_id, subtopic_id)
        refs = st.get("data_endpoints", [])  # strings of form "source.endpoint_id"
        out = []
        for ref in refs:
            if "." in ref:
                src_id, ep_id = ref.split(".", 1)
                src = self.get_source(src_id)
                for ep in src.data_endpoints:
                    if ep["id"] == ep_id:
                        out.append({**ep, "source_id": src_id})
        return out

    # -- citation building --

    def build_citation(
        self,
        source_id: str,
        document_title: str,
        url: str | None = None,
        style: str = "chatbot",
    ) -> str:
        src = self.get_source(source_id)
        template = src.citation_templates.get(style)
        if not template:
            template = "{document_title} ({source_name}) — {url}".replace(
                "{source_name}", src.name
            )
        if url is None:
            url = src.base_url
        return template.format(
            document_title=document_title,
            url=url,
            access_date=date.today().isoformat(),
            year=date.today().year,
        )

    # -- disclaimer resolution --

    def disclaimer_for(self, topic_id: str, subtopic_id: str | None = None) -> str:
        st = None
        if subtopic_id:
            try:
                st = self.get_subtopic(topic_id, subtopic_id)
            except TopicNotFound:
                pass
        disclaimer_key = (st or {}).get("disclaimer") or self.get_topic(topic_id).get("disclaimer")
        if not disclaimer_key:
            return ""
        return self.policy["disclaimers"].get(disclaimer_key, "").strip()


# ----------------------------------------------------------------- enforcement

class AnswerValidator:
    """
    Enforces the schema's `policy` block on a generated answer before it is
    returned to the end-user.  Use as a final gate in your retrieval layer.
    """

    CITATION_MARKER = re.compile(r"\[[^\]]+\]\([^)]+\)|https?://\S+")

    def __init__(self, catalog: SourceCatalog):
        self.catalog = catalog
        self.policy = catalog.policy

    def validate(
        self,
        *,
        answer_text: str,
        topic_id: str,
        subtopic_id: str | None = None,
        cited_source_ids: list[str],
    ) -> list[str]:
        """Return a list of violation messages; empty list = OK."""
        violations: list[str] = []

        # 1) citation required
        if self.policy.get("require_citation") and not cited_source_ids:
            violations.append("policy.require_citation: no source cited")

        # 2) at least N primary sources
        primary_cited = [s for s in cited_source_ids
                         if s in self.catalog.sources
                         and self.catalog.sources[s].is_primary()]
        min_primary = self.policy.get("min_primary_sources_per_answer", 1)
        if len(primary_cited) < min_primary:
            violations.append(
                f"policy.min_primary_sources_per_answer: got "
                f"{len(primary_cited)}, need {min_primary}"
            )

        # 3) cited sources must be authoritative for this topic
        authoritative_ids = {s.id for s in
                             self.catalog.primary_sources_for(topic_id, subtopic_id)}
        # also allow topic-level primaries as fallback
        try:
            authoritative_ids |= {s.id for s in
                                  self.catalog.primary_sources_for(topic_id)}
        except TopicNotFound:
            pass

        off_topic = [s for s in primary_cited if s not in authoritative_ids]
        if off_topic and self.policy.get("reject_if_no_primary_source"):
            if not (set(primary_cited) & authoritative_ids):
                violations.append(
                    f"policy.reject_if_no_primary_source: cited sources "
                    f"{primary_cited} are not authoritative for "
                    f"{topic_id}.{subtopic_id or '*'}"
                )

        # 4) disclaimer present if required
        if self.policy.get("must_include_disclaimer"):
            expected = self.catalog.disclaimer_for(topic_id, subtopic_id)
            if expected and expected[:40].lower() not in answer_text.lower():
                violations.append(
                    "policy.must_include_disclaimer: expected disclaimer not present"
                )

        # 5) red-flag phrases
        lowered = answer_text.lower()
        for phrase in self.policy.get("red_flags", []):
            if phrase.lower() in lowered:
                violations.append(f"policy.red_flag: answer contains '{phrase}'")

        return violations


# ----------------------------------------------------------------- live helpers

def fetch_amfi_nav(catalog: SourceCatalog) -> list[dict]:
    """Pull the public AMFI NAV feed and return as list of dicts. No auth."""
    amfi = catalog.get_source("amfi")
    endpoint = next((e for e in amfi.data_endpoints if e["id"] == "nav_all"), None)
    if not endpoint:
        raise RuntimeError("AMFI nav_all endpoint not configured")

    with urllib.request.urlopen(endpoint["url"], timeout=30) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    cols = endpoint["columns"]
    rows: list[dict] = []
    for line in raw.splitlines():
        parts = line.split(";")
        if len(parts) == len(cols) and parts[0].strip().isdigit():
            rows.append(dict(zip(cols, [p.strip() for p in parts])))
    return rows


# ----------------------------------------------------------------- CLI helper

if __name__ == "__main__":
    import sys
    base = Path(__file__).parent
    cat = SourceCatalog(base / "bfsi_sources.yaml", base / "bfsi_schema.json")
    print(f"[ok] loaded {len(cat.sources)} sources, {len(cat.topics)} topics")
    print(f"     schema v{cat.raw['meta']['version']}  "
          f"jurisdiction={cat.raw['meta']['jurisdiction']}  "
          f"fy={cat.raw['meta']['fiscal_year']}")
    if len(sys.argv) > 1 and sys.argv[1] == "--fetch-nav":
        navs = fetch_amfi_nav(cat)
        print(f"[ok] fetched {len(navs)} NAV rows from AMFI")
        for row in navs[:3]:
            print("     ", row)
