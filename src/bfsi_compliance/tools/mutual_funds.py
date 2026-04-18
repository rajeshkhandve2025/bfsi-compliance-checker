"""Mutual Fund tools — NAV, categories, tax guide."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "mutual_fund_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def mf_explain_concept(concept: str) -> dict:
    """
    Explain a Mutual Fund concept in simple language.
    Supported concepts: NAV, SIP, Expense Ratio, AUM, Exit Load, ELSS,
    Riskometer, Direct vs Regular Plan, KYC.
    """
    data = _load()
    concept_key = concept.strip().upper()

    # Normalise common aliases
    aliases = {
        "NET ASSET VALUE": "NAV",
        "SYSTEMATIC INVESTMENT PLAN": "SIP",
        "EXPENSE": "Expense Ratio",
        "EXPENSE RATIO": "Expense Ratio",
        "ASSETS UNDER MANAGEMENT": "AUM",
        "EXIT": "Exit Load",
        "EXIT LOAD": "Exit Load",
        "EQUITY LINKED SAVINGS SCHEME": "ELSS",
        "RISK": "Riskometer",
        "RISKOMETER": "Riskometer",
        "DIRECT": "Direct vs Regular Plan",
        "REGULAR": "Direct vs Regular Plan",
        "DIRECT VS REGULAR": "Direct vs Regular Plan",
        "DIRECT PLAN": "Direct vs Regular Plan",
        "KYC": "KYC",
    }

    lookup_key = aliases.get(concept_key, concept.strip())

    concepts = data.get("concepts", {})
    for key, value in concepts.items():
        if key.upper() == lookup_key.upper():
            return {
                "concept": key,
                "framework": data["domain"],
                "regulator": data["regulator"],
                **value,
                "disclaimer": data["disclaimer"],
            }

    return {
        "found": False,
        "queried_concept": concept,
        "available_concepts": list(concepts.keys()),
        "error": f"Concept '{concept}' not found. Use one of the available concepts listed.",
    }


def mf_list_categories() -> dict:
    """
    List all SEBI-defined Mutual Fund categories (equity, debt, hybrid, etc.)
    with a plain-language description of each sub-category.
    """
    data = _load()
    return {
        "framework": data["domain"],
        "regulator": data["regulator"],
        "total_categories": len(data["sebi_mf_categories"]),
        "categories": data["sebi_mf_categories"],
        "how_to_invest": data["how_to_invest"],
        "disclaimer": data["disclaimer"],
    }


def mf_tax_guide(fund_type: str = "all") -> dict:
    """
    Explain the tax implications of Mutual Fund investments for FY 2025-26.
    fund_type: 'equity', 'debt', 'elss', or 'all'.
    """
    data = _load()
    tax = data["tax_guide"]
    fund_type = fund_type.lower().strip()

    if fund_type == "all":
        return {
            "framework": data["domain"],
            "financial_year": "FY 2025-26",
            "tax_guide": tax,
            "note": "Tax rates updated as per Finance Act 2024 (effective 23 July 2024).",
            "disclaimer": data["disclaimer"],
        }

    mapping = {"equity": "equity_funds", "debt": "debt_funds", "elss": "elss"}
    key = mapping.get(fund_type)
    if not key:
        return {
            "error": f"Unknown fund type '{fund_type}'. Use: equity, debt, elss, or all.",
            "available": list(mapping.keys()) + ["all"],
        }

    return {
        "framework": data["domain"],
        "financial_year": "FY 2025-26",
        "fund_type": fund_type,
        "tax_details": tax[key],
        "note": "Tax rates updated as per Finance Act 2024 (effective 23 July 2024).",
        "disclaimer": data["disclaimer"],
    }
