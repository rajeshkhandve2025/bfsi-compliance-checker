"""Tests for Stock market tools."""

from bfsi_compliance.tools.stocks import stock_explain_concept, stock_market_basics, stock_regulatory_info


def test_explain_bull_market():
    r = stock_explain_concept("Bull Market")
    assert "concept" in r
    assert "rising" in r["explanation"].lower() or "optimist" in r["explanation"].lower()


def test_explain_demat():
    r = stock_explain_concept("Demat Account")
    assert "concept" in r


def test_explain_pe_ratio():
    r = stock_explain_concept("P/E Ratio")
    assert "concept" in r


def test_explain_unknown():
    r = stock_explain_concept("Quantum Trading Engine")
    assert r["found"] is False
    assert "suggestion" in r


def test_market_basics():
    r = stock_market_basics()
    assert "basics" in r
    assert "BSE" in r["basics"]
    assert "Demat Account" in r["basics"]
    assert "common_mistakes_to_avoid" in r
    assert len(r["common_mistakes_to_avoid"]) >= 5


def test_regulatory_taxation():
    r = stock_regulatory_info("taxation")
    assert "taxation" in r
    assert "Short Term Capital Gain (STCG)" in r["taxation"]


def test_regulatory_investor_protection():
    r = stock_regulatory_info("investor_protection")
    assert "sebi_investor_protections" in r


def test_regulatory_invalid():
    r = stock_regulatory_info("xyz")
    assert "error" in r
