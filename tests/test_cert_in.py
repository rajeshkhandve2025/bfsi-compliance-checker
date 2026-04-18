"""Tests for CERT-In compliance tools."""

from bfsi_compliance.tools.cert_in import (
    certin_list_directives,
    certin_check_directive,
    certin_assess_incident_response,
)


def test_list_directives():
    result = certin_list_directives()
    assert result["total_directives"] >= 4
    assert all("id" in d and "title" in d for d in result["directives"])


def test_check_directive_found():
    result = certin_check_directive("CERTIN-1")
    assert result["found"] is True
    assert result["deadline_hours"] == 6


def test_check_directive_log_retention():
    result = certin_check_directive("CERTIN-3")
    assert result["found"] is True
    assert result["retention_period_months"] == 180
    assert result["data_residency"] == "India"


def test_check_directive_not_found():
    result = certin_check_directive("CERTIN-99")
    assert result["found"] is False


def test_assess_ir_plan_full_compliance():
    description = (
        "We report incidents to CERT-In within 6 hours. "
        "All systems are synced with NTP via time.nplindia.org. "
        "Log retention is 180 days. "
        "A Point of Contact is registered on the CERT-In portal and available 24x7."
    )
    result = certin_assess_incident_response(description)
    assert result["gaps_identified"] == 0
    assert result["compliance_score_percent"] == 100.0


def test_assess_ir_plan_with_gaps():
    description = "We have an incident response team but no formal reporting procedure."
    result = certin_assess_incident_response(description)
    assert result["gaps_identified"] >= 2
    assert result["compliance_score_percent"] < 50
