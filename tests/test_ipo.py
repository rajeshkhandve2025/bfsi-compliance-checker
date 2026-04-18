"""Tests for IPO tools."""

from bfsi_compliance.tools.ipo import ipo_explain_process, ipo_list_concepts, ipo_eligibility_guide


def test_explain_process():
    r = ipo_explain_process()
    assert "step_by_step_process" in r
    assert len(r["step_by_step_process"]) >= 8
    assert "risks" in r


def test_list_all_concepts():
    r = ipo_list_concepts("all")
    assert "concepts" in r
    assert "GMP (Grey Market Premium)" in r["concepts"]
    assert "ASBA" in r["concepts"]


def test_explain_asba():
    r = ipo_list_concepts("ASBA")
    assert r["concept"] == "ASBA"
    assert "blocked" in r["explanation"].lower()


def test_explain_gmp():
    r = ipo_list_concepts("GMP")
    assert "speculative" in r["explanation"].lower() or "unofficial" in r["explanation"].lower()


def test_explain_unknown_concept():
    r = ipo_list_concepts("UnknownTerm")
    assert r["found"] is False


def test_eligibility_retail():
    r = ipo_eligibility_guide("retail")
    assert len(r["details"]) >= 1
    detail = r["details"][0]
    assert "2 lakh" in detail["application_limit"]


def test_eligibility_all():
    r = ipo_eligibility_guide("all")
    assert len(r["investor_categories"]) >= 3


def test_eligibility_invalid():
    r = ipo_eligibility_guide("unknown_type")
    assert "error" in r
