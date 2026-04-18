"""Insurance tools — types, concepts, IRDAI regulatory info."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "insurance_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def insurance_list_types(category: str = "all") -> dict:
    """
    List all insurance types with plain-language descriptions.
    category: 'life', 'health', 'general', or 'all'.
    """
    data = _load()
    category = category.lower().strip()

    category_map = {
        "life": "Life Insurance",
        "health": "Health Insurance",
        "general": "General Insurance",
    }

    if category == "all":
        return {
            "domain": data["domain"],
            "regulator": data["regulator"],
            "total_types": len(data["types"]),
            "types": data["types"],
            "how_to_choose": data["how_to_choose"],
            "disclaimer": data["disclaimer"],
        }

    filter_cat = category_map.get(category)
    if not filter_cat:
        return {
            "error": f"Unknown category '{category}'. Use: life, health, general, or all.",
        }

    filtered = [t for t in data["types"] if t["category"] == filter_cat]
    return {
        "domain": data["domain"],
        "category": filter_cat,
        "types": filtered,
        "disclaimer": data["disclaimer"],
    }


def insurance_explain_concept(concept: str) -> dict:
    """
    Explain an insurance concept in simple language.
    Examples: Sum Assured, Premium, Claim Settlement Ratio, Free Look Period,
    Surrender Value, Grace Period, Rider, Nominee, Pre-existing Disease.
    """
    data = _load()
    concepts = data.get("key_concepts", {})
    concept_lower = concept.strip().lower()

    for key, value in concepts.items():
        if key.lower() == concept_lower or concept_lower in key.lower():
            return {
                "concept": key,
                "explanation": value,
                "domain": data["domain"],
                "regulator": data["regulator"],
            }

    return {
        "found": False,
        "queried_concept": concept,
        "available_concepts": list(concepts.keys()),
        "error": f"Concept '{concept}' not found. Try one of the available concepts listed.",
    }


def insurance_regulatory_info(topic: str = "all") -> dict:
    """
    Get IRDAI regulatory information for insurance in India.
    Topics: 'kyc', 'claim', 'grievance', 'ombudsman', 'mis_selling', 'bima_sugam', or 'all'.
    """
    data = _load()
    regulations = data.get("irdai_regulations", {})
    topic = topic.lower().strip().replace(" ", "_")

    if topic == "all":
        return {
            "domain": data["domain"],
            "regulator": data["regulator"],
            "applicable_law": data["applicable_law"],
            "regulations": regulations,
            "disclaimer": data["disclaimer"],
        }

    topic_map = {
        "kyc": "know_your_customer",
        "claim": "claim_settlement_timeline",
        "grievance": "grievance_redressal",
        "ombudsman": "insurance_ombudsman",
        "mis_selling": "mis_selling_protection",
        "bima_sugam": "bima_sugam",
    }

    key = topic_map.get(topic, topic)
    if key not in regulations:
        return {
            "error": f"Topic '{topic}' not found.",
            "available_topics": list(topic_map.keys()),
        }

    return {
        "domain": data["domain"],
        "topic": topic,
        "information": regulations[key],
        "disclaimer": data["disclaimer"],
    }
