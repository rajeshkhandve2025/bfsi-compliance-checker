"""
BFSI Compliance Checker — MCP Server entry point.

Exposes 24 tools across 7 domains:
  - Compliance: RBI CSF, CERT-In, PCI-DSS
  - Financial Products: Mutual Funds, Insurance, IPO, Stocks, India Tax
over stdio transport (compatible with Claude Desktop and MCP Inspector).
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from bfsi_compliance.tools.rbi_csf import (
    rbi_list_controls, rbi_check_control, rbi_assess_system,
)
from bfsi_compliance.tools.cert_in import (
    certin_list_directives, certin_check_directive, certin_assess_incident_response,
)
from bfsi_compliance.tools.pci_dss import (
    pcidss_list_requirements, pcidss_check_requirement, pcidss_assess_control,
)
from bfsi_compliance.tools.mutual_funds import (
    mf_explain_concept, mf_list_categories, mf_tax_guide,
)
from bfsi_compliance.tools.insurance import (
    insurance_list_types, insurance_explain_concept, insurance_regulatory_info,
)
from bfsi_compliance.tools.ipo import (
    ipo_explain_process, ipo_list_concepts, ipo_eligibility_guide,
)
from bfsi_compliance.tools.stocks import (
    stock_explain_concept, stock_market_basics, stock_regulatory_info,
)
from bfsi_compliance.tools.india_tax import (
    tax_compare_regimes, tax_explain_deduction, tax_capital_gains_guide,
)

app = Server("bfsi-compliance-checker")

TOOLS: list[Tool] = [
    # ── RBI CSF ──────────────────────────────────────────────────────────────
    Tool(
        name="rbi_list_controls",
        description="List all RBI Cyber Security Framework (RBI CSF) control domains and their controls.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="rbi_check_control",
        description=(
            "Get full details for a specific RBI CSF control by ID (e.g. 'RBI-CSF-2.1'). "
            "Returns requirement text, maturity levels, and evidence checklist."
        ),
        inputSchema={
            "type": "object",
            "properties": {"control_id": {"type": "string", "description": "RBI CSF control ID e.g. 'RBI-CSF-2.1'"}},
            "required": ["control_id"],
        },
    ),
    Tool(
        name="rbi_assess_system",
        description="Assess a system description against RBI CSF controls using keyword matching.",
        inputSchema={
            "type": "object",
            "properties": {"system_description": {"type": "string", "description": "Plain-text description of the system"}},
            "required": ["system_description"],
        },
    ),
    # ── CERT-In ──────────────────────────────────────────────────────────────
    Tool(
        name="certin_list_directives",
        description="List all CERT-In Directions (April 2022) applicable to organisations in India.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="certin_check_directive",
        description="Get full details of a CERT-In directive by ID (e.g. 'CERTIN-1' for incident reporting).",
        inputSchema={
            "type": "object",
            "properties": {"directive_id": {"type": "string", "description": "CERT-In directive ID e.g. 'CERTIN-3'"}},
            "required": ["directive_id"],
        },
    ),
    Tool(
        name="certin_assess_incident_response",
        description="Assess an Incident Response plan against CERT-In mandates. Returns compliance score and gaps.",
        inputSchema={
            "type": "object",
            "properties": {"ir_plan_description": {"type": "string", "description": "IR plan text or excerpt"}},
            "required": ["ir_plan_description"],
        },
    ),
    # ── PCI-DSS ──────────────────────────────────────────────────────────────
    Tool(
        name="pcidss_list_requirements",
        description="List all 12 PCI-DSS v4.0 requirements with titles.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="pcidss_check_requirement",
        description="Get full details for a PCI-DSS v4.0 requirement by number (1–12).",
        inputSchema={
            "type": "object",
            "properties": {"requirement_number": {"type": "string", "description": "Requirement number e.g. '3'"}},
            "required": ["requirement_number"],
        },
    ),
    Tool(
        name="pcidss_assess_control",
        description="Assess a control description against PCI-DSS v4.0. Flags deprecated protocols (SSL/TLS 1.0/1.1).",
        inputSchema={
            "type": "object",
            "properties": {"control_description": {"type": "string", "description": "Control or system description"}},
            "required": ["control_description"],
        },
    ),
    # ── Mutual Funds ─────────────────────────────────────────────────────────
    Tool(
        name="mf_explain_concept",
        description=(
            "Explain a Mutual Fund concept in simple language for customers and laymen. "
            "Supports: NAV, SIP, Expense Ratio, AUM, Exit Load, ELSS, Riskometer, "
            "Direct vs Regular Plan, KYC."
        ),
        inputSchema={
            "type": "object",
            "properties": {"concept": {"type": "string", "description": "Concept to explain e.g. 'NAV', 'SIP', 'ELSS'"}},
            "required": ["concept"],
        },
    ),
    Tool(
        name="mf_list_categories",
        description=(
            "List all SEBI-defined Mutual Fund categories (equity, debt, hybrid, etc.) "
            "with plain-language descriptions. Useful for RM and customers choosing funds."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="mf_tax_guide",
        description=(
            "Explain tax implications of Mutual Fund investments for FY 2025-26. "
            "fund_type: 'equity', 'debt', 'elss', or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "fund_type": {
                    "type": "string",
                    "description": "Fund type: 'equity', 'debt', 'elss', or 'all' (default: all)",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    # ── Insurance ────────────────────────────────────────────────────────────
    Tool(
        name="insurance_list_types",
        description=(
            "List all insurance types available in India with plain-language descriptions. "
            "Covers Term, Endowment, ULIP, Health, Motor, Home, Travel insurance. "
            "category: 'life', 'health', 'general', or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Insurance category: 'life', 'health', 'general', or 'all'",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="insurance_explain_concept",
        description=(
            "Explain an insurance concept in simple language. "
            "Examples: Sum Assured, Premium, Claim Settlement Ratio, Free Look Period, "
            "Surrender Value, Grace Period, Rider, Nominee, Pre-existing Disease."
        ),
        inputSchema={
            "type": "object",
            "properties": {"concept": {"type": "string", "description": "Insurance concept to explain"}},
            "required": ["concept"],
        },
    ),
    Tool(
        name="insurance_regulatory_info",
        description=(
            "Get IRDAI regulatory information for insurance in India. "
            "Topics: 'kyc', 'claim', 'grievance', 'ombudsman', 'mis_selling', 'bima_sugam', or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic: kyc, claim, grievance, ombudsman, mis_selling, bima_sugam, or all",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    # ── IPO ──────────────────────────────────────────────────────────────────
    Tool(
        name="ipo_explain_process",
        description=(
            "Explain the complete IPO process step-by-step for a layman. "
            "Covers what an IPO is, ASBA, Demat account, cut-off price, allotment, and listing. "
            "Also covers SEBI investor protections and risks."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="ipo_list_concepts",
        description=(
            "Explain IPO concepts in plain language. "
            "Examples: GMP, ASBA, Price Band, Lot Size, Cut-off Price, Oversubscription, "
            "DRHP, OFS, Fresh Issue, Listing Gains, Anchor Investor. "
            "Use 'all' for the complete glossary."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "concept": {
                    "type": "string",
                    "description": "Concept name e.g. 'GMP', 'ASBA', or 'all' for full glossary",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="ipo_eligibility_guide",
        description=(
            "Explain IPO investor categories and eligibility. "
            "investor_type: 'retail' (up to ₹2 lakh), 'hni' (above ₹2 lakh), "
            "'qib' (institutions), 'employee', or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "investor_type": {
                    "type": "string",
                    "description": "Investor type: retail, hni, qib, employee, or all",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    # ── Stocks ───────────────────────────────────────────────────────────────
    Tool(
        name="stock_explain_concept",
        description=(
            "Explain a stock market concept in simple language. "
            "Examples: Bull Market, Bear Market, Circuit Breaker, Dividend, P/E Ratio, "
            "Demat Account, Stop Loss, Intraday, F&O, Buyback, Bonus Shares, Market Order."
        ),
        inputSchema={
            "type": "object",
            "properties": {"concept": {"type": "string", "description": "Stock market concept to explain"}},
            "required": ["concept"],
        },
    ),
    Tool(
        name="stock_market_basics",
        description=(
            "Complete beginner's guide to the Indian stock market. "
            "Covers BSE, NSE, SENSEX, NIFTY, Demat account, T+1 settlement, "
            "types of trading, order types, and common mistakes to avoid."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="stock_regulatory_info",
        description=(
            "SEBI regulations and investor protections for stock market investors. "
            "topic: 'taxation' (STCG/LTCG for FY 2025-26), "
            "'investor_protection' (SEBI rules, SCORES), "
            "'fundamental_analysis' (P/E, ROE, EPS), or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic: taxation, investor_protection, fundamental_analysis, or all",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
    # ── India Tax ────────────────────────────────────────────────────────────
    Tool(
        name="tax_compare_regimes",
        description=(
            "Compare Old vs New Income Tax regime for FY 2025-26. "
            "Calculates tax under both regimes and recommends the better one. "
            "annual_income in ₹ (e.g. 1200000 for ₹12 lakh). "
            "total_deductions: total deductions under old regime (80C + 80D + HRA etc.)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "annual_income": {"type": "number", "description": "Gross annual income in ₹ e.g. 1200000"},
                "total_deductions": {
                    "type": "number",
                    "description": "Total deductions under old regime in ₹ (default 0)",
                    "default": 0,
                },
            },
            "required": ["annual_income"],
        },
    ),
    Tool(
        name="tax_explain_deduction",
        description=(
            "Explain a specific income tax deduction section for FY 2025-26. "
            "Examples: '80C' (₹1.5 lakh — PPF/ELSS/LIC), '80D' (health insurance), "
            "'80CCD1B' (NPS extra ₹50k), 'HRA', 'LTA', '24b' (home loan interest), "
            "'80E' (education loan), '80G' (donations), '80TTA', '80TTB'."
        ),
        inputSchema={
            "type": "object",
            "properties": {"section": {"type": "string", "description": "Tax section e.g. '80C', '80D', 'HRA'"}},
            "required": ["section"],
        },
    ),
    Tool(
        name="tax_capital_gains_guide",
        description=(
            "Explain capital gains tax rules for FY 2025-26 as per Finance Act 2024. "
            "asset_type: 'equity' (stocks/equity MF), 'debt_mf', 'real_estate', "
            "'gold', 'crypto', or 'all'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "Asset type: equity, debt_mf, real_estate, gold, crypto, or all",
                    "default": "all",
                }
            },
            "required": [],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    dispatch = {
        # Compliance
        "rbi_list_controls": lambda _: rbi_list_controls(),
        "rbi_check_control": lambda a: rbi_check_control(a["control_id"]),
        "rbi_assess_system": lambda a: rbi_assess_system(a["system_description"]),
        "certin_list_directives": lambda _: certin_list_directives(),
        "certin_check_directive": lambda a: certin_check_directive(a["directive_id"]),
        "certin_assess_incident_response": lambda a: certin_assess_incident_response(a["ir_plan_description"]),
        "pcidss_list_requirements": lambda _: pcidss_list_requirements(),
        "pcidss_check_requirement": lambda a: pcidss_check_requirement(a["requirement_number"]),
        "pcidss_assess_control": lambda a: pcidss_assess_control(a["control_description"]),
        # Mutual Funds
        "mf_explain_concept": lambda a: mf_explain_concept(a["concept"]),
        "mf_list_categories": lambda _: mf_list_categories(),
        "mf_tax_guide": lambda a: mf_tax_guide(a.get("fund_type", "all")),
        # Insurance
        "insurance_list_types": lambda a: insurance_list_types(a.get("category", "all")),
        "insurance_explain_concept": lambda a: insurance_explain_concept(a["concept"]),
        "insurance_regulatory_info": lambda a: insurance_regulatory_info(a.get("topic", "all")),
        # IPO
        "ipo_explain_process": lambda _: ipo_explain_process(),
        "ipo_list_concepts": lambda a: ipo_list_concepts(a.get("concept", "all")),
        "ipo_eligibility_guide": lambda a: ipo_eligibility_guide(a.get("investor_type", "all")),
        # Stocks
        "stock_explain_concept": lambda a: stock_explain_concept(a["concept"]),
        "stock_market_basics": lambda _: stock_market_basics(),
        "stock_regulatory_info": lambda a: stock_regulatory_info(a.get("topic", "all")),
        # Tax
        "tax_compare_regimes": lambda a: tax_compare_regimes(
            float(a["annual_income"]), float(a.get("total_deductions", 0))
        ),
        "tax_explain_deduction": lambda a: tax_explain_deduction(a["section"]),
        "tax_capital_gains_guide": lambda a: tax_capital_gains_guide(a.get("asset_type", "all")),
    }

    if name not in dispatch:
        result = {"error": f"Unknown tool: '{name}'"}
    else:
        try:
            result = dispatch[name](arguments)
        except KeyError as e:
            result = {"error": f"Missing required argument: {e}"}
        except Exception as e:
            result = {"error": f"Tool execution failed: {e}"}

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
