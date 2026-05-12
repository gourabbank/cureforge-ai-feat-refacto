# app/src/core/tools/hypothesis_bank/tools.py

import json
from typing import Optional
from langchain_core.tools import tool

from app.src.core.tools.hypothesis_bank import storage


@tool
def add_to_hypothesis_bank(
    hypothesis_text: str,
    disease: str,
    phase_origin: str = "unknown",
    keywords: str = "[]",
    efficacy_score: float = 0.0,
    safety_score: float = 0.0,
    notes: str = "",
) -> str:
    """
    Add a hypothesis to the persistent hypothesis bank.
    Embeds and stores the hypothesis for future semantic retrieval.

    Args:
        hypothesis_text: Full text of the hypothesis.
        disease: Disease this hypothesis targets.
        phase_origin: Research phase that generated it (research/hypothesize/test/synthesize).
        keywords: JSON array string of keywords e.g. '["VEGF", "angiogenesis"]'.
        efficacy_score: Initial predicted efficacy (0.0–1.0).
        safety_score: Initial predicted safety (0.0–1.0).
        notes: Any additional notes or context.

    Returns:
        JSON string with hypothesis_id and confirmation.
    """
    try:
        kw_list = json.loads(keywords) if isinstance(keywords, str) else keywords
    except json.JSONDecodeError:
        kw_list = []

    hyp_id = storage.add_hypothesis(
        text=hypothesis_text,
        disease=disease,
        phase_origin=phase_origin,
        keywords=kw_list,
        efficacy_score=efficacy_score,
        safety_score=safety_score,
        notes=notes,
    )
    return json.dumps({
        "status": "success",
        "hypothesis_id": hyp_id,
        "message": f"Hypothesis stored with ID {hyp_id}",
    })


@tool
def search_hypothesis_bank(
    query: str,
    disease_filter: Optional[str] = None,
    keyword_filter: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """
    Semantic search over the hypothesis bank.
    Returns the most relevant prior hypotheses for a given query.

    Args:
        query: Natural language query (e.g. "mTOR inhibition in glioblastoma").
        disease_filter: Optional. Only return hypotheses for this disease.
        keyword_filter: Optional. Only return hypotheses containing this keyword.
        top_k: Number of results to return (default 5).

    Returns:
        JSON string with list of matching hypotheses and similarity scores.
    """
    results = storage.search_hypotheses(
        query=query,
        disease_filter=disease_filter,
        keyword_filter=keyword_filter,
        top_k=top_k,
    )
    if not results:
        return json.dumps({"status": "success", "count": 0, "hypotheses": [],
                           "message": "No hypotheses found matching the query."})

    return json.dumps({
        "status": "success",
        "count": len(results),
        "hypotheses": [
            {
                "id": r["id"],
                "disease": r["disease"],
                "phase_origin": r["phase_origin"],
                "score": round(r["score"], 4),
                "efficacy_score": r["efficacy_score"],
                "safety_score": r["safety_score"],
                "keywords": r["keywords"],
                "text_preview": r["text"][:200] + "…" if len(r["text"]) > 200 else r["text"],
                "created_at": r["created_at"],
            }
            for r in results
        ],
    }, indent=2)


@tool
def get_hypothesis_by_id(hypothesis_id: str) -> str:
    """
    Retrieve a specific hypothesis by its ID.

    Args:
        hypothesis_id: The UUID of the hypothesis to retrieve.

    Returns:
        JSON string with full hypothesis data including all metadata.
    """
    result = storage.get_hypothesis(hypothesis_id)
    if result is None:
        return json.dumps({"status": "error", "message": f"No hypothesis found with ID {hypothesis_id}"})
    return json.dumps({"status": "success", "hypothesis": result}, indent=2)


@tool
def list_hypotheses(
    disease: Optional[str] = None,
    phase_filter: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    List hypotheses with optional filters.

    Args:
        disease: Optional filter by disease name.
        phase_filter: Optional filter by phase (research/hypothesize/test/synthesize).
        limit: Maximum number of results (default 20).

    Returns:
        JSON string with summary list of hypotheses.
    """
    rows = storage.list_hypotheses(disease=disease, phase_filter=phase_filter, limit=limit)
    if not rows:
        return json.dumps({"status": "success", "count": 0, "hypotheses": [],
                           "message": "No hypotheses found."})
    return json.dumps({
        "status": "success",
        "count": len(rows),
        "hypotheses": [
            {
                "id": r["id"],
                "disease": r["disease"],
                "phase_origin": r["phase_origin"],
                "efficacy_score": r["efficacy_score"],
                "safety_score": r["safety_score"],
                "keywords": r["keywords"],
                "retrieval_count": r["retrieval_count"],
                "created_at": r["created_at"],
                "text_preview": r["text"][:150] + "…" if len(r["text"]) > 150 else r["text"],
            }
            for r in rows
        ],
    }, indent=2)


@tool
def update_hypothesis_scores(
    hypothesis_id: str,
    new_efficacy_score: float,
    new_safety_score: float,
    update_reason: str = "",
) -> str:
    """
    Update efficacy and safety scores for a hypothesis after testing.

    Args:
        hypothesis_id: The UUID of the hypothesis to update.
        new_efficacy_score: Updated efficacy score (0.0–1.0).
        new_safety_score: Updated safety score (0.0–1.0).
        update_reason: Reason for update, e.g. "Phase 2 trial showed 40% response rate".

    Returns:
        JSON confirmation string.
    """
    success = storage.update_scores(
        hyp_id=hypothesis_id,
        efficacy_score=new_efficacy_score,
        safety_score=new_safety_score,
        update_reason=update_reason,
    )
    if not success:
        return json.dumps({"status": "error", "message": f"Hypothesis {hypothesis_id} not found."})
    return json.dumps({
        "status": "success",
        "hypothesis_id": hypothesis_id,
        "new_efficacy_score": new_efficacy_score,
        "new_safety_score": new_safety_score,
        "message": "Scores updated successfully.",
    })


@tool
def export_hypothesis_bank(disease: Optional[str] = None) -> str:
    """
    Export all hypotheses (or for a specific disease) as a Markdown report.

    Args:
        disease: Optional. Filter export to one disease.

    Returns:
        Markdown-formatted string of all hypotheses.
    """
    return storage.export_to_markdown(disease=disease)


# Convenience list for registration
HYPOTHESIS_BANK_TOOLS = [
    add_to_hypothesis_bank,
    search_hypothesis_bank,
    get_hypothesis_by_id,
    list_hypotheses,
    update_hypothesis_scores,
    export_hypothesis_bank,
]