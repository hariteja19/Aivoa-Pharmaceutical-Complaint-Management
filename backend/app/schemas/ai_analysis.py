from typing import Optional, List
from pydantic import BaseModel, Field

class ExtractedComplaintFields(BaseModel):
    complaint_source: Optional[str] = Field(None, description="Source of complaint e.g. Customer, Hospital, Pharmacy, Distributor")
    customer_name: Optional[str] = Field(None, description="Name or identifier of person/entity reporting the complaint")
    product_name: Optional[str] = Field(None, description="Name of the pharmaceutical product")
    product_strength_grade: Optional[str] = Field(None, description="Dosage strength or material grade e.g. 500 mg, 10 mg/mL, USP")
    batch_lot_number: Optional[str] = Field(None, description="Batch or lot identification code")
    affected_quantity: Optional[str] = Field(None, description="Number of units/packs/amount affected e.g. 15 blister packs, 50 kg")
    manufacturing_date: Optional[str] = Field(None, description="Date of manufacture in YYYY-MM-DD or readable string")
    expiry_date: Optional[str] = Field(None, description="Expiration date in YYYY-MM-DD or readable string")
    manufacturing_site: Optional[str] = Field(None, description="Manufacturing site/plant location")
    material_type: Optional[str] = Field(None, description="Material type e.g. Finished Product, API, Excipient, Packaging")
    complaint_date: Optional[str] = Field(None, description="Date complaint was received")
    complaint_type: Optional[str] = Field(None, description="Category of defect e.g. Packaging Defect, Broken Tablets, Contamination, Label Error")
    complaint_description: Optional[str] = Field(None, description="Detailed narrative description of the complaint")

class SeverityRiskResult(BaseModel):
    severity_level: str = Field("Low", description="Critical, Major, Minor, Low")
    priority: str = Field("Medium", description="Urgent, High, Medium, Low")
    patient_risk_flag: bool = Field(False, description="True if patient safety or injury risk is detected")
    rationale: str = Field(..., description="Explainable regulatory risk assessment rationale")

class RootCauseAnalysisResult(BaseModel):
    recommendations: List[str] = Field(..., description="List of potential root causes following 5-Why/Fishbone methodology")

class CAPAResult(BaseModel):
    recommendations: List[str] = Field(..., description="List of Corrective and Preventive Action recommendations")

class ExecutiveSummaryResult(BaseModel):
    summary: str = Field(..., description="Concise executive summary for QA Reviewer")
