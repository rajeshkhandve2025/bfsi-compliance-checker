"""Live AMFI NAV tool — fetches real-time mutual fund NAV data."""

from __future__ import annotations


def mf_live_nav(scheme_name: str = "") -> dict:
    """Fetch live NAV from AMFI public feed. Optionally filter by scheme name."""
    try:
        from bfsi_compliance.grounding import get_catalog, fetch_amfi_nav
        catalog = get_catalog()
        rows = fetch_amfi_nav(catalog)

        if scheme_name:
            q = scheme_name.lower()
            rows = [r for r in rows if q in r.get("scheme_name", "").lower()]

        if not rows:
            return {
                "status": "no_results",
                "message": f"No scheme found matching '{scheme_name}'. Try a shorter keyword.",
                "tip": "Example: 'SBI Blue Chip' or 'HDFC Mid Cap'",
            }

        # Return top 20 matches (or all if < 20)
        sample = rows[:20]
        return {
            "source": "AMFI India — www.amfiindia.com",
            "note": "NAV data as of latest AMFI update. Past NAV is not indicative of future returns.",
            "total_matches": len(rows),
            "showing": len(sample),
            "nav_data": sample,
        }
    except Exception as e:
        return {"error": str(e)}
