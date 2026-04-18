# BFSI Compliance & Financial Advisory — MCP Server
## Architecture Document

**Version:** 1.0  
**Date:** April 2025  
**Prepared for:** Internal Presentation  

---

## 1. Executive Summary

This project delivers a **Model Context Protocol (MCP) Server** that gives any AI assistant
(Claude Desktop, or any MCP-compatible client) real-time access to:

- **Regulatory compliance rules** — RBI CSF, CERT-In, PCI-DSS
- **Financial product knowledge** — Mutual Funds, Insurance, IPO, Stocks
- **India Income Tax guidance** — FY 2025-26, both regimes, capital gains

The target audience spans **bank customers**, **Relationship Managers (RMs)**,
and **compliance / audit teams** — all accessing the same server through
Claude Desktop's natural language interface.

---

## 2. What is MCP?

```
┌─────────────────────────────────────────────────────────────────┐
│                  Model Context Protocol (MCP)                   │
│                  ──────────────────────────                     │
│  An open protocol by Anthropic that lets AI models securely     │
│  call external tools and data sources — like an API, but for    │
│  AI assistants.                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Without MCP:**  Claude answers from training data alone (may be outdated)

**With MCP:**  Claude calls your server to get authoritative, up-to-date answers

---

## 3. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER LAYER                                    │
│                                                                      │
│   Bank Customer          Relationship Manager       Auditor / IT     │
│   "What is NAV?"         "Compare tax regimes       "Are we RBI      │
│   "How to apply          for ₹15L income"           CSF compliant?"  │
│    for an IPO?"                                                      │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  Natural Language
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     CLAUDE DESKTOP (MCP Client)                      │
│                                                                      │
│   • Receives user query in plain English                             │
│   • Decides which MCP tool(s) to call                                │
│   • Formats tool results into a human-friendly response              │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │  MCP Protocol (stdio / JSON-RPC)
                                 ▼
┌──────────────────────────────────────────────────────────────────────┐
│               BFSI MCP SERVER  (this project)                        │
│                                                                      │
│   server.py — registers 24 tools, routes calls, returns JSON        │
│                                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                 │
│  │  Compliance  │ │   Products   │ │     Tax      │                 │
│  │  ──────────  │ │  ──────────  │ │  ──────────  │                 │
│  │  rbi_csf.py  │ │  mutual_     │ │  india_      │                 │
│  │  cert_in.py  │ │  funds.py    │ │  tax.py      │                 │
│  │  pci_dss.py  │ │  insurance.  │ │              │                 │
│  │              │ │  py          │ │              │                 │
│  │              │ │  ipo.py      │ │              │                 │
│  │              │ │  stocks.py   │ │              │                 │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘                 │
│         │                │                │                          │
│         └────────────────┼────────────────┘                          │
│                          ▼                                           │
│              ┌───────────────────────┐                               │
│              │    Rule Catalogues    │                               │
│              │    (JSON files)       │                               │
│              │  ─────────────────    │                               │
│              │  rbi_rules.json       │                               │
│              │  cert_in_rules.json   │                               │
│              │  pci_dss_rules.json   │                               │
│              │  mutual_fund_rules    │                               │
│              │  insurance_rules      │                               │
│              │  ipo_rules.json       │                               │
│              │  stocks_rules.json    │                               │
│              │  india_tax_rules      │                               │
│              └───────────────────────┘                               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| AI Client | Claude Desktop | Natural language interface for end users |
| Protocol | MCP (Model Context Protocol) v1.0 | Communication between Claude and server |
| Transport | stdio (stdin/stdout) | Claude Desktop launches server as a subprocess |
| Server Runtime | Python 3.11+ | MCP server implementation |
| MCP Library | `mcp>=1.0.0` (Anthropic Python SDK) | Server framework, tool registration |
| Data Validation | `pydantic>=2.0.0` | Input validation (used by MCP SDK internally) |
| Rule Storage | JSON files | Human-readable, auditor-updatable rule catalogues |
| Testing | `pytest` + `pytest-asyncio` | Unit tests for all tool functions |
| Package Manager | `pip` + `pyproject.toml` (hatchling) | Dependency and package management |
| Version Control | Git + GitHub | Source code hosting |

---

## 5. Repository Structure

```
bfsi-compliance-checker/
│
├── src/bfsi_compliance/
│   │
│   ├── server.py                  ← MCP server: registers all 24 tools,
│   │                                routes calls, returns JSON responses
│   │
│   ├── tools/                     ← Pure Python business logic (no MCP dependency)
│   │   ├── rbi_csf.py             │
│   │   ├── cert_in.py             │  Each module has 3 functions:
│   │   ├── pci_dss.py             │  list_*  → discovery
│   │   ├── mutual_funds.py        │  check_* → specific lookup
│   │   ├── insurance.py           │  assess_*→ heuristic evaluation
│   │   ├── ipo.py                 │
│   │   ├── stocks.py              │
│   │   └── india_tax.py           │
│   │
│   └── rules/                     ← Compliance & knowledge catalogues
│       ├── rbi_rules.json         │
│       ├── cert_in_rules.json     │  Updated by compliance/product teams
│       ├── pci_dss_rules.json     │  without touching Python code
│       ├── mutual_fund_rules.json │
│       ├── insurance_rules.json   │
│       ├── ipo_rules.json         │
│       ├── stocks_rules.json      │
│       └── india_tax_rules.json   │
│
├── tests/                         ← 61 unit tests (pytest)
│   ├── test_rbi.py
│   ├── test_cert_in.py
│   ├── test_pci_dss.py
│   ├── test_mutual_funds.py
│   ├── test_insurance.py
│   ├── test_ipo.py
│   ├── test_stocks.py
│   └── test_india_tax.py
│
├── pyproject.toml                 ← Package definition + dependencies
├── CLAUDE.md                      ← Developer guide & Claude Code context
├── ARCHITECTURE.md                ← This document
└── .claude/settings.json          ← Claude Code permissions
```

---

## 6. Tool Inventory — All 24 Tools

### 6.1 Compliance Domain (9 tools) — For Auditors & IT Teams

| Tool | Input | Output |
|------|-------|--------|
| `rbi_list_controls` | — | 5 domains, 15 controls |
| `rbi_check_control` | control_id (e.g. RBI-CSF-2.1) | Requirements + evidence checklist |
| `rbi_assess_system` | System description (text) | Matching controls + gaps |
| `certin_list_directives` | — | 6 CERT-In directives |
| `certin_check_directive` | directive_id (e.g. CERTIN-3) | Full directive text |
| `certin_assess_incident_response` | IR plan text | Compliance score + gap list |
| `pcidss_list_requirements` | — | All 12 PCI-DSS requirements |
| `pcidss_check_requirement` | requirement number (1–12) | Sub-requirements + evidence |
| `pcidss_assess_control` | Control description (text) | Matched requirements + warnings |

### 6.2 Mutual Funds (3 tools) — For Customers & RMs

| Tool | Input | Output |
|------|-------|--------|
| `mf_explain_concept` | Concept (NAV, SIP, ELSS, AUM…) | Plain-language explanation + analogy |
| `mf_list_categories` | — | All SEBI MF categories with descriptions |
| `mf_tax_guide` | fund_type (equity/debt/elss/all) | Tax rates, holding periods, FY25-26 |

### 6.3 Insurance (3 tools) — For Customers & RMs

| Tool | Input | Output |
|------|-------|--------|
| `insurance_list_types` | category (life/health/general/all) | Types with features, tax benefits |
| `insurance_explain_concept` | Concept (Sum Assured, Rider…) | Plain-language explanation |
| `insurance_regulatory_info` | topic (claim/ombudsman/kyc…) | IRDAI rules & timelines |

### 6.4 IPO (3 tools) — For Customers & RMs

| Tool | Input | Output |
|------|-------|--------|
| `ipo_explain_process` | — | Step-by-step IPO guide, SEBI protections |
| `ipo_list_concepts` | concept (GMP/ASBA/all…) | IPO glossary explanations |
| `ipo_eligibility_guide` | investor_type (retail/hni/qib/all) | Limits, reservations, allotment method |

### 6.5 Stocks (3 tools) — For Customers & RMs

| Tool | Input | Output |
|------|-------|--------|
| `stock_explain_concept` | Concept (P/E, Bull Market, F&O…) | Plain-language explanation |
| `stock_market_basics` | — | Complete beginner's guide to Indian markets |
| `stock_regulatory_info` | topic (taxation/investor_protection/all) | SEBI rules, STCG/LTCG rates |

### 6.6 India Income Tax (3 tools) — For All Audiences

| Tool | Input | Output |
|------|-------|--------|
| `tax_compare_regimes` | annual_income + total_deductions | Side-by-side comparison + recommendation |
| `tax_explain_deduction` | section (80C/80D/HRA/LTA…) | Limit, eligible investments, examples |
| `tax_capital_gains_guide` | asset_type (equity/debt/gold/crypto/all) | Holding period + tax rate per Finance Act 2024 |

---

## 7. Data Flow — End-to-End Request Lifecycle

```
User types in Claude Desktop
         │
         ▼
Claude reads tool descriptions (list_tools response)
         │
         ▼
Claude selects the right tool and constructs arguments
  e.g. tool="tax_compare_regimes", args={annual_income: 1500000, total_deductions: 175000}
         │
         ▼  MCP call_tool request (JSON over stdio)
         │
         ▼
server.py dispatches to india_tax.tax_compare_regimes(1500000, 175000)
         │
         ▼
tax.py runs slab calculation, applies rebate 87A, adds 4% cess
         │
         ▼
Returns dict → server.py wraps in TextContent(type="text", text=json.dumps(...))
         │
         ▼  MCP response (JSON over stdio)
         │
         ▼
Claude reads the JSON, formats it into a natural language answer:
  "For ₹15 lakh income with ₹1.75 lakh deductions, the New Regime saves
   you ₹X in tax. Here's the breakdown: ..."
         │
         ▼
User sees a clear, friendly answer
```

---

## 8. Key Design Decisions

### 8.1 Rules as JSON, not code
Compliance rules and product knowledge live in `/rules/*.json` files, not Python.
This means a compliance officer or product manager can update rules without a
developer — just edit the JSON and restart the server.

### 8.2 Pure Python tool functions
Each tool function (e.g. `rbi_check_control`, `mf_explain_concept`) has zero
dependency on MCP. They take plain inputs, return plain dicts.
This makes them independently testable and reusable.

### 8.3 stdio transport
Claude Desktop launches the MCP server as a child process and communicates
over stdin/stdout. No HTTP server, no ports, no firewall rules needed.
The server lives and dies with the Claude Desktop session.

### 8.4 src/ layout
Package code lives under `src/bfsi_compliance/` (not at root).
This prevents accidentally importing an uninstalled version during tests
and is the modern Python packaging best practice.

### 8.5 Disclaimer on every financial response
Every tool that returns financial or tax information includes a `disclaimer`
field reminding users this is educational content, not personalised advice.
This is important for RBI/SEBI regulatory compliance around investment advice.

---

## 9. Security & Compliance Considerations

| Concern | How it's handled |
|---------|-----------------|
| No live data | Server reads only from local JSON files — no external API calls, no internet dependency |
| No PII stored | Server does not log user queries or store any personal data |
| Read-only | All tools are read-only; no writes to any system |
| Advice disclaimer | Every financial tool response includes a regulatory disclaimer |
| Local execution | Server runs on the user's own machine — data never leaves the device |
| SEBI/IRDAI alignment | Product knowledge reflects current regulations; rules can be updated in JSON |

---

## 10. Deployment

### Current: Claude Desktop (Local)
```
Machine: User's MacBook / Windows PC
Server:  /bfsi-compliance-checker/.venv/bin/python -m bfsi_compliance.server
Config:  ~/Library/Application Support/Claude/claude_desktop_config.json
```

### Future Options

| Option | Use Case |
|--------|----------|
| **Docker container** | Deploy to a shared server so multiple users share one instance |
| **HTTP/SSE transport** | Replace stdio with HTTP for web-based MCP clients |
| **Database backend** | Replace JSON files with a database for live rule updates |
| **Auth layer** | Add role-based access (customers see product tools; auditors see compliance tools) |
| **RAG / Vector search** | Semantic search over rules instead of keyword matching |
| **Live data feeds** | Connect to NSE/BSE APIs for real-time NAV, stock prices |

---

## 11. Test Coverage

```
Total tests:   61
Pass rate:     100% (61/61)
Test runtime:  ~0.03 seconds

Coverage by module:
  test_rbi.py          6 tests   — list, check, assess
  test_cert_in.py      6 tests   — list, check, assess IR plan
  test_pci_dss.py      6 tests   — list, check, assess control
  test_mutual_funds.py 8 tests   — concepts, categories, tax guide
  test_insurance.py    8 tests   — types, concepts, IRDAI info
  test_ipo.py          8 tests   — process, concepts, eligibility
  test_stocks.py       8 tests   — concepts, basics, regulatory info
  test_india_tax.py   11 tests   — regime comparison, deductions, capital gains
```

---

## 12. GitHub Repository

**URL:** https://github.com/rajeshkhandve2025/bfsi-compliance-checker

```
main branch
├── Initial commit  — 9 compliance tools (RBI CSF, CERT-In, PCI-DSS)
└── Latest commit   — +15 tools: MF, Insurance, IPO, Stocks, India Tax FY25-26
```

---

*Document prepared using Claude Code + Claude Desktop MCP integration.*  
*All financial and regulatory content is for educational purposes only.*  
*Consult qualified professionals for specific advice.*
