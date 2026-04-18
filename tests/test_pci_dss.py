"""Tests for PCI-DSS v4.0 compliance tools."""

from bfsi_compliance.tools.pci_dss import (
    pcidss_list_requirements,
    pcidss_check_requirement,
    pcidss_assess_control,
)


def test_list_requirements_has_12():
    result = pcidss_list_requirements()
    assert result["total_requirements"] == 12
    numbers = [r["requirement_number"] for r in result["requirements"]]
    assert "1" in numbers and "12" in numbers


def test_check_requirement_found():
    result = pcidss_check_requirement("3")
    assert result["found"] is True
    assert "PAN" in result["title"] or "Account" in result["title"]
    assert len(result["sub_requirements"]) >= 5


def test_check_requirement_not_found():
    result = pcidss_check_requirement("13")
    assert result["found"] is False


def test_assess_control_tls_match():
    result = pcidss_assess_control(
        "We use TLS 1.2 to encrypt cardholder data in transit. MFA is enforced."
    )
    matched = [r["requirement_number"] for r in result["applicable_requirements"]]
    assert "4" in matched  # TLS
    assert "8" in matched  # MFA


def test_assess_control_deprecated_protocol_warning():
    result = pcidss_assess_control(
        "Payment page uses SSL for encryption and stores cardholder data."
    )
    assert len(result["warnings"]) > 0
    assert any("deprecated" in w.lower() or "ssl" in w.lower() for w in result["warnings"])


def test_assess_control_no_match():
    result = pcidss_assess_control("We run a static HTML landing page with no forms.")
    assert result["matched_requirements"] == 0
