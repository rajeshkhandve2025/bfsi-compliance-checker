"""Tests for the bfsifiles grounding layer integration."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_catalog_loads():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    assert len(cat.sources) == 29
    assert len(cat.topics) == 6


def test_catalog_topics():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    assert set(cat.topics.keys()) == {"mutual_funds", "insurance", "ipo", "stocks", "income_tax", "compliance"}


def test_red_flags_present():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    flags = cat.policy["red_flags"]
    assert "guaranteed returns" in flags
    assert "risk-free" in flags
    assert "will this stock go up" in flags


def test_disclaimer_mutual_funds():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    d = cat.disclaimer_for("mutual_funds")
    assert d
    assert "SEBI" in d or "investment" in d.lower()


def test_disclaimer_insurance():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    d = cat.disclaimer_for("insurance")
    assert d
    assert "IRDAI" in d or "insurance" in d.lower()


def test_disclaimer_tax():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    d = cat.disclaimer_for("income_tax")
    assert d


def test_disclaimer_compliance():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    # compliance topic has no disclaimer in YAML (regulatory info needs no consumer disclaimer)
    d = cat.disclaimer_for("compliance")
    assert isinstance(d, str)


def test_answer_validator_red_flag():
    from bfsi_compliance.grounding import get_catalog, AnswerValidator
    cat = get_catalog()
    v = AnswerValidator(cat)
    violations = v.validate(
        answer_text="You should buy this fund because it gives guaranteed returns.",
        topic_id="mutual_funds",
        cited_source_ids=["sebi"],
    )
    assert any("guaranteed returns" in viol for viol in violations)


def test_answer_validator_no_citation():
    from bfsi_compliance.grounding import get_catalog, AnswerValidator
    cat = get_catalog()
    v = AnswerValidator(cat)
    violations = v.validate(
        answer_text="NAV stands for Net Asset Value.",
        topic_id="mutual_funds",
        cited_source_ids=[],
    )
    assert any("require_citation" in viol for viol in violations)


def test_build_citation_sebi():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    citation = cat.build_citation("sebi", "SEBI Circular on Mutual Funds")
    assert citation
    assert "sebi" in citation.lower() or "SEBI" in citation


def test_primary_sources_mutual_funds():
    from bfsi_compliance.grounding import get_catalog
    cat = get_catalog()
    sources = cat.primary_sources_for("mutual_funds")
    source_ids = [s.id for s in sources]
    assert "sebi" in source_ids or "amfi" in source_ids


def test_live_nav_returns_data():
    from bfsi_compliance.tools.live_nav import mf_live_nav
    result = mf_live_nav("SBI")
    assert result.get("total_matches", 0) > 0
    assert result.get("nav_data")
    first = result["nav_data"][0]
    assert "scheme_name" in first
    assert "nav" in first
    assert "date" in first


def test_live_nav_no_match():
    from bfsi_compliance.tools.live_nav import mf_live_nav
    result = mf_live_nav("XYZNONEXISTENTFUND12345")
    assert result.get("status") == "no_results"


def test_live_nav_empty_filter():
    from bfsi_compliance.tools.live_nav import mf_live_nav
    result = mf_live_nav("")
    assert result.get("total_matches", 0) > 1000
    assert result.get("showing") == 20
