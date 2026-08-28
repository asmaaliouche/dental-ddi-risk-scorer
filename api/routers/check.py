"""
api/routers/check.py
--------------------
POST /check

Accepts a list of patient drug names and returns all known drug-drug
interaction risks with dental prescribing drugs, ranked by composite
risk score (highest first).

Matching is case-insensitive. Drug names are normalised to lowercase
before lookup against the pre-computed scores.parquet dataset.
"""

from __future__ import annotations

import logging
import math

from fastapi import APIRouter, HTTPException, Request

from api.schemas import CheckRequest, CheckResponse, InteractionResult

log = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/check",
    response_model=CheckResponse,
    summary="Check drug interactions",
    description=(
        "Given a list of drugs the patient is currently taking, returns all "
        "known drug-drug interactions with dental prescribing drugs, ranked by "
        "risk score (highest first). Drug names are matched case-insensitively "
        "against the TWOSIDES pharmacovigilance database."
    ),
)
async def check_interactions(body: CheckRequest, request: Request) -> CheckResponse:
    """
    Filter the pre-computed scores DataFrame by patient drug name and
    return ranked interaction results.

    Raises:
        HTTPException(503): if scores.parquet was not loaded on startup.
    """
    scores_df = request.app.state.scores
    if scores_df is None:
        log.error("POST /check called but scores DataFrame is not loaded.")
        raise HTTPException(
            status_code=503,
            detail="Interaction database not loaded. Run `make score` to generate scores.parquet.",
        )

    # Normalise input drug names to lowercase for case-insensitive matching
    patient_drugs_input = [d.lower().strip() for d in body.patient_drugs]
    log.info(
        "POST /check — checking %d drug(s): %s",
        len(patient_drugs_input),
        ", ".join(patient_drugs_input),
    )

    # Boolean mask: keep rows where the patient_drug_name matches any input drug
    mask = scores_df["patient_drug_name"].str.lower().isin(patient_drugs_input)
    matched = scores_df[mask].copy()

    # Track which patient drugs had at least one interaction match
    matched_patient_drugs = set(matched["patient_drug_name"].str.lower().unique())
    not_found = [d for d in patient_drugs_input if d not in matched_patient_drugs]

    if matched.empty:
        log.info("No interactions found for: %s", patient_drugs_input)
        return CheckResponse(
            interactions=[],
            patient_drugs_checked=patient_drugs_input,
            patient_drugs_not_found=not_found,
            total_interactions=0,
        )

    # Sort by composite risk score, highest first
    matched = matched.sort_values("risk_score", ascending=False)

    interactions: list[InteractionResult] = []
    for _, row in matched.iterrows():
        # top_adverse_effects is stored as a pipe-separated string in parquet
        top_ae_raw = row.get("top_adverse_effects", "") or ""
        top_ae = [ae.strip() for ae in str(top_ae_raw).split("|") if ae.strip()]

        # Guard against NaN PRR values (can occur for pairs with sparse data)
        prr_max = row["prr_max"]
        if isinstance(prr_max, float) and math.isnan(prr_max):
            prr_max = 0.0

        interactions.append(
            InteractionResult(
                dental_drug=str(row["dental_drug_name"]),
                dental_drug_display=str(row.get("dental_drug_display") or row["dental_drug_name"]),
                dental_drug_category=str(row["dental_drug_category"]),
                dental_drug_notes=str(row.get("dental_drug_notes") or ""),
                patient_drug=str(row["patient_drug_name"]),
                risk_score=round(float(row["risk_score"]), 1),
                severity_bin=str(row["severity_bin"]),
                top_adverse_effects=top_ae,
                prr_max=round(float(prr_max), 1),
                n_adverse_effects=int(row["n_adverse_effects"]),
            )
        )

    log.info(
        "POST /check — returned %d interaction(s) (%d not found in DB)",
        len(interactions),
        len(not_found),
    )

    return CheckResponse(
        interactions=interactions,
        patient_drugs_checked=patient_drugs_input,
        patient_drugs_not_found=not_found,
        total_interactions=len(interactions),
    )
