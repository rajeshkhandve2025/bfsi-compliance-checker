"""RBI Cyber Security Framework compliance tools."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "rbi_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def rbi_list_controls() -> dict:
    """Return all RBI CSF domains and a summary of their controls."""
    data = _load()
    summary = []
    for domain in data["domains"]:
        summary.append({
            "domain_id": domain["id"],
            "domain": domain["domain"],
            "description": domain["description"],
            "control_count": len(domain["controls"]),
            "control_ids": [c["id"] for c in domain["controls"]],
        })
    return {
        "framework": data["framework"],
        "version": data["version"],
        "applicability": data["applicability"],
        "total_domains": len(data["domains"]),
        "total_controls": sum(len(d["controls"]) for d in data["domains"]),
        "domains": summary,
    }


def rbi_check_control(control_id: str) -> dict:
    """Return full details for a specific RBI CSF control by ID (e.g. RBI-CSF-2.1)."""
    data = _load()
    control_id = control_id.upper().strip()

    # Support domain-level lookup (e.g. "RBI-CSF-2")
    if control_id.count("-") == 2 and "." not in control_id:
        for domain in data["domains"]:
            if domain["id"] == control_id:
                return {"found": True, "type": "domain", **domain}
        return {"found": False, "queried_id": control_id, "error": f"Domain '{control_id}' not found."}

    for domain in data["domains"]:
        for control in domain["controls"]:
            if control["id"] == control_id:
                return {
                    "found": True,
                    "type": "control",
                    "domain": domain["domain"],
                    **control,
                }

    return {
        "found": False,
        "queried_id": control_id,
        "error": f"Control '{control_id}' not found. Use rbi_list_controls to see valid IDs.",
    }


def rbi_assess_system(system_description: str) -> dict:
    """
    Assess a plain-text system description against RBI CSF.
    Returns a list of potentially applicable controls and gaps based on
    keywords in the description.
    """
    data = _load()
    description_lower = system_description.lower()

    # Keyword → control ID mapping for heuristic matching
    keyword_map = {
        "policy": ["RBI-CSF-1.1"],
        "ciso": ["RBI-CSF-1.2"],
        "governance": ["RBI-CSF-1.2", "RBI-CSF-1.3"],
        "firewall": ["RBI-CSF-2.1"],
        "network": ["RBI-CSF-2.1"],
        "endpoint": ["RBI-CSF-2.2"],
        "antivirus": ["RBI-CSF-2.2"],
        "patch": ["RBI-CSF-2.4"],
        "data centre": ["RBI-CSF-2.3"],
        "datacenter": ["RBI-CSF-2.3"],
        "soc": ["RBI-CSF-3.1"],
        "siem": ["RBI-CSF-3.1"],
        "incident": ["RBI-CSF-3.2", "RBI-CSF-3.3"],
        "sdlc": ["RBI-CSF-4.1"],
        "application": ["RBI-CSF-4.1", "RBI-CSF-4.2"],
        "internet banking": ["RBI-CSF-4.2"],
        "mfa": ["RBI-CSF-4.2"],
        "api": ["RBI-CSF-4.3"],
        "bcp": ["RBI-CSF-5.1"],
        "business continuity": ["RBI-CSF-5.1"],
        "penetration test": ["RBI-CSF-5.2"],
        "red team": ["RBI-CSF-5.2"],
    }

    matched_ids: set[str] = set()
    for keyword, ids in keyword_map.items():
        if keyword in description_lower:
            matched_ids.update(ids)

    applicable_controls = []
    for domain in data["domains"]:
        for control in domain["controls"]:
            if control["id"] in matched_ids:
                applicable_controls.append({
                    "control_id": control["id"],
                    "title": control["title"],
                    "requirement": control["requirement"],
                    "evidence_needed": control["evidence"],
                })

    return {
        "framework": data["framework"],
        "system_description": system_description[:200],
        "matched_controls": len(applicable_controls),
        "assessment_note": (
            "This is a keyword-based heuristic assessment. "
            "Use rbi_check_control for detailed requirements on specific controls."
        ),
        "applicable_controls": applicable_controls,
    }
