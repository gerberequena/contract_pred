# schemas.py
from datetime import date
from pydantic import BaseModel


class CreateSOWRequest(BaseModel):
    sow_id: str
    days_before_expiration: int
    sow_status: str
    sow_title: str
    contract_id: str
    active_sow_workers: int
    start_date: date
    end_date: date
    latest_maximum_budget: float
    currency: str
    supplier: str
    business_unit: str
    primary_lob: str
    sow_owner: str
    risk: str
    status: str
