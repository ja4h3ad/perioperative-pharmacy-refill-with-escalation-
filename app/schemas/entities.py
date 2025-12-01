# app/schemas/entities.py

from pydantic import BaseModel, Field, field_validator
from typing import Optional

class ExtractedEntities(BaseModel):
    """
    output of entity extraction node (slot filling)
    contains all required / optional slots for refill request
    """

    # required slots
    patient_id:  str = Field(
        ...,
        regex=r"^\d{6,8}$",
        description="patient id / MRN",
        example="12345678"
    )

    drug_name:  str = Field(
        ...,
        min_length=2,
        description="Medication name (generic or brand)",
        example="Lisinopril"
    )

    dose:  str = Field(
        ...,
        regex=r"^\d+(\.\d+)?\s*(mg|mcg|g|mL)$",
        description="Dose with unit",
        example="10mg"
    )
    quantity: int = Field(
        ...,
        gt=0,
        le=365,
        description="Number of tablets/capsules or days supply",
        example=30
    )
    # optional slots
    frequency:  Optional[str] = Field(
        None,
        description="dosing schedule",
        example="daily"
    )

    # metadata
    missing_slots: list[str] = Field(
        default_factory=list,
        description="List of required slots not yet filled"
    )

    @field_validator('missing_slots', always=True)
    def check_missing_slots(cls, v, values):
        """Auto-populate missing required slots"""
        required = ['patient_id', 'drug_name', 'dose', 'quantity']
        missing = [slot for slot in required if not values.get(slot)]
        return missing