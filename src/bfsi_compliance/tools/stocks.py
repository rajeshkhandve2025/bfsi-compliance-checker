"""Stock market tools — concepts, basics, regulatory info, taxation."""

import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent.parent / "rules" / "stocks_rules.json"


def _load() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def stock_explain_concept(concept: str) -> dict:
    """
    Explain a stock market concept in simple language.
    Examples: Bull Market, Bear Market, Circuit Breaker, Dividend, P/E Ratio,
    Demat Account, Stop Loss, SIP, Intraday, F&O, Buyback, Bonus Shares, etc.
    """
    data = _load()

    # Search across multiple sections
    all_concepts = {}
    all_concepts.update(data.get("basics", {}))
    all_concepts.update(data.get("market_concepts", {}))
    all_concepts.update(data.get("order_types", {}))
    all_concepts.update(data.get("trading_types", {}))
    all_concepts.update(data.get("fundamental_analysis", {}).get("key_metrics", {}))

    concept_lower = concept.strip().lower()

    for key, value in all_concepts.items():
        if key.lower() == concept_lower or concept_lower in key.lower():
            return {
                "domain": data["domain"],
                "concept": key,
                "explanation": value if isinstance(value, str) else value,
                "disclaimer": data["disclaimer"],
            }

    return {
        "found": False,
        "queried_concept": concept,
        "suggestion": (
            "Try concepts like: Bull Market, Bear Market, Demat Account, "
            "P/E Ratio, Stop Loss, Intraday, Dividend, Buyback, Circuit Breaker, "
            "Market Order, Limit Order, F&O"
        ),
    }


def stock_market_basics() -> dict:
    """
    Get a complete beginner's guide to the Indian stock market.
    Covers BSE, NSE, SENSEX, NIFTY, Demat account, trading account,
    T+1 settlement, types of trading, and common mistakes to avoid.
    """
    data = _load()
    return {
        "domain": data["domain"],
        "regulator": data["regulator"],
        "exchanges": data["exchanges"],
        "basics": data["basics"],
        "types_of_trading": data["trading_types"],
        "order_types": data["order_types"],
        "settlement": data["settlement"],
        "common_mistakes_to_avoid": data["common_mistakes"],
        "where_to_learn": data["where_to_learn"],
        "disclaimer": data["disclaimer"],
    }


def stock_regulatory_info(topic: str = "all") -> dict:
    """
    Get SEBI regulations and investor protections for stock market investors in India.
    topic: 'taxation', 'investor_protection', 'fundamental_analysis', or 'all'.
    """
    data = _load()
    topic = topic.lower().strip()

    if topic == "taxation":
        return {
            "domain": data["domain"],
            "topic": "Taxation on Stock Market Gains (FY 2025-26)",
            "taxation": data["taxation"],
            "note": "Revised rates as per Finance Act 2024, effective 23 July 2024.",
            "disclaimer": data["disclaimer"],
        }

    if topic == "investor_protection":
        return {
            "domain": data["domain"],
            "topic": "SEBI Investor Protections",
            "sebi_investor_protections": data["sebi_investor_protections"],
            "complaint_portal": "https://scores.sebi.gov.in",
        }

    if topic == "fundamental_analysis":
        return {
            "domain": data["domain"],
            "topic": "Fundamental Analysis — Key Metrics",
            "fundamental_analysis": data["fundamental_analysis"],
        }

    if topic == "all":
        return {
            "domain": data["domain"],
            "regulator": data["regulator"],
            "applicable_law": data["applicable_law"],
            "sebi_investor_protections": data["sebi_investor_protections"],
            "taxation": data["taxation"],
            "fundamental_analysis": data["fundamental_analysis"],
            "disclaimer": data["disclaimer"],
        }

    return {
        "error": f"Unknown topic '{topic}'.",
        "available_topics": ["taxation", "investor_protection", "fundamental_analysis", "all"],
    }
