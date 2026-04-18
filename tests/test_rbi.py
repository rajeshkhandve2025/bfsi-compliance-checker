"""Tests for RBI CSF tools."""

from bfsi_compliance.tools.rbi_csf import (
    rbi_list_controls,
    rbi_check_control,
    rbi_assess_system,
)


def test_list_controls_returns_domains():
    result = rbi_list_controls()
    assert result["total_domains"] >= 5
    assert result["total_controls"] >= 10
    assert all("domain_id" in d for d in result["domains"])


def test_check_control_domain_level():
    result = rbi_check_control("RBI-CSF-2")
    assert result["found"] is True
    assert result["type"] == "domain"
    assert "controls" in result


def test_check_control_specific():
    result = rbi_check_control("rbi-csf-2.1")  # lowercase should work
    assert result["found"] is True
    assert result["type"] == "control"
    assert "requirement" in result
    assert "evidence" in result


def test_check_control_not_found():
    result = rbi_check_control("RBI-CSF-99.9")
    assert result["found"] is False
    assert "error" in result


def test_assess_system_firewall_match():
    result = rbi_assess_system("We have a firewall, SIEM, and incident response plan.")
    assert result["matched_controls"] >= 2
    ids = [c["control_id"] for c in result["applicable_controls"]]
    assert "RBI-CSF-2.1" in ids  # firewall → network security


def test_assess_system_no_match():
    result = rbi_assess_system("We sell vegetables online.")
    assert result["matched_controls"] == 0
