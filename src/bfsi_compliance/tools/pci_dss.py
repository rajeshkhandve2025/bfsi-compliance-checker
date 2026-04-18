"""PCI-DSS v4.0 compliance tools."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "pci_dss_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def pcidss_list_requirements() -> dict:
    """Return all 12 PCI-DSS v4.0 requirements with a one-line summary of each."""
    data = _load()
    summary = []
    for req in data["requirements"]:
        summary.append({
            "requirement_number": req["number"],
            "id": req["id"],
            "title": req["title"],
            "sub_requirement_count": len(req["sub_requirements"]),
        })
    return {
        "framework": data["framework"],
        "version": data["version"],
        "applicability": data["applicability"],
        "total_requirements": len(data["requirements"]),
        "requirements": summary,
    }


def pcidss_check_requirement(requirement_number: str) -> dict:
    """
    Return full details for a PCI-DSS requirement by number (1–12).
    Includes all sub-requirements and evidence expectations.
    """
    data = _load()
    number = str(requirement_number).strip()

    for req in data["requirements"]:
        if req["number"] == number:
            return {"found": True, **req}

    return {
        "found": False,
        "queried_number": number,
        "error": f"Requirement '{number}' not found. Valid numbers are 1 through 12.",
    }


def pcidss_assess_control(control_description: str) -> dict:
    """
    Assess a control description against PCI-DSS v4.0 requirements.
    Returns matching requirements and identifies potential gaps.
    """
    data = _load()
    description_lower = control_description.lower()

    # Keyword → requirement number mapping
    keyword_map = {
        "firewall": ["1"],
        "network segmentation": ["1"],
        "dmz": ["1"],
        "default password": ["2"],
        "hardening": ["2"],
        "configuration baseline": ["2"],
        "encryption": ["3", "4"],
        "cardholder data": ["3", "7", "10"],
        "pan": ["3", "4"],
        "tls": ["4"],
        "ssl": ["4"],
        "certificate": ["4"],
        "antivirus": ["5"],
        "malware": ["5"],
        "anti-malware": ["5"],
        "patch": ["6"],
        "vulnerability": ["6", "11"],
        "waf": ["6"],
        "sast": ["6"],
        "dast": ["6"],
        "access control": ["7"],
        "least privilege": ["7"],
        "rbac": ["7"],
        "mfa": ["8"],
        "multi-factor": ["8"],
        "password": ["8"],
        "authentication": ["8"],
        "physical access": ["9"],
        "cctv": ["9"],
        "media": ["9"],
        "logging": ["10"],
        "log": ["10"],
        "siem": ["10"],
        "audit": ["10"],
        "penetration test": ["11"],
        "pentest": ["11"],
        "vulnerability scan": ["11"],
        "fim": ["11"],
        "policy": ["12"],
        "awareness": ["12"],
        "training": ["12"],
        "third party": ["12"],
        "vendor": ["12"],
        "incident response": ["12"],
    }

    matched_req_numbers: set[str] = set()
    for keyword, req_numbers in keyword_map.items():
        if keyword in description_lower:
            matched_req_numbers.update(req_numbers)

    applicable_requirements = []
    for req in data["requirements"]:
        if req["number"] in matched_req_numbers:
            applicable_requirements.append({
                "requirement_number": req["number"],
                "title": req["title"],
                "key_sub_requirements": req["sub_requirements"][:3],
                "evidence_needed": req["evidence"],
            })

    # Flag protocol-specific gaps
    warnings = []
    if any(p in description_lower for p in ["ssl", "tls 1.0", "tls 1.1"]):
        warnings.append(
            "Deprecated protocol detected (SSL/TLS 1.0/1.1). PCI-DSS 4.0 requires TLS 1.2 minimum."
        )

    return {
        "framework": data["framework"],
        "control_description": control_description[:200],
        "matched_requirements": len(applicable_requirements),
        "applicable_requirements": applicable_requirements,
        "warnings": warnings,
        "assessment_note": (
            "Keyword-based heuristic assessment. "
            "Use pcidss_check_requirement for authoritative requirement text."
        ),
    }
