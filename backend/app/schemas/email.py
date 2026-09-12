from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class EmailDraftRequest(BaseModel):
    complaint_number: Optional[str] = Field(None, description="Complaint reference ID")
    complaint_source: Optional[str] = Field(None, description="Origin or reporter channel")
    customer_name: Optional[str] = Field(None, description="Customer or facility name")
    product_name: Optional[str] = Field(None, description="Product commercial name")
    product_strength_grade: Optional[str] = Field(None, description="Strength or grade")
    batch_lot_number: Optional[str] = Field(None, description="Batch or lot identifier")
    affected_quantity: Optional[str] = Field(None, description="Quantity affected")
    manufacturing_date: Optional[str] = Field(None, description="Manufacturing date")
    expiry_date: Optional[str] = Field(None, description="Expiry date")
    manufacturing_site: Optional[str] = Field(None, description="Manufacturing site / facility")
    material_type: Optional[str] = Field(None, description="Material type")
    complaint_date: Optional[str] = Field(None, description="Date complaint was received")
    complaint_type: Optional[str] = Field(None, description="Classification of defect")
    complaint_description: Optional[str] = Field(None, description="Detailed narrative of issue")
    severity_level: Optional[str] = Field("Low", description="Severity classification")
    priority: Optional[str] = Field("Medium", description="Handling priority")
    completeness_score: Optional[float] = Field(None, description="Field completeness score")
    patient_risk_flag: Optional[bool] = Field(None, description="Whether patient safety hazard detected")
    risk_rationale: Optional[str] = Field(None, description="Regulatory risk rationale")
    is_possible_duplicate: Optional[bool] = Field(None, description="Whether recurring complaint on same batch")
    duplicate_reasons: Optional[List[str]] = Field(default_factory=list, description="Duplicate match explanations")
    root_cause_recommendations: Optional[List[str]] = Field(default_factory=list, description="AI root cause hypotheses")
    capa_recommendations: Optional[List[str]] = Field(default_factory=list, description="AI CAPA recommendations")
    executive_summary: Optional[str] = Field(None, description="Executive summary narrative")

class EmailDraftResponse(BaseModel):
    to: str = Field("Quality Assurance Team", description="Recipient name or department")
    subject: str = Field(..., description="Subject line for the complaint email")
    body: str = Field(..., description="Full body text of the complaint notification email")
