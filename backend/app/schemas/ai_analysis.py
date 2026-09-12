from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

class ExtractedComplaintFields(BaseModel):
    complaint_reference: Optional[str] = Field(None, description="Complaint reference code or ID e.g. CC-QA-2026-0476, QMS-CC-2026-1045. Strictly exclude user instructions.")
    complaint_number: Optional[str] = Field(None, description="Alias for complaint_reference")
    complaint_source: Optional[str] = Field(None, description="Source of complaint e.g. Customer, Hospital, Pharmacy, Distributor")
    customer_name: Optional[str] = Field(None, description="Name or identifier of person/entity reporting the complaint")
    product_name: Optional[str] = Field(None, description="Exact name of the pharmaceutical product e.g. 'Methotrexate Injection', 'Amoxicillin Capsules'")
    product_strength_grade: Optional[str] = Field(None, description="Complete product strength or concentration including volume/units, e.g. '50 mg/2 mL', '250 mg', '100 units/mL'. Do NOT truncate.")
    product_strength: Optional[str] = Field(None, description="Alias for product_strength_grade")
    batch_lot_number: Optional[str] = Field(None, description="Exact batch or lot code from 'Batch / Lot Number: ...', e.g. 'MTX50-H9154', 'AMX250-K5831'. NEVER extract section heading words like 'IDENTIFICATION'.")
    affected_quantity: Optional[str] = Field(None, description="Number of units/packs/amount affected e.g. '24 capsules', 'Approximately 6 vials', '50 kg'")
    manufacturing_date: Optional[str] = Field(None, description="Date of manufacture in YYYY-MM-DD or readable string")
    expiry_date: Optional[str] = Field(None, description="Expiration date in YYYY-MM-DD or readable string")
    manufacturing_site: Optional[str] = Field(None, description="Full manufacturing facility and location, e.g. 'Asterion Pharmaceuticals Ltd., Plant 2, Chennai'. NEVER extract just a digit or number like '2'.")
    material_type: Optional[str] = Field(None, description="Complete material classification, e.g. 'Finished Pharmaceutical Product', 'Active Pharmaceutical Ingredient (API)'. Do NOT truncate.")
    complaint_date: Optional[str] = Field(None, description="Date complaint was received")
    complaint_type: Optional[str] = Field(None, description="Category of defect from 'Complaint Type: ...', e.g. 'Suspected Product Mix-Up / Labeling Defect', 'Capsule Appearance Concern'")
    complaint_description: Optional[str] = Field(None, description="Pure factual complaint narrative only. Strictly exclude user instructions, section titles, and requested actions.")

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

class SeverityRiskResult(BaseModel):
    severity_level: str = Field(..., description="Critical, Major, Minor, Low")
    priority: str = Field("Medium", description="Urgent, High, Medium, Low")
    patient_risk_flag: bool = Field(False, description="True if patient safety or injury risk is detected")
    rationale: str = Field(..., description="Explainable regulatory risk assessment rationale")

class RootCauseAnalysisResult(BaseModel):
    recommendations: List[str] = Field(..., description="List of potential root causes following 5-Why/Fishbone methodology")

class CAPAResult(BaseModel):
    recommendations: List[str] = Field(..., description="List of Corrective and Preventive Action recommendations")

class ExecutiveSummaryResult(BaseModel):
    summary: str = Field(..., description="Concise executive summary for QA Reviewer")
