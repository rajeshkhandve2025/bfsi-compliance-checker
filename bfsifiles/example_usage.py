"""
example_usage.py
=================
Shows how to wire the schema into a public BFSI chatbot's retrieval layer
so that every answer is (a) grounded in a primary government/regulator source,
(b) carries the correct disclaimer, and (c) is rejected if it drifts into
personalised advice.
"""

from pathlib import Path

from bfsi_advisor import (
    SourceCatalog,
    AnswerValidator,
    PolicyViolation,
)

BASE = Path(__file__).parent
catalog = SourceCatalog(BASE / "bfsi_sources.yaml", BASE / "bfsi_schema.json")
validator = AnswerValidator(catalog)


# ------------------------------------------------------------------
# STEP 1 - Classify user question -> (topic_id, subtopic_id)
# ------------------------------------------------------------------
# In practice this is done by a small classifier (intent model, keyword
# matcher, or an LLM prompt constrained to the taxonomy). For this example
# we'll hard-code the classifications.
# ------------------------------------------------------------------

def classify(question: str) -> tuple[str, str]:
    q = question.lower()
    if "nav" in q:                               return ("mutual_funds", "nav")
    if "sip" in q:                               return ("mutual_funds", "sip")
    if "old" in q and "new" in q and "regime" in q:
        return ("income_tax", "regime_comparison")
    if "80c" in q:                               return ("income_tax", "section_80c")
    if "term insurance" in q:                    return ("insurance", "term_insurance")
    if "asba" in q:                              return ("ipo", "asba")
    if "cert-in" in q or "6 hour" in q or "6-hour" in q:
        return ("compliance", "certin_6hour")
    raise ValueError(f"Could not classify: {question!r}")


# ------------------------------------------------------------------
# STEP 2 - Retrieve content ONLY from authoritative sources
# ------------------------------------------------------------------
# Your actual retrieval is a vector search over a pre-indexed corpus.
# The important bit: filter retrieval results by source_id IN primary_sources
# for the classified topic. If nothing is found, REFUSE to answer.
# ------------------------------------------------------------------

def retrieve(topic_id: str, subtopic_id: str) -> dict:
    """
    Stub: in production, query your vector store with a metadata filter
    like  {"source_id": {"$in": allowed_source_ids}}.
    """
    primaries = catalog.primary_sources_for(topic_id, subtopic_id)
    allowed_ids = [s.id for s in primaries]

    # Fake retrieval result
    src = primaries[0]
    return {
        "source_id":      src.id,
        "source_name":    src.name,
        "url":            src.base_url,
        "document_title": f"{catalog.get_subtopic(topic_id, subtopic_id)['display_name']} — Reference",
        "passage":        f"[retrieved from {src.name}] authoritative passage here",
        "allowed_ids":    allowed_ids,
    }


# ------------------------------------------------------------------
# STEP 3 - Generate grounded answer + citation + disclaimer
# ------------------------------------------------------------------

def answer(question: str) -> str:
    topic_id, subtopic_id = classify(question)
    hit = retrieve(topic_id, subtopic_id)

    # Build the answer body from the retrieved passage (your LLM does this)
    body = (
        f"{hit['passage']}\n\n"
        f"Regarding {catalog.get_subtopic(topic_id, subtopic_id)['display_name']}: "
        f"[model-generated explanation constrained to the retrieved passage]"
    )

    citation = catalog.build_citation(
        source_id=hit["source_id"],
        document_title=hit["document_title"],
        url=hit["url"],
        style="chatbot",
    )

    disclaimer = catalog.disclaimer_for(topic_id, subtopic_id)

    final = f"{body}\n\n{citation}"
    if disclaimer:
        final += f"\n\n_Disclaimer: {disclaimer}_"

    # Step 4 - Validate before returning
    violations = validator.validate(
        answer_text=final,
        topic_id=topic_id,
        subtopic_id=subtopic_id,
        cited_source_ids=[hit["source_id"]],
    )
    if violations:
        raise PolicyViolation(
            "Answer rejected by policy:\n  - " + "\n  - ".join(violations)
        )

    return final


# ------------------------------------------------------------------
# STEP 5 - Negative test: answer that breaks policy gets rejected
# ------------------------------------------------------------------

def demo_rejected_answer() -> None:
    bad = (
        "You should buy the ABC Mutual Fund — it gives guaranteed returns of 15%."
    )
    violations = validator.validate(
        answer_text=bad,
        topic_id="mutual_funds",
        subtopic_id="sip",
        cited_source_ids=[],  # nothing cited
    )
    print("\n[demo] bad-answer policy check:")
    for v in violations:
        print("  -", v)


# ------------------------------------------------------------------
# main
# ------------------------------------------------------------------

if __name__ == "__main__":
    demo_questions = [
        "What is NAV of a mutual fund?",
        "Old vs new regime which is better?",
        "How does ASBA work in IPO?",
        "What is CERT-In 6 hour reporting rule?",
    ]
    for q in demo_questions:
        print("=" * 72)
        print("Q:", q)
        print("-" * 72)
        print(answer(q))

    demo_rejected_answer()
