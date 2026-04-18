"""Tests for India Tax tools (FY 2025-26)."""

from bfsi_compliance.tools.india_tax import tax_compare_regimes, tax_explain_deduction, tax_capital_gains_guide


def test_compare_12_lakh_no_deductions():
    r = tax_compare_regimes(1200000, 0)
    assert "new_regime" in r
    assert "old_regime" in r
    # ₹12 lakh with no deductions — new regime should be NIL due to rebate
    assert r["new_regime"]["total_tax_payable"] == "₹0"


def test_compare_15_lakh_with_deductions():
    r = tax_compare_regimes(1500000, 375000)
    assert "recommendation" in r
    # With high deductions, old regime typically wins
    assert "₹" in r["new_regime"]["total_tax_payable"]


def test_compare_salary_salaried_75k_std_deduction():
    # ₹12 lakh — new regime rebate 87A makes it NIL
    r = tax_compare_regimes(1200000, 0)
    assert r["new_regime"]["total_tax_payable"] == "₹0"


def test_explain_80c():
    r = tax_explain_deduction("80C")
    assert "limit" in r
    assert "1,50,000" in r["limit"] or "1.5" in r["limit"]
    assert "eligible_investments" in r


def test_explain_80d():
    r = tax_explain_deduction("80D")
    assert "limits" in r


def test_explain_hra():
    r = tax_explain_deduction("HRA")
    assert "calculation" in r or "Calculation" in str(r)


def test_explain_invalid_section():
    r = tax_explain_deduction("99ZZZ")
    assert r["found"] is False
    assert "available_sections" in r


def test_capital_gains_equity():
    r = tax_capital_gains_guide("equity")
    assert "capital_gains_details" in r
    details = r["capital_gains_details"]
    assert "short_term" in details
    assert "20%" in details["short_term"]["rate"]


def test_capital_gains_crypto():
    r = tax_capital_gains_guide("crypto")
    assert "30%" in r["rate"]
    assert "no_loss_setoff" in r


def test_capital_gains_all():
    r = tax_capital_gains_guide("all")
    assert "capital_gains_tax" in r
    assert "crypto_vda" in r


def test_capital_gains_invalid():
    r = tax_capital_gains_guide("diamonds")
    assert "error" in r
