"""India Income Tax tools for FY 2025-26."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "india_tax_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def tax_compare_regimes(annual_income: float, total_deductions: float = 0) -> dict:
    """
    Compare Old vs New tax regime for FY 2025-26 based on income and deductions.
    annual_income: gross annual income in rupees (e.g. 1200000 for ₹12 lakh).
    total_deductions: total deductions claimed under old regime (80C, 80D, HRA, etc.).
    Returns tax under both regimes and a recommendation.
    """

    def compute_new_regime_tax(income: float) -> float:
        std_deduction = 75000
        taxable = max(0, income - std_deduction)
        slabs = [
            (400000, 0.00),
            (400000, 0.05),
            (400000, 0.10),
            (400000, 0.15),
            (400000, 0.20),
            (400000, 0.25),
            (float("inf"), 0.30),
        ]
        thresholds = [0, 400000, 800000, 1200000, 1600000, 2000000, 2400000]
        tax = 0.0
        for i, (band, rate) in enumerate(slabs):
            lower = thresholds[i]
            if taxable <= lower:
                break
            upper = lower + band
            taxable_in_band = min(taxable, upper) - lower
            tax += taxable_in_band * rate
        # Rebate 87A: if income (before std deduction) <= 12 lakh, rebate up to 60000
        if income <= 1200000:
            tax = max(0, tax - 60000)
        return tax

    def compute_old_regime_tax(income: float, deductions: float) -> float:
        std_deduction = 50000
        taxable = max(0, income - std_deduction - deductions)
        slabs = [
            (250000, 0.00),
            (250000, 0.05),
            (500000, 0.20),
            (float("inf"), 0.30),
        ]
        thresholds = [0, 250000, 500000, 1000000]
        tax = 0.0
        for i, (band, rate) in enumerate(slabs):
            lower = thresholds[i]
            if taxable <= lower:
                break
            upper = lower + band
            taxable_in_band = min(taxable, upper) - lower
            tax += taxable_in_band * rate
        # Rebate 87A: if taxable <= 5 lakh, rebate up to 12500
        if taxable <= 500000:
            tax = max(0, tax - 12500)
        return tax

    new_tax = compute_new_regime_tax(annual_income)
    old_tax = compute_old_regime_tax(annual_income, total_deductions)
    cess_new = new_tax * 0.04
    cess_old = old_tax * 0.04
    total_new = new_tax + cess_new
    total_old = old_tax + cess_old

    if total_new < total_old:
        recommendation = "New Regime is better — saves ₹{:,.0f} in tax.".format(total_old - total_new)
    elif total_old < total_new:
        recommendation = "Old Regime is better — saves ₹{:,.0f} in tax.".format(total_new - total_old)
    else:
        recommendation = "Both regimes result in the same tax liability."

    return {
        "financial_year": "FY 2025-26",
        "annual_income": f"₹{annual_income:,.0f}",
        "deductions_claimed_old_regime": f"₹{total_deductions:,.0f}",
        "new_regime": {
            "standard_deduction": "₹75,000",
            "income_tax": f"₹{new_tax:,.0f}",
            "health_education_cess_4pct": f"₹{cess_new:,.0f}",
            "total_tax_payable": f"₹{total_new:,.0f}",
        },
        "old_regime": {
            "standard_deduction": "₹50,000",
            "income_tax": f"₹{old_tax:,.0f}",
            "health_education_cess_4pct": f"₹{cess_old:,.0f}",
            "total_tax_payable": f"₹{total_old:,.0f}",
        },
        "recommendation": recommendation,
        "note": "Surcharge not included. For income above ₹50 lakh, consult a CA.",
        "disclaimer": "This is an indicative calculation. Consult a Chartered Accountant for precise tax planning.",
    }


def tax_explain_deduction(section: str) -> dict:
    """
    Explain a specific income tax deduction section for FY 2025-26.
    Examples: '80C', '80D', '80CCD1B', 'HRA', 'LTA', '24b', '80E', '80G', '80TTA', '80TTB'.
    """
    data = _load()
    deductions = data.get("key_deductions_old_regime", {})
    section_key = section.strip().upper().replace(" ", "_")

    # Normalise common inputs
    aliases = {
        "80C": "section_80C",
        "80D": "section_80D",
        "80CCD1B": "section_80CCD1B",
        "80CCD(1B)": "section_80CCD1B",
        "80CCD2": "section_80CCD2",
        "80CCD(2)": "section_80CCD2",
        "24B": "section_24b",
        "24(B)": "section_24b",
        "80E": "section_80E",
        "80G": "section_80G",
        "80TTA": "section_80TTA",
        "80TTB": "section_80TTB",
        "HRA": "HRA",
        "LTA": "LTA",
    }

    key = aliases.get(section_key)
    if key and key in deductions:
        return {
            "financial_year": "FY 2025-26",
            "section": section.upper(),
            "available_in": "Old Regime only (except 80CCD2 which is available in both)",
            **deductions[key],
            "disclaimer": data["disclaimer"],
        }

    return {
        "found": False,
        "queried_section": section,
        "available_sections": list(aliases.keys()),
        "error": f"Section '{section}' not found. Try one of the available sections.",
    }


def tax_capital_gains_guide(asset_type: str = "all") -> dict:
    """
    Explain capital gains tax rules for FY 2025-26.
    asset_type: 'equity', 'debt_mf', 'real_estate', 'gold', 'crypto', or 'all'.
    """
    data = _load()
    cg = data.get("capital_gains_tax", {})

    type_map = {
        "equity": "equity_shares_equity_mf",
        "stocks": "equity_shares_equity_mf",
        "mutual funds": "equity_shares_equity_mf",
        "debt_mf": "debt_mutual_funds_post_april_2023",
        "debt": "debt_mutual_funds_post_april_2023",
        "real_estate": "real_estate",
        "property": "real_estate",
        "gold": "gold_physical",
        "crypto": None,
        "vda": None,
    }

    asset_lower = asset_type.lower().strip()

    if asset_lower == "all":
        return {
            "financial_year": "FY 2025-26",
            "capital_gains_tax": cg,
            "crypto_vda": data.get("crypto_vda_tax"),
            "note": "Rates revised by Finance Act 2024, effective 23 July 2024.",
            "disclaimer": data["disclaimer"],
        }

    if asset_lower in ("crypto", "vda"):
        return {
            "financial_year": "FY 2025-26",
            "asset_type": "Crypto / Virtual Digital Assets (VDA)",
            **data.get("crypto_vda_tax", {}),
            "disclaimer": data["disclaimer"],
        }

    key = type_map.get(asset_lower)
    if not key or key not in cg:
        return {
            "error": f"Asset type '{asset_type}' not found.",
            "available_types": ["equity", "debt_mf", "real_estate", "gold", "crypto", "all"],
        }

    return {
        "financial_year": "FY 2025-26",
        "asset_type": asset_type,
        "capital_gains_details": cg[key],
        "note": "Rates revised by Finance Act 2024, effective 23 July 2024.",
        "disclaimer": data["disclaimer"],
    }
