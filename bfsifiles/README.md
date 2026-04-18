# BFSI Public Advisor — Source Grounding Schema

A retrieval-layer grounding schema for a public BFSI chatbot advisor in India.
Every answer the bot produces **must** cite at least one authoritative government /
regulator source listed here, carry the correct disclaimer, and pass red-flag checks
before being returned to the user.

## Why this exists

Public financial advisors in India sit close to SEBI's Investment Adviser Regulations
(2013) and IRDAI intermediary rules. Keeping the bot squarely in **educational**
territory — not personalised advice — requires three hard constraints on every
response:

1. It must be grounded in a primary source (SEBI, RBI, IRDAI, Income Tax Dept, etc.)
2. It must carry a domain-appropriate disclaimer
3. It must refuse questions that drift into personalised advice ("should I buy X?")

This repo enforces all three as code, not as prompt instructions.

## Files

```
bfsi_advisor_schema/
├── bfsi_sources.yaml     # The authoritative catalog: sources + topics + policy
├── bfsi_schema.json      # JSON Schema — validates the YAML structure
├── bfsi_advisor.py       # Python loader, citation builder, policy validator
├── example_usage.py      # End-to-end demo of retrieval + enforcement
├── requirements.txt
└── README.md
```

## Install

```bash
pip install -r requirements.txt
python3 bfsi_advisor.py          # Validates schema, prints load summary
python3 example_usage.py         # Runs the demo
```

Validation output you should see:

```
[ok] loaded 29 sources, 6 topics
     schema v1.0.0  jurisdiction=IN  fy=FY 2025-26
```

## Schema anatomy

The YAML has three top-level blocks:

### `sources` — authoritative catalog

Every source has a `trust_level`:

| Level       | Meaning                                     | Example                |
|-------------|---------------------------------------------|------------------------|
| `primary`   | Government regulator, statute, recognised SRO | SEBI, RBI, IRDAI, AMFI |
| `secondary` | Industry body, exchange data, service portal | NSE, MF Central, DSCI  |
| `reference` | Educational material                        | NISM, NCFE             |

Each source declares: `authority_type`, `parent_regulator`, `base_url`, `domains`,
`citation_templates` (formal / inline / chatbot / footnote), and optional
`data_endpoints` for live feeds like AMFI's daily NAV.

### `topics` — taxonomy

Six top-level topics map to authoritative sources:

- 📈 `mutual_funds`   → primary: SEBI, AMFI
- 🛡️ `insurance`      → primary: IRDAI, Bima Bharosa, CIO
- 📋 `ipo`            → primary: SEBI
- 📊 `stocks`         → primary: SEBI
- 💰 `income_tax`     → primary: Income Tax Dept, CBDT, MoF, India Code
- 🔒 `compliance`     → primary: RBI, CERT-In, MeitY, PCI SSC

Each topic has subtopics (e.g. `mutual_funds.nav`, `income_tax.regime_comparison`)
with `primary_source`, optional `regulation_refs` (statute + provision), and
`data_endpoints` for live data where applicable.

### `policy` — enforcement rules

```yaml
require_citation: true
min_primary_sources_per_answer: 1
allowed_trust_levels_for_citation: [primary]
must_include_disclaimer: true
reject_if_no_primary_source: true
red_flags:
  - "should I buy"
  - "guaranteed returns"
  - "will this stock go up"
  ...
```

## Integration pattern for your retrieval layer

```python
from bfsi_advisor import SourceCatalog, AnswerValidator

catalog   = SourceCatalog("bfsi_sources.yaml", "bfsi_schema.json")
validator = AnswerValidator(catalog)

# 1. Classify user question -> (topic_id, subtopic_id)
topic_id, subtopic_id = classify(user_question)

# 2. Restrict retrieval to authoritative sources only
allowed = [s.id for s in catalog.primary_sources_for(topic_id, subtopic_id)]
#    ->  pass `allowed` as a metadata filter to your vector store

# 3. Generate answer from retrieved passages
answer_body = llm.generate(context=retrieved_passages)

# 4. Build citation from the schema's template
citation = catalog.build_citation(
    source_id="sebi",
    document_title="SEBI (Mutual Funds) Regulations, 1996",
    url="https://www.sebi.gov.in/legal/regulations/...",
    style="chatbot",
)

# 5. Append the right disclaimer
disclaimer = catalog.disclaimer_for(topic_id, subtopic_id)

final = f"{answer_body}\n\n{citation}\n\n_Disclaimer: {disclaimer}_"

# 6. HARD GATE — reject if any policy violation
violations = validator.validate(
    answer_text=final,
    topic_id=topic_id,
    subtopic_id=subtopic_id,
    cited_source_ids=["sebi"],
)
if violations:
    raise PolicyViolation(violations)

return final
```

## Live-data helper — AMFI NAV

AMFI's daily NAV feed is a free public pipe-delimited text file and is the ONLY
authoritative source for mutual fund NAV in India:

```python
from bfsi_advisor import SourceCatalog, fetch_amfi_nav

catalog = SourceCatalog("bfsi_sources.yaml", "bfsi_schema.json")
navs = fetch_amfi_nav(catalog)    # list of dicts
# [{'scheme_code': '129008', 'isin_growth': 'INF090I01KR8', ...}, ...]
```

Run it:

```bash
python3 bfsi_advisor.py --fetch-nav
```

## Adding a new subtopic

1. Open `bfsi_sources.yaml`, find the parent topic, add the subtopic with
   `display_name`, `primary_source` (must match a key in `sources:`), and any
   `regulation_refs`.
2. Run `python3 bfsi_advisor.py` — the loader cross-validates references and
   fails loudly if the primary source is unknown.
3. Bump `meta.version` (semver) and update `meta.last_updated`.

## Maintenance cadence

- **Daily**: nothing — schema is static, live feeds (like AMFI NAV) fetch on demand.
- **Quarterly**: re-check URLs in `key_pages` and `data_endpoints` (the `.gov.in`
  sites do restructure paths occasionally).
- **After every Union Budget**: review the `income_tax` topic and update
  `regulation_refs` with the new Finance Act citations and `effective_from` dates.
- **After any RBI / IRDAI / SEBI circular that affects a subtopic**: add a new
  `regulation_refs` entry with `date` and `reference`.

## Regulatory notes for you

Before shipping to the public:

1. **SEBI Investment Adviser Regulations 2013** — if your bot ever crosses into
   *personalised* recommendations ("buy fund X for your goals"), you likely need
   SEBI RIA registration. The `red_flags` list in this schema is a safety net, not
   legal cover. Treat it as a tripwire that forces a disclaimer-only fallback.
2. **IRDAI intermediary rules** — same principle for insurance.
3. **DPDP Act 2023** — the moment you log chat interactions containing PII,
   you're a Data Fiduciary. Build consent, purpose limitation, and deletion
   workflows into the product from day one.
4. **Citation freshness** — `policy.max_content_age_days` defaults to 365 days.
   Tighten it for compliance topics where rules change faster.

## License

Use freely. URLs and regulation references were verified against primary sources
as of the `meta.last_updated` date in the YAML — **re-verify before each
production release.**
