"""
BFSI Compliance Checker — MCP Server entry point.

Exposes 9 compliance tools across RBI CSF, CERT-In, and PCI-DSS frameworks
over stdio transport (compatible with Claude Desktop and MCP Inspector).
"""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from bfsi_compliance.tools.rbi_csf import (
    rbi_list_controls,
    rbi_check_control,
    rbi_assess_system,
)
from bfsi_compliance.tools.cert_in import (
    certin_list_directives,
    certin_check_directive,
    certin_assess_incident_response,
)
from bfsi_compliance.tools.pci_dss import (
    pcidss_list_requirements,
    pcidss_check_requirement,
    pcidss_assess_control,
)

# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
app = Server("bfsi-compliance-checker")

# ---------------------------------------------------------------------------
# Tool registry: describes every tool to MCP clients
# The JSON Schema under "inputSchema" is what Claude uses to know what
# arguments to pass when calling a tool.
# ---------------------------------------------------------------------------
TOOLS: list[Tool] = [
    # ── RBI CSF ──────────────────────────────────────────────────────────────
    Tool(
        name="rbi_list_controls",
        description=(
            "List all RBI Cyber Security Framework (RBI CSF) control domains "
            "and their controls. Use this first to discover available control IDs."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="rbi_check_control",
        description=(
            "Get full details for a specific RBI CSF control or domain by ID. "
            "Example IDs: 'RBI-CSF-1', 'RBI-CSF-2.1', 'RBI-CSF-3.3'. "
            "Returns the requirement text, maturity levels, and evidence checklist."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "control_id": {
                    "type": "string",
                    "description": "RBI CSF control ID, e.g. 'RBI-CSF-2.1'",
                }
            },
            "required": ["control_id"],
        },
    ),
    Tool(
        name="rbi_assess_system",
        description=(
            "Assess a plain-text description of a system or architecture against "
            "RBI CSF controls. Performs keyword-based matching and returns "
            "applicable controls with their evidence requirements."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "system_description": {
                    "type": "string",
                    "description": (
                        "Plain-text description of the system, e.g. "
                        "'We have a firewall, SIEM, and an internet banking portal with MFA.'"
                    ),
                }
            },
            "required": ["system_description"],
        },
    ),
    # ── CERT-In ──────────────────────────────────────────────────────────────
    Tool(
        name="certin_list_directives",
        description=(
            "List all CERT-In Directions (April 2022) with a brief summary. "
            "Applicable to all organisations operating in India."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="certin_check_directive",
        description=(
            "Get full details of a specific CERT-In directive. "
            "Example IDs: 'CERTIN-1' (incident reporting), 'CERTIN-3' (log retention)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "directive_id": {
                    "type": "string",
                    "description": "CERT-In directive ID, e.g. 'CERTIN-1'",
                }
            },
            "required": ["directive_id"],
        },
    ),
    Tool(
        name="certin_assess_incident_response",
        description=(
            "Assess an Incident Response (IR) plan description against CERT-In "
            "mandates. Checks for 6-hour reporting window, NTP sync, 180-day log "
            "retention, and designated PoC requirements. Returns a compliance score "
            "and list of gaps."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "ir_plan_description": {
                    "type": "string",
                    "description": "Plain-text description or excerpt of the IR plan",
                }
            },
            "required": ["ir_plan_description"],
        },
    ),
    # ── PCI-DSS ──────────────────────────────────────────────────────────────
    Tool(
        name="pcidss_list_requirements",
        description=(
            "List all 12 PCI-DSS v4.0 requirements with titles and sub-requirement "
            "counts. Use this to discover which requirement numbers to query."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    Tool(
        name="pcidss_check_requirement",
        description=(
            "Get full details for a specific PCI-DSS v4.0 requirement by number (1–12). "
            "Returns all sub-requirements and the evidence checklist."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "requirement_number": {
                    "type": "string",
                    "description": "PCI-DSS requirement number as a string, e.g. '3' or '10'",
                }
            },
            "required": ["requirement_number"],
        },
    ),
    Tool(
        name="pcidss_assess_control",
        description=(
            "Assess a control or system description against PCI-DSS v4.0 requirements. "
            "Performs keyword matching and flags deprecated protocol usage (SSL/TLS 1.0/1.1). "
            "Returns matched requirements and warnings."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "control_description": {
                    "type": "string",
                    "description": (
                        "Plain-text description of a control or system, e.g. "
                        "'We use TLS 1.2, MFA, and store encrypted cardholder data in a segmented network.'"
                    ),
                }
            },
            "required": ["control_description"],
        },
    ),
]

# ---------------------------------------------------------------------------
# MCP handler: list_tools
# Called by the client to discover what this server can do.
# ---------------------------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


# ---------------------------------------------------------------------------
# MCP handler: call_tool
# Called by the client whenever Claude decides to invoke one of our tools.
# Each branch calls the relevant pure-Python function and serialises the
# result as JSON inside a TextContent block.
# ---------------------------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    dispatch = {
        "rbi_list_controls": lambda _: rbi_list_controls(),
        "rbi_check_control": lambda a: rbi_check_control(a["control_id"]),
        "rbi_assess_system": lambda a: rbi_assess_system(a["system_description"]),
        "certin_list_directives": lambda _: certin_list_directives(),
        "certin_check_directive": lambda a: certin_check_directive(a["directive_id"]),
        "certin_assess_incident_response": lambda a: certin_assess_incident_response(a["ir_plan_description"]),
        "pcidss_list_requirements": lambda _: pcidss_list_requirements(),
        "pcidss_check_requirement": lambda a: pcidss_check_requirement(a["requirement_number"]),
        "pcidss_assess_control": lambda a: pcidss_assess_control(a["control_description"]),
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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def _run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main():
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
