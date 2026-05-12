# app/src/core/tools/phases/research_tools/clinical_trials.py

import time
from typing import Optional

import requests
from langchain_core.tools import tool

from app.src.utils.logger import get_logger

logger = get_logger(__name__)

BASE_URL = "https://clinicaltrials.gov/api/v2"
TIMEOUT = 30
FIELDS = "NCTId,BriefTitle,OverallStatus,Phases,InterventionName,InterventionType,PrimaryOutcomeMeasure,LocationFacility,LocationCity,LocationCountry"


def _get(url: str, params: dict, retries: int = 1) -> dict:
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < retries:
                time.sleep(1)
                continue
            raise


def _format_trial(study: dict) -> str:
    p = study.get("protocolSection", {})
    id_module = p.get("identificationModule", {})
    status_module = p.get("statusModule", {})
    design_module = p.get("designModule", {})
    arms_module = p.get("armsInterventionsModule", {})
    outcomes_module = p.get("outcomesModule", {})
    contacts_module = p.get("contactsLocationsModule", {})

    nct_id = id_module.get("nctId", "N/A")
    title = id_module.get("briefTitle", "N/A")
    status = status_module.get("overallStatus", "N/A")
    phases = ", ".join(design_module.get("phases", [])) or "N/A"

    interventions = arms_module.get("interventions", [])
    intervention_str = ", ".join(
        f"{i.get('name', '')} ({i.get('type', '')})" for i in interventions
    ) or "N/A"

    primary_outcomes = outcomes_module.get("primaryOutcomes", [])
    primary_str = "; ".join(o.get("measure", "") for o in primary_outcomes) or "N/A"

    locations = contacts_module.get("locations", [])
    location_str = ", ".join(
        f"{loc.get('facility', '')} - {loc.get('city', '')}, {loc.get('country', '')}"
        for loc in locations[:3]
    ) or "N/A"

    return (
        f"### {nct_id} - {title}\n"
        f"- **Status**: {status}\n"
        f"- **Phase**: {phases}\n"
        f"- **Interventions**: {intervention_str}\n"
        f"- **Primary Outcome**: {primary_str}\n"
        f"- **Locations**: {location_str}\n"
    )


@tool
def search_clinical_trials(
    condition: str,
    status: Optional[str] = None,
    phase: Optional[str] = None,
    max_results: int = 10,
) -> str:
    """Search ClinicalTrials.gov for trials related to a disease or condition.

    Args:
        condition: Disease or condition to search for, e.g. 'Alzheimer'.
        status: Optional trial status filter e.g. 'RECRUITING', 'COMPLETED'.
        phase: Optional phase filter e.g. 'PHASE2', 'PHASE3'.
        max_results: Maximum number of results to return (default 10).

    Returns:
        Markdown formatted list of matching clinical trials.
    """
    params = {
        "query.cond": condition,
        "pageSize": max_results,
        "fields": FIELDS,
        "format": "json",
    }
    if status:
        params["filter.overallStatus"] = status.upper()
    if phase:
        params["filter.advanced"] = f"AREA[Phase]{phase.upper()}"

    try:
        data = _get(f"{BASE_URL}/studies", params)
        studies = data.get("studies", [])

        if not studies:
            return f"## Clinical Trials\n\nNo trials found for condition: **{condition}**."

        lines = [f"## Clinical Trials for: {condition}\n"]
        lines.append(f"*Found {len(studies)} result(s)*\n\n---\n")
        for i, study in enumerate(studies, 1):
            lines.append(f"### {i}. {_format_trial(study)}\n---\n")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"[ClinicalTrials] search failed: {e}")
        return f"## Clinical Trials\n\nError searching ClinicalTrials.gov: {e}"


@tool
def get_trial_details(nct_id: str) -> str:
    """Retrieve full details for a specific clinical trial by NCT ID.

    Args:
        nct_id: The NCT identifier e.g. 'NCT01234567'.

    Returns:
        Full trial details formatted as markdown.
    """
    try:
        data = _get(f"{BASE_URL}/studies/{nct_id}", {"format": "json"})
        p = data.get("protocolSection", {})

        id_module = p.get("identificationModule", {})
        status_module = p.get("statusModule", {})
        design_module = p.get("designModule", {})
        desc_module = p.get("descriptionModule", {})
        eligibility_module = p.get("eligibilityModule", {})
        arms_module = p.get("armsInterventionsModule", {})
        outcomes_module = p.get("outcomesModule", {})
        contacts_module = p.get("contactsLocationsModule", {})

        title = id_module.get("briefTitle", "N/A")
        official_title = id_module.get("officialTitle", "")
        status = status_module.get("overallStatus", "N/A")
        phases = ", ".join(design_module.get("phases", [])) or "N/A"
        brief_summary = desc_module.get("briefSummary", "N/A")
        eligibility = eligibility_module.get("eligibilityCriteria", "N/A")[:500] + "..."

        interventions = arms_module.get("interventions", [])
        intervention_str = "\n".join(
            f"  - {i.get('name', '')} ({i.get('type', '')})" for i in interventions
        ) or "  - N/A"

        primary_outcomes = outcomes_module.get("primaryOutcomes", [])
        primary_str = "\n".join(
            f"  - {o.get('measure', '')}" for o in primary_outcomes
        ) or "  - N/A"

        secondary_outcomes = outcomes_module.get("secondaryOutcomes", [])
        secondary_str = "\n".join(
            f"  - {o.get('measure', '')}" for o in secondary_outcomes[:5]
        ) or "  - N/A"

        locations = contacts_module.get("locations", [])
        location_str = "\n".join(
            f"  - {loc.get('facility', '')} — {loc.get('city', '')}, {loc.get('country', '')}"
            for loc in locations[:5]
        ) or "  - N/A"

        return (
            f"## Trial: {nct_id}\n\n"
            f"**Title**: {title}\n"
            f"**Official Title**: {official_title}\n"
            f"**Status**: {status}\n"
            f"**Phase**: {phases}\n\n"
            f"### Summary\n{brief_summary}\n\n"
            f"### Interventions\n{intervention_str}\n\n"
            f"### Primary Outcomes\n{primary_str}\n\n"
            f"### Secondary Outcomes\n{secondary_str}\n\n"
            f"### Eligibility (excerpt)\n{eligibility}\n\n"
            f"### Locations\n{location_str}\n"
        )

    except Exception as e:
        logger.error(f"[ClinicalTrials] get_trial_details failed for {nct_id}: {e}")
        return f"## Trial Details\n\nError retrieving trial {nct_id}: {e}"