from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, model_validator, ConfigDict

class ComplaintFieldsBase(BaseModel):
    complaint_reference: Optional[str] = Field(None, example="CC-QA-2026-0476")
    complaint_number: Optional[str] = Field(None, example="CC-QA-2026-0476")
    complaint_source: Optional[str] = Field(None, example="Healthcare Professional")
    customer_name: Optional[str] = Field(None, example="Dr. Robert Vance, St. Jude Hospital")
    product_name: Optional[str] = Field(None, example="Metformin HCI")
    product_strength_grade: Optional[str] = Field(None, example="500 mg")
    product_strength: Optional[str] = Field(None, example="500 mg")
    batch_lot_number: Optional[str] = Field(None, example="MET500-KP4821")
    affected_quantity: Optional[str] = Field(None, example="15 blister packs")
    manufacturing_date: Optional[str] = Field(None, example="2026-03-18")
    expiry_date: Optional[str] = Field(None, example="2029-03-17")
    manufacturing_site: Optional[str] = Field(None, example="Site Alpha - Dublin")
    material_type: Optional[str] = Field(None, example="Finished Product")
    complaint_date: Optional[str] = Field(None, example="2026-09-11")
    complaint_type: Optional[str] = Field(None, example="Broken Tablets / Packaging Defect")
    complaint_description: Optional[str] = Field(None, example="Broken tablets inside 15 blister packs.")

    @model_validator(mode="after")
    def sync_aliases(self):
        st = self.product_strength_grade or self.product_strength
        if st:
            self.product_strength_grade = st
            self.product_strength = st
        ref = self.complaint_reference or self.complaint_number
        if ref:
            self.complaint_reference = ref
            self.complaint_number = ref
        return self

class ComplaintCreateSchema(ComplaintFieldsBase):
    raw_input_text: Optional[str] = None
    document_name: Optional[str] = None
    completeness_score: Optional[float] = 0.0
    is_complete: Optional[bool] = False
    missing_fields: Optional[List[str]] = []
    severity_level: Optional[str] = None
    priority: Optional[str] = None
    patient_risk_flag: Optional[bool] = False
    risk_rationale: Optional[str] = None
    is_possible_duplicate: Optional[bool] = False
    duplicate_reasons: Optional[List[str]] = []
    root_cause_recommendations: Optional[List[str]] = []
    capa_recommendations: Optional[List[str]] = []
    executive_summary: Optional[str] = None

class ComplaintResponseSchema(ComplaintCreateSchema):
    id: str
    complaint_number: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ComplaintProcessRequest(BaseModel):
    text: str = Field(..., description="Raw text of customer complaint")

class ComplaintListResponse(BaseModel):
    items: List[ComplaintResponseSchema]
    total: int
