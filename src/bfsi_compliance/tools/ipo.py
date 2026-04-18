"""IPO tools — process, concepts, investor categories, eligibility."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "ipo_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def ipo_explain_process() -> dict:
    """
    Explain the complete IPO application process step-by-step for a layman.
    Covers ASBA, Demat account requirement, cut-off price, allotment, and listing.
    """
    data = _load()
    return {
        "domain": data["domain"],
        "definition": data["definition"],
        "simple_analogy": data["simple_analogy"],
        "types_of_ipo": data["types"],
        "step_by_step_process": data["how_to_apply"],
        "sebi_investor_protections": data["sebi_investor_protections"],
        "risks": data["risks"],
        "disclaimer": data["disclaimer"],
    }


def ipo_list_concepts(concept: str = "all") -> dict:
    """
    Explain IPO concepts in plain language.
    concept: a specific term like 'GMP', 'ASBA', 'Price Band', 'Lot Size',
    'Cut-off Price', 'Oversubscription', 'DRHP', 'OFS', etc. — or 'all'.
    """
    data = _load()
    concepts = data.get("key_terms", {})

    if concept.lower() == "all":
        return {
            "domain": data["domain"],
            "total_concepts": len(concepts),
            "concepts": concepts,
        }

    concept_lower = concept.strip().lower()
    for key, value in concepts.items():
        if key.lower() == concept_lower or concept_lower in key.lower():
            return {
                "domain": data["domain"],
                "concept": key,
                "explanation": value,
            }

    return {
        "found": False,
        "queried_concept": concept,
        "available_concepts": list(concepts.keys()),
        "suggestion": f"Try 'all' to see all concepts, or check spelling.",
    }


def ipo_eligibility_guide(investor_type: str = "all") -> dict:
    """
    Explain IPO investor categories and eligibility.
    investor_type: 'retail', 'hni', 'qib', 'employee', or 'all'.
    Covers application limits, reservations, and allotment method for each category.
    """
    data = _load()
    categories = data.get("investor_categories", [])

    type_map = {
        "retail": "RII",
        "rii": "RII",
        "hni": "NII",
        "nii": "NII",
        "qib": "QIB",
        "employee": "Employee",
        "shareholder": "Shareholder",
    }

    if investor_type.lower() == "all":
        return {
            "domain": data["domain"],
            "investor_categories": categories,
            "disclaimer": data["disclaimer"],
        }

    keyword = type_map.get(investor_type.lower(), investor_type)
    matched = [c for c in categories if keyword.upper() in c["category"].upper()]

    if not matched:
        return {
            "error": f"Investor type '{investor_type}' not found.",
            "available_types": list(type_map.keys()),
        }

    return {
        "domain": data["domain"],
        "investor_type": investor_type,
        "details": matched,
        "disclaimer": data["disclaimer"],
    }
