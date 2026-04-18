"""BFSI Advisory Chatbot — FastAPI web backend.

Reuses all 24 tool functions from the MCP server directly.
Calls the Anthropic API with tool_use, streams the response via SSE.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── Make src/ importable when running from web/ or project root ──────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

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

load_dotenv()

# ── Anthropic client ──────────────────────────────────────────────────────────
_api_key = os.getenv("ANTHROPIC_API_KEY")
if not _api_key:
    raise RuntimeError(
        "ANTHROPIC_API_KEY not set. Copy .env.example to .env and add your key."
    )

client = anthropic.AsyncAnthropic(api_key=_api_key)
MODEL = "claude-sonnet-4-6"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a BFSI Advisory Assistant for an Indian bank. You help three audiences:

• Bank Customers — questions about mutual funds, NAV, insurance, IPOs, stocks, and tax
• Relationship Managers (RMs) — product knowledge and customer advisory support
• Compliance / IT Teams — RBI CSF, CERT-In, and PCI-DSS regulatory compliance

Guidelines:
- Always use the available tools to give accurate, up-to-date answers
- Use simple, clear language — assume customers may not have financial expertise
- For RMs and compliance teams, technical terminology is fine
- Always include appropriate disclaimers for financial advice
- All amounts are in Indian Rupees (₹); tax rules are for FY 2025-26
- Never recommend specific stocks, funds, or insurance products by name
- For compliance queries, cite the specific control or regulation ID
- Keep responses concise but complete; use bullet points for lists"""

# ── Tool definitions (Anthropic input_schema format) ─────────────────────────
TOOLS = [
    # RBI CSF
    {"name": "rbi_list_controls",
     "description": "List all RBI Cyber Security Framework (RBI CSF) control domains and controls.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "rbi_check_control",
     "description": "Get full details for a specific RBI CSF control by ID (e.g. 'RBI-CSF-2.1'). Returns requirements and evidence checklist.",
     "input_schema": {"type": "object", "properties": {"control_id": {"type": "string"}}, "required": ["control_id"]}},
    {"name": "rbi_assess_system",
     "description": "Assess a system description against RBI CSF controls using keyword matching.",
     "input_schema": {"type": "object", "properties": {"system_description": {"type": "string"}}, "required": ["system_description"]}},
    # CERT-In
    {"name": "certin_list_directives",
     "description": "List all CERT-In Directions (April 2022) applicable to organisations in India.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "certin_check_directive",
     "description": "Get full details of a CERT-In directive by ID (e.g. 'CERTIN-1' for 6-hour incident reporting).",
     "input_schema": {"type": "object", "properties": {"directive_id": {"type": "string"}}, "required": ["directive_id"]}},
    {"name": "certin_assess_incident_response",
     "description": "Assess an Incident Response plan against CERT-In mandates. Returns compliance score and gaps.",
     "input_schema": {"type": "object", "properties": {"ir_plan_description": {"type": "string"}}, "required": ["ir_plan_description"]}},
    # PCI-DSS
    {"name": "pcidss_list_requirements",
     "description": "List all 12 PCI-DSS v4.0 requirements with titles.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "pcidss_check_requirement",
     "description": "Get full details for a PCI-DSS v4.0 requirement by number (1–12).",
     "input_schema": {"type": "object", "properties": {"requirement_number": {"type": "string"}}, "required": ["requirement_number"]}},
    {"name": "pcidss_assess_control",
     "description": "Assess a control description against PCI-DSS v4.0. Flags deprecated protocols.",
     "input_schema": {"type": "object", "properties": {"control_description": {"type": "string"}}, "required": ["control_description"]}},
    # Mutual Funds
    {"name": "mf_explain_concept",
     "description": "Explain a Mutual Fund concept in simple language: NAV, SIP, ELSS, Expense Ratio, AUM, Exit Load, Riskometer, KYC, Direct vs Regular.",
     "input_schema": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}},
    {"name": "mf_list_categories",
     "description": "List all SEBI-defined Mutual Fund categories (equity, debt, hybrid, etc.) with plain-language descriptions.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "mf_tax_guide",
     "description": "Tax implications of Mutual Fund investments for FY 2025-26. fund_type: equity, debt, elss, or all.",
     "input_schema": {"type": "object", "properties": {"fund_type": {"type": "string", "default": "all"}}, "required": []}},
    # Insurance
    {"name": "insurance_list_types",
     "description": "List insurance types available in India with descriptions. category: life, health, general, or all.",
     "input_schema": {"type": "object", "properties": {"category": {"type": "string", "default": "all"}}, "required": []}},
    {"name": "insurance_explain_concept",
     "description": "Explain an insurance concept: Sum Assured, Premium, Claim Settlement Ratio, Free Look Period, Surrender Value, Rider, Nominee, Pre-existing Disease.",
     "input_schema": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}},
    {"name": "insurance_regulatory_info",
     "description": "IRDAI regulatory information. topic: kyc, claim, grievance, ombudsman, mis_selling, bima_sugam, or all.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "default": "all"}}, "required": []}},
    # IPO
    {"name": "ipo_explain_process",
     "description": "Complete IPO process step-by-step for a layman: ASBA, Demat, cut-off price, allotment, listing, SEBI protections.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "ipo_list_concepts",
     "description": "Explain IPO concepts: GMP, ASBA, Price Band, Lot Size, Cut-off Price, DRHP, OFS, Anchor Investor. Use 'all' for full glossary.",
     "input_schema": {"type": "object", "properties": {"concept": {"type": "string", "default": "all"}}, "required": []}},
    {"name": "ipo_eligibility_guide",
     "description": "IPO investor categories and eligibility. investor_type: retail (up to ₹2L), hni (above ₹2L), qib, employee, or all.",
     "input_schema": {"type": "object", "properties": {"investor_type": {"type": "string", "default": "all"}}, "required": []}},
    # Stocks
    {"name": "stock_explain_concept",
     "description": "Explain a stock market concept: Bull/Bear Market, Circuit Breaker, Dividend, P/E Ratio, Demat Account, Stop Loss, Intraday, F&O, Buyback.",
     "input_schema": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}},
    {"name": "stock_market_basics",
     "description": "Complete beginner's guide to Indian stock market: BSE, NSE, SENSEX, NIFTY, Demat account, T+1 settlement, order types, common mistakes.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "stock_regulatory_info",
     "description": "SEBI regulations and investor protections. topic: taxation (STCG/LTCG FY25-26), investor_protection, fundamental_analysis, or all.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string", "default": "all"}}, "required": []}},
    # India Tax
    {"name": "tax_compare_regimes",
     "description": "Compare Old vs New Income Tax regime for FY 2025-26. Calculates exact tax under both and recommends the better one.",
     "input_schema": {"type": "object", "properties": {
         "annual_income": {"type": "number", "description": "Gross annual income in ₹ e.g. 1500000 for ₹15 lakh"},
         "total_deductions": {"type": "number", "description": "Total deductions under old regime in ₹ (80C+80D+HRA etc.)", "default": 0}
     }, "required": ["annual_income"]}},
    {"name": "tax_explain_deduction",
     "description": "Explain an income tax deduction for FY 2025-26: 80C (₹1.5L), 80D (health insurance), HRA, LTA, 80CCD1B (NPS), 24b (home loan), 80E, 80G, 80TTA, 80TTB.",
     "input_schema": {"type": "object", "properties": {"section": {"type": "string"}}, "required": ["section"]}},
    {"name": "tax_capital_gains_guide",
     "description": "Capital gains tax rules for FY 2025-26 per Finance Act 2024. asset_type: equity, debt_mf, real_estate, gold, crypto, or all.",
     "input_schema": {"type": "object", "properties": {"asset_type": {"type": "string", "default": "all"}}, "required": []}},
]

# ── Human-readable names shown in the UI while a tool is running ──────────────
TOOL_DISPLAY = {
    "rbi_list_controls": "Checking RBI CSF controls…",
    "rbi_check_control": "Looking up RBI CSF control…",
    "rbi_assess_system": "Assessing system against RBI CSF…",
    "certin_list_directives": "Checking CERT-In directives…",
    "certin_check_directive": "Looking up CERT-In directive…",
    "certin_assess_incident_response": "Assessing IR plan against CERT-In…",
    "pcidss_list_requirements": "Checking PCI-DSS requirements…",
    "pcidss_check_requirement": "Looking up PCI-DSS requirement…",
    "pcidss_assess_control": "Assessing control against PCI-DSS…",
    "mf_explain_concept": "Looking up Mutual Fund concept…",
    "mf_list_categories": "Fetching MF categories…",
    "mf_tax_guide": "Checking MF tax rules…",
    "insurance_list_types": "Fetching insurance types…",
    "insurance_explain_concept": "Looking up insurance concept…",
    "insurance_regulatory_info": "Checking IRDAI regulations…",
    "ipo_explain_process": "Fetching IPO process guide…",
    "ipo_list_concepts": "Looking up IPO concept…",
    "ipo_eligibility_guide": "Checking IPO eligibility…",
    "stock_explain_concept": "Looking up stock market concept…",
    "stock_market_basics": "Fetching stock market basics…",
    "stock_regulatory_info": "Checking SEBI regulations…",
    "tax_compare_regimes": "Calculating tax comparison…",
    "tax_explain_deduction": "Looking up tax deduction…",
    "tax_capital_gains_guide": "Checking capital gains tax rules…",
}

# ── Tool dispatch ─────────────────────────────────────────────────────────────
TOOL_DISPATCH = {
    "rbi_list_controls":               lambda a: rbi_list_controls(),
    "rbi_check_control":               lambda a: rbi_check_control(a["control_id"]),
    "rbi_assess_system":               lambda a: rbi_assess_system(a["system_description"]),
    "certin_list_directives":          lambda a: certin_list_directives(),
    "certin_check_directive":          lambda a: certin_check_directive(a["directive_id"]),
    "certin_assess_incident_response": lambda a: certin_assess_incident_response(a["ir_plan_description"]),
    "pcidss_list_requirements":        lambda a: pcidss_list_requirements(),
    "pcidss_check_requirement":        lambda a: pcidss_check_requirement(a["requirement_number"]),
    "pcidss_assess_control":           lambda a: pcidss_assess_control(a["control_description"]),
    "mf_explain_concept":              lambda a: mf_explain_concept(a["concept"]),
    "mf_list_categories":              lambda a: mf_list_categories(),
    "mf_tax_guide":                    lambda a: mf_tax_guide(a.get("fund_type", "all")),
    "insurance_list_types":            lambda a: insurance_list_types(a.get("category", "all")),
    "insurance_explain_concept":       lambda a: insurance_explain_concept(a["concept"]),
    "insurance_regulatory_info":       lambda a: insurance_regulatory_info(a.get("topic", "all")),
    "ipo_explain_process":             lambda a: ipo_explain_process(),
    "ipo_list_concepts":               lambda a: ipo_list_concepts(a.get("concept", "all")),
    "ipo_eligibility_guide":           lambda a: ipo_eligibility_guide(a.get("investor_type", "all")),
    "stock_explain_concept":           lambda a: stock_explain_concept(a["concept"]),
    "stock_market_basics":             lambda a: stock_market_basics(),
    "stock_regulatory_info":           lambda a: stock_regulatory_info(a.get("topic", "all")),
    "tax_compare_regimes":             lambda a: tax_compare_regimes(float(a["annual_income"]), float(a.get("total_deductions", 0))),
    "tax_explain_deduction":           lambda a: tax_explain_deduction(a["section"]),
    "tax_capital_gains_guide":         lambda a: tax_capital_gains_guide(a.get("asset_type", "all")),
}


def _execute_tool(name: str, arguments: dict) -> dict:
    fn = TOOL_DISPATCH.get(name)
    if not fn:
        return {"error": f"Unknown tool: {name}"}
    try:
        return fn(arguments)
    except Exception as e:
        return {"error": str(e)}


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="BFSI Advisory Chatbot")

_STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


class ChatMessage(BaseModel):
    role: str
    content: str | list


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


@app.get("/")
async def root():
    return FileResponse(str(_STATIC / "index.html"))


@app.post("/chat")
async def chat(request: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    return StreamingResponse(
        _stream(messages),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream(messages: list) -> AsyncGenerator[str, None]:
    current = list(messages)

    try:
        while True:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=current,
            )

            if response.stop_reason == "tool_use":
                tool_blocks = [b for b in response.content if b.type == "tool_use"]

                # Tell the UI which tools are running
                for block in tool_blocks:
                    display = TOOL_DISPLAY.get(block.name, block.name)
                    yield f"data: {json.dumps({'type': 'tool_call', 'display': display})}\n\n"

                # Execute every tool
                tool_results = []
                for block in tool_blocks:
                    result = _execute_tool(block.name, dict(block.input))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                # Serialise assistant turn (needed for the API message list)
                assistant_content = []
                for block in response.content:
                    if block.type == "text":
                        assistant_content.append({"type": "text", "text": block.text})
                    elif block.type == "tool_use":
                        assistant_content.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": dict(block.input),
                        })

                current.append({"role": "assistant", "content": assistant_content})
                current.append({"role": "user", "content": tool_results})

            else:
                # Final text response — stream character chunks for a live feel
                text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                chunk_size = 4
                for i in range(0, len(text), chunk_size):
                    yield f"data: {json.dumps({'type': 'text', 'text': text[i:i + chunk_size]})}\n\n"
                    await asyncio.sleep(0.006)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
