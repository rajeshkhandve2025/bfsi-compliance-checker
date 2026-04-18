"""BFSI Advisory Chatbot — FastAPI backend using Groq (free tier).

Uses Groq's free API (llama-3.3-70b-versatile) with tool calling.
Get a free key at https://console.groq.com — no credit card required.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from groq import AsyncGroq
from pydantic import BaseModel

# ── Make src/ importable ──────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

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
from bfsi_compliance.tools.live_nav import mf_live_nav
from bfsi_compliance.grounding import get_catalog, AnswerValidator

# ── Grounding layer ───────────────────────────────────────────────────────────
try:
    _catalog = get_catalog()
    _validator = AnswerValidator(_catalog)
    _GROUNDING_OK = True
except Exception as _grounding_err:
    _GROUNDING_OK = False
    print(f"[warn] grounding layer unavailable: {_grounding_err}")

# Topic detection: map tool name prefix → catalog topic_id
_TOOL_TOPIC: dict[str, str] = {
    "rbi_": "compliance", "certin_": "compliance", "pcidss_": "compliance",
    "mf_": "mutual_funds",
    "insurance_": "insurance",
    "ipo_": "ipo",
    "stock_": "stocks",
    "tax_": "income_tax",
}

# Red-flag phrases that must trigger a refusal before streaming
_RED_FLAGS: list[str] = []
if _GROUNDING_OK:
    _RED_FLAGS = _catalog.policy.get("red_flags", [])


def _detect_topic(tool_names_used: list[str]) -> str | None:
    for tool in tool_names_used:
        for prefix, topic in _TOOL_TOPIC.items():
            if tool.startswith(prefix):
                return topic
    return None


def _check_red_flags(text: str) -> str | None:
    """Return the first matched red-flag phrase, or None if clean."""
    lowered = text.lower()
    for phrase in _RED_FLAGS:
        if phrase.lower() in lowered:
            return phrase
    return None


load_dotenv(Path(__file__).parent.parent / ".env")

# ── Groq client ───────────────────────────────────────────────────────────────
_api_key = os.getenv("GROQ_API_KEY")
if not _api_key:
    raise RuntimeError(
        "GROQ_API_KEY not set.\n"
        "Get a free key at https://console.groq.com (no credit card needed).\n"
        "Then add it to your .env file."
    )

client = AsyncGroq(api_key=_api_key)
MODEL = "llama-3.3-70b-versatile"

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a BFSI Advisory Assistant for an Indian bank. You help three audiences:

• Bank Customers — questions about mutual funds, NAV, insurance, IPOs, stocks, and tax
• Relationship Managers (RMs) — product knowledge and customer advisory support
• Compliance / IT Teams — RBI CSF, CERT-In, and PCI-DSS regulatory compliance

Guidelines:
- Always use the available tools to give accurate, up-to-date answers
- Use simple, clear language — assume customers may not have financial expertise
- For RMs and compliance teams, technical terminology is fine
- All amounts are in Indian Rupees (₹); tax rules are for FY 2025-26
- Never recommend specific stocks, funds, or insurance products by name
- For compliance queries, cite the specific control or regulation ID
- Keep responses concise but complete; use bullet points for lists

Citation & Grounding Rules (MANDATORY):
- For Mutual Funds: cite SEBI (sebi.gov.in) or AMFI (amfiindia.com) as the authoritative source
- For Insurance: cite IRDAI (irdai.gov.in) or policyholder.gov.in
- For IPO / Stocks: cite SEBI (sebi.gov.in)
- For Tax: cite Income Tax India (incometax.gov.in) or CBDT circulars
- For Compliance (RBI/CERT-In/PCI-DSS): cite the specific regulation ID and issuing body
- End every financial answer with a one-line disclaimer such as:
  "This is educational information only — consult a SEBI-registered advisor before investing."

Strict Prohibitions:
- NEVER say "you should buy", "which fund is best for me", "which policy should I take"
- NEVER promise "guaranteed returns" or "risk-free" investments
- NEVER predict stock movements ("will this stock go up")
- Refuse these requests politely and redirect to educational content"""

# ── Tool definitions (OpenAI/Groq function-calling format) ───────────────────
TOOLS = [
    # RBI CSF
    {"type": "function", "function": {"name": "rbi_list_controls",
     "description": "List all RBI Cyber Security Framework (RBI CSF) control domains and controls.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "rbi_check_control",
     "description": "Get full details for a specific RBI CSF control by ID (e.g. 'RBI-CSF-2.1'). Returns requirements and evidence checklist.",
     "parameters": {"type": "object", "properties": {"control_id": {"type": "string", "description": "e.g. RBI-CSF-2.1"}}, "required": ["control_id"]}}},
    {"type": "function", "function": {"name": "rbi_assess_system",
     "description": "Assess a system description against RBI CSF controls.",
     "parameters": {"type": "object", "properties": {"system_description": {"type": "string"}}, "required": ["system_description"]}}},
    # CERT-In
    {"type": "function", "function": {"name": "certin_list_directives",
     "description": "List all CERT-In Directions (April 2022) applicable to organisations in India.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "certin_check_directive",
     "description": "Get full details of a CERT-In directive by ID (e.g. 'CERTIN-1' for 6-hour incident reporting).",
     "parameters": {"type": "object", "properties": {"directive_id": {"type": "string"}}, "required": ["directive_id"]}}},
    {"type": "function", "function": {"name": "certin_assess_incident_response",
     "description": "Assess an Incident Response plan against CERT-In mandates. Returns compliance score and gaps.",
     "parameters": {"type": "object", "properties": {"ir_plan_description": {"type": "string"}}, "required": ["ir_plan_description"]}}},
    # PCI-DSS
    {"type": "function", "function": {"name": "pcidss_list_requirements",
     "description": "List all 12 PCI-DSS v4.0 requirements.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "pcidss_check_requirement",
     "description": "Get full details for a PCI-DSS v4.0 requirement by number (1–12).",
     "parameters": {"type": "object", "properties": {"requirement_number": {"type": "string"}}, "required": ["requirement_number"]}}},
    {"type": "function", "function": {"name": "pcidss_assess_control",
     "description": "Assess a control description against PCI-DSS v4.0. Flags deprecated protocols (SSL/TLS 1.0/1.1).",
     "parameters": {"type": "object", "properties": {"control_description": {"type": "string"}}, "required": ["control_description"]}}},
    # Mutual Funds
    {"type": "function", "function": {"name": "mf_explain_concept",
     "description": "Explain a Mutual Fund concept in simple language: NAV, SIP, ELSS, Expense Ratio, AUM, Exit Load, Riskometer, KYC, Direct vs Regular Plan.",
     "parameters": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}}},
    {"type": "function", "function": {"name": "mf_list_categories",
     "description": "List all SEBI-defined Mutual Fund categories (equity, debt, hybrid, etc.) with plain-language descriptions.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "mf_tax_guide",
     "description": "Tax implications of MF investments for FY 2025-26. fund_type: equity, debt, elss, or all.",
     "parameters": {"type": "object", "properties": {"fund_type": {"type": "string", "enum": ["equity", "debt", "elss", "all"]}}, "required": []}}},
    # Insurance
    {"type": "function", "function": {"name": "insurance_list_types",
     "description": "List insurance types available in India. category: life, health, general, or all.",
     "parameters": {"type": "object", "properties": {"category": {"type": "string", "enum": ["life", "health", "general", "all"]}}, "required": []}}},
    {"type": "function", "function": {"name": "insurance_explain_concept",
     "description": "Explain an insurance concept: Sum Assured, Premium, Claim Settlement Ratio, Free Look Period, Surrender Value, Rider, Nominee, Pre-existing Disease.",
     "parameters": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}}},
    {"type": "function", "function": {"name": "insurance_regulatory_info",
     "description": "IRDAI regulatory information. topic: kyc, claim, grievance, ombudsman, mis_selling, bima_sugam, or all.",
     "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": []}}},
    # IPO
    {"type": "function", "function": {"name": "ipo_explain_process",
     "description": "Complete IPO application process step-by-step: ASBA, Demat, cut-off price, allotment, listing, SEBI protections.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "ipo_list_concepts",
     "description": "Explain IPO concepts: GMP, ASBA, Price Band, Lot Size, Cut-off Price, DRHP, OFS, Anchor Investor. Use 'all' for full glossary.",
     "parameters": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "ipo_eligibility_guide",
     "description": "IPO investor categories and eligibility. investor_type: retail (up to ₹2L), hni (above ₹2L), qib, employee, or all.",
     "parameters": {"type": "object", "properties": {"investor_type": {"type": "string", "enum": ["retail", "hni", "qib", "employee", "all"]}}, "required": []}}},
    # Stocks
    {"type": "function", "function": {"name": "stock_explain_concept",
     "description": "Explain a stock market concept: Bull/Bear Market, Circuit Breaker, Dividend, P/E Ratio, Demat Account, Stop Loss, Intraday, F&O, Buyback.",
     "parameters": {"type": "object", "properties": {"concept": {"type": "string"}}, "required": ["concept"]}}},
    {"type": "function", "function": {"name": "stock_market_basics",
     "description": "Complete beginner's guide to Indian stock market: BSE, NSE, SENSEX, NIFTY, Demat, T+1 settlement, order types, common mistakes.",
     "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "stock_regulatory_info",
     "description": "SEBI regulations and investor protections. topic: taxation (STCG/LTCG FY25-26), investor_protection, fundamental_analysis, or all.",
     "parameters": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": []}}},
    # India Tax
    {"type": "function", "function": {"name": "tax_compare_regimes",
     "description": "Compare Old vs New Income Tax regime for FY 2025-26. Calculates exact tax under both and recommends the better one.",
     "parameters": {"type": "object", "properties": {
         "annual_income": {"type": "number", "description": "Gross annual income in ₹ e.g. 1500000 for ₹15 lakh"},
         "total_deductions": {"type": "number", "description": "Total deductions under old regime in ₹ (80C+80D+HRA etc.), default 0"}
     }, "required": ["annual_income"]}}},
    {"type": "function", "function": {"name": "tax_explain_deduction",
     "description": "Explain an income tax deduction for FY 2025-26: 80C, 80D, HRA, LTA, 80CCD1B, 24b, 80E, 80G, 80TTA, 80TTB.",
     "parameters": {"type": "object", "properties": {"section": {"type": "string", "description": "e.g. 80C, 80D, HRA"}}, "required": ["section"]}}},
    {"type": "function", "function": {"name": "tax_capital_gains_guide",
     "description": "Capital gains tax for FY 2025-26 per Finance Act 2024. asset_type: equity, debt_mf, real_estate, gold, crypto, or all.",
     "parameters": {"type": "object", "properties": {"asset_type": {"type": "string"}}, "required": []}}},
    # Live NAV
    {"type": "function", "function": {"name": "mf_live_nav",
     "description": "Fetch real-time Mutual Fund NAV from AMFI India's public feed. Optionally filter by scheme name keyword (e.g. 'SBI Blue Chip', 'HDFC Mid Cap'). Returns current NAV, scheme type, and date.",
     "parameters": {"type": "object", "properties": {
         "scheme_name": {"type": "string", "description": "Partial scheme name to filter, e.g. 'SBI Blue Chip'. Leave empty to sample latest NAVs."}
     }, "required": []}}},
]

# ── Human-readable names shown while a tool runs ──────────────────────────────
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
    "mf_live_nav": "Fetching live NAV from AMFI India…",
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
    "mf_live_nav":                     lambda a: mf_live_nav(a.get("scheme_name", "")),
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
    # Groq uses the system message inside the messages list
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)
    tools_used: list[str] = []

    try:
        _retried = False
        while True:
            try:
                response = await client.chat.completions.create(
                    model=MODEL,
                    messages=full_messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    max_tokens=4096,
                )
            except Exception as groq_err:
                # Groq occasionally generates malformed tool calls; retry without tools
                if not _retried and "tool_use_failed" in str(groq_err):
                    _retried = True
                    response = await client.chat.completions.create(
                        model=MODEL,
                        messages=full_messages,
                        max_tokens=4096,
                    )
                else:
                    raise

            msg = response.choices[0].message

            if msg.tool_calls:
                # Notify UI which tools are running
                for tc in msg.tool_calls:
                    tools_used.append(tc.function.name)
                    display = TOOL_DISPLAY.get(tc.function.name, tc.function.name)
                    yield f"data: {json.dumps({'type': 'tool_call', 'display': display})}\n\n"

                # Execute every tool call
                tool_results = []
                for tc in msg.tool_calls:
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        args = {}
                    result = _execute_tool(tc.function.name, args)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

                # Add assistant turn + tool results to conversation
                full_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })
                full_messages.extend(tool_results)

            else:
                text = msg.content or ""

                # ── Red-flag gate ─────────────────────────────────────────────
                matched = _check_red_flags(text)
                if matched:
                    refusal = (
                        "I'm not able to provide personalised investment recommendations. "
                        "As an educational assistant, I can explain concepts, products, and regulations — "
                        "but specific advice like selecting funds, policies, or predicting returns must come from a "
                        "**SEBI-registered Investment Adviser** or **IRDAI-licensed insurance advisor**.\n\n"
                        "Would you like me to explain a concept or regulatory rule instead?"
                    )
                    text = refusal

                # ── Disclaimer injection ──────────────────────────────────────
                if _GROUNDING_OK and tools_used:
                    topic = _detect_topic(tools_used)
                    if topic:
                        disclaimer = _catalog.disclaimer_for(topic)
                        if disclaimer and disclaimer.lower() not in text.lower():
                            text += f"\n\n---\n*{disclaimer}*"

                # ── Stream text in small chunks ───────────────────────────────
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
