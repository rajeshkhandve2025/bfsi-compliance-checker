"""Tests for Insurance tools."""

from bfsi_compliance.tools.insurance import insurance_list_types, insurance_explain_concept, insurance_regulatory_info


def test_list_all_types():
    r = insurance_list_types("all")
    assert r["total_types"] >= 8
    categories = {t["category"] for t in r["types"]}
    assert "Life Insurance" in categories
    assert "Health Insurance" in categories
    assert "General Insurance" in categories


def test_list_life_only():
    r = insurance_list_types("life")
    assert all(t["category"] == "Life Insurance" for t in r["types"])
    names = [t["name"] for t in r["types"]]
    assert "Term Insurance" in names


def test_list_invalid_category():
    r = insurance_list_types("xyz")
    assert "error" in r


def test_explain_sum_assured():
    r = insurance_explain_concept("Sum Assured")
    assert "explanation" in r


def test_explain_csr():
    r = insurance_explain_concept("Claim Settlement Ratio")
    assert "explanation" in r


def test_explain_unknown_concept():
    r = insurance_explain_concept("Quantum Flux Coverage")
    assert r["found"] is False


def test_regulatory_all():
    r = insurance_regulatory_info("all")
    assert "regulations" in r
    assert "claim_settlement_timeline" in r["regulations"]


def test_regulatory_ombudsman():
    r = insurance_regulatory_info("ombudsman")
    assert "information" in r
    assert "50 lakh" in r["information"]
