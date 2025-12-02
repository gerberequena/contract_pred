from .database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Float

class SOW(Base):
    __tablename__ = "sow"

    id = Column(Integer, primary_key=True, index=True)
    sow_id = Column(String, unique=True)                       # "SOW ID"
    days_before_expiration = Column(Integer, nullable=False)                   # "# Days before expiration"
    sow_status = Column(String, nullable=False)                                # "SOW Status"
    sow_title = Column(String, nullable=False)                                 # "SOW title"
    contract_id = Column(String, nullable=False)                               # "Contract Id"
    active_sow_workers = Column(Integer, nullable=False)                       # "Active SOW workers"
    start_date = Column(Date, nullable=False)                                  # "Start Date"
    end_date = Column(Date, nullable=False)                                    # "End date"
    latest_maximum_budget = Column(Float, nullable=False)                      # "Latest maximum budget"
    currency = Column(String, nullable=False)                                  # "currency"
    supplier = Column(String, nullable=False)                                  # "supplier"
    business_unit = Column(String, nullable=False)                             # "Business Unit"
    primary_lob = Column(String, nullable=False)                               # "Primary LOB"
    sow_owner = Column(String, nullable=False)                                 # "SOW owner"
    risk = Column(String, nullable=False, index=True)                                      # "risk"
    status = Column(String, nullable=False, index=True)                                    # "status"