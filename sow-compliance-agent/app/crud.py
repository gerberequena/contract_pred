# crud.py
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from .models import SOW
from .schemas import CreateSOWRequest


KEY_MAPPING: Dict[str, str] = {
    "SOW ID": "sow_id",
    "# Days before expiration": "days_before_expiration",
    "SOW Status": "sow_status",
    "SOW title": "sow_title",
    "Contract Id": "contract_id",
    "Active SOW workers": "active_sow_workers",
    "Start Date": "start_date",
    "End date": "end_date",
    "Latest maximum budget": "latest_maximum_budget",
    "currency": "currency",
    "supplier": "supplier",
    "Business Unit": "business_unit",
    "Primary LOB": "primary_lob",
    "SOW owner": "sow_owner",
    "risk": "risk",
    "status": "status",
}


def normalize_sow_data(raw_dict: dict) -> dict:
    normalized = {}
    for key, value in raw_dict.items():
        if key in KEY_MAPPING:
            normalized[KEY_MAPPING[key]] = value
    return normalized


def create_or_update_sow(
    db: Session, raw_sow_dict: dict
) -> Tuple[SOW, str]:
    """
    If sow_id exists in DB: update only risk & status.
    Otherwise: create a new SOW row.
    Returns (sow_obj, "created" | "updated").
    """
    normalized = normalize_sow_data(raw_sow_dict)

    sow_id = normalized.get("sow_id")
    if not sow_id:
        raise ValueError("sow_id is required to create or update a SOW")

    existing = db.query(SOW).filter(SOW.sow_id == sow_id).first()

    if existing:
        if "risk" in normalized:
            existing.risk = normalized["risk"]
        if "status" in normalized:
            existing.status = normalized["status"]

        db.commit()
        db.refresh(existing)
        return existing, "updated"

    sow_request = CreateSOWRequest(**normalized)
    new_sow = SOW(**sow_request.model_dump())

    db.add(new_sow)
    db.commit()
    db.refresh(new_sow)
    return new_sow, "created"
