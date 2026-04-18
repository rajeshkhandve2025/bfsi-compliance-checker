"""Tests for Mutual Fund tools."""

from bfsi_compliance.tools.mutual_funds import mf_explain_concept, mf_list_categories, mf_tax_guide


def test_explain_nav():
    r = mf_explain_concept("NAV")
    assert r["concept"] == "NAV"
    assert "definition" in r
    assert "simple_analogy" in r


def test_explain_sip_alias():
    r = mf_explain_concept("Systematic Investment Plan")
    assert r["concept"] == "SIP"


def test_explain_elss():
    r = mf_explain_concept("ELSS")
    assert r["concept"] == "ELSS"
    assert "lock_in_period" in r


def test_explain_unknown():
    r = mf_explain_concept("XYZ Unknown")
    assert r["found"] is False
    assert "available_concepts" in r


def test_list_categories():
    r = mf_list_categories()
    assert r["total_categories"] >= 4
    names = [c["category"] for c in r["categories"]]
    assert "Equity Schemes" in names
    assert "Debt Schemes" in names


def test_tax_guide_all():
    r = mf_tax_guide("all")
    assert "tax_guide" in r
    assert "equity_funds" in r["tax_guide"]


def test_tax_guide_equity():
    r = mf_tax_guide("equity")
    assert r["fund_type"] == "equity"
    assert "short_term_capital_gain" in r["tax_details"]


def test_tax_guide_invalid():
    r = mf_tax_guide("unknown")
    assert "error" in r
