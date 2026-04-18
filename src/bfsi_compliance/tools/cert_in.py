"""CERT-In Directions compliance tools."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "cert_in_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def certin_list_directives() -> dict:
    """Return all CERT-In directives with a brief summary of each."""
    data = _load()
    summary = []
    for directive in data["directives"]:
        summary.append({
            "id": directive["id"],
            "title": directive["title"],
            "description": directive["description"][:120] + "...",
        })
    return {
        "framework": data["framework"],
        "version": data["version"],
        "applicability": data["applicability"],
        "total_directives": len(data["directives"]),
        "directives": summary,
    }


def certin_check_directive(directive_id: str) -> dict:
    """Return full details for a specific CERT-In directive by ID (e.g. CERTIN-3)."""
    data = _load()
    directive_id = directive_id.upper().strip()

    for directive in data["directives"]:
        if directive["id"] == directive_id:
            return {"found": True, **directive}

    return {
        "found": False,
        "queried_id": directive_id,
        "error": f"Directive '{directive_id}' not found. Valid IDs: CERTIN-1 through CERTIN-6.",
    }


def certin_assess_incident_response(ir_plan_description: str) -> dict:
    """
    Assess an Incident Response plan description against CERT-In mandates.
    Checks for reporting timeliness, NTP sync, log retention, and PoC requirements.
    """
    data = _load()
    description_lower = ir_plan_description.lower()

    gaps = []
    compliant_items = []

    # CERTIN-1: 6-hour reporting
    if any(kw in description_lower for kw in ["6 hour", "six hour", "cert-in report", "certin report", "incident report"]):
        compliant_items.append("Incident reporting to CERT-In within 6 hours — addressed")
    else:
        gaps.append({
            "directive": "CERTIN-1",
            "gap": "No mention of 6-hour mandatory reporting window to CERT-In.",
            "requirement": "All cyber incidents must be reported to CERT-In within 6 hours of detection.",
        })

    # CERTIN-2: NTP synchronisation
    if any(kw in description_lower for kw in ["ntp", "time sync", "npl", "nplindia"]):
        compliant_items.append("NTP synchronisation with NPL/NIC — addressed")
    else:
        gaps.append({
            "directive": "CERTIN-2",
            "gap": "No mention of NTP synchronisation with NPL or NIC servers.",
            "requirement": "All ICT systems must sync with time.nplindia.org or time.nic.in.",
        })

    # CERTIN-3: Log retention
    if any(kw in description_lower for kw in ["180 day", "6 month", "log retention", "log storage"]):
        compliant_items.append("Log retention period — addressed")
    else:
        gaps.append({
            "directive": "CERTIN-3",
            "gap": "Log retention period of 180 days not explicitly mentioned.",
            "requirement": "All ICT system logs must be retained for a minimum of 180 days within India.",
        })

    # CERTIN-4: Point of Contact
    if any(kw in description_lower for kw in ["point of contact", "poc", "cert-in portal", "certin portal"]):
        compliant_items.append("Designated CERT-In PoC — addressed")
    else:
        gaps.append({
            "directive": "CERTIN-4",
            "gap": "No mention of a designated 24x7 Point of Contact registered with CERT-In.",
            "requirement": "A PoC must be registered on the CERT-In portal and be reachable 24x7.",
        })

    compliance_score = len(compliant_items) / (len(compliant_items) + len(gaps)) * 100 if (compliant_items or gaps) else 0

    return {
        "framework": data["framework"],
        "ir_plan_excerpt": ir_plan_description[:200],
        "compliance_score_percent": round(compliance_score, 1),
        "compliant_items": compliant_items,
        "gaps_identified": len(gaps),
        "gaps": gaps,
        "recommendation": (
            "Address all gaps before the next CERT-In audit. "
            "Use certin_check_directive for full directive text."
        ),
    }
