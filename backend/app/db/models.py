import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    complaint_number = Column(String, unique=True, index=True, nullable=False)
    
    # 13 Core Structured Complaint Fields
    complaint_reference = Column(String, nullable=True, index=True)
    complaint_source = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    product_name = Column(String, nullable=False, index=True)
    product_strength_grade = Column(String, nullable=True)
    batch_lot_number = Column(String, nullable=False, index=True)
    affected_quantity = Column(String, nullable=True)
    manufacturing_date = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    manufacturing_site = Column(String, nullable=True)
    material_type = Column(String, nullable=True)
    complaint_date = Column(String, nullable=False, index=True)
    complaint_type = Column(String, nullable=False)
    complaint_description = Column(Text, nullable=False)

    # AI Analysis & Risk Findings
    completeness_score = Column(Float, default=0.0)
    is_complete = Column(Boolean, default=False)
    missing_fields = Column(JSON, default=list)
    
    severity_level = Column(String, default="Low", index=True)  # Critical, Major, Minor, Low
    patient_risk_flag = Column(Boolean, default=False)
    risk_rationale = Column(Text, nullable=True)
    
    is_possible_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(String, ForeignKey("complaints.id"), nullable=True)
    duplicate_reasons = Column(JSON, default=list)
    
    root_cause_recommendations = Column(JSON, default=list)
    capa_recommendations = Column(JSON, default=list)
    executive_summary = Column(Text, nullable=True)
    
    # Metadata & Tracking
    raw_input_text = Column(Text, nullable=True)
    document_name = Column(String, nullable=True)
    status = Column(String, default="Logged")  # Logged, Under Investigation, CAPA Pending, Closed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    duplicate_parent = relationship("Complaint", remote_side=[id], backref="child_duplicates")
