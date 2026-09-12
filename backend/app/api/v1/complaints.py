import random
import string
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.logging import logger
from app.db.models import Complaint
from app.schemas.complaint import (
    ComplaintProcessRequest,
    ComplaintCreateSchema,
    ComplaintResponseSchema,
    ComplaintListResponse
)
from app.services.doc_parser import DocumentParserService
from app.workflow.graph import complaint_workflow_app

router = APIRouter(prefix="/complaints", tags=["Complaints"])

def generate_complaint_number() -> str:
    from datetime import datetime
    year = datetime.now().year
    rand_str = ''.join(random.choices(string.digits, k=5))
    return f"CMP-{year}-{rand_str}"

@router.post("/process")
def process_text_complaint(
    payload: ComplaintProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process raw text complaint through LangGraph state machine.
    Returns structured fields, validation scores, risk assessment, duplicate check, root causes, CAPA, and summary.
    """
    if not payload.text or not payload.text.strip():
        raise HTTPException(status_code=400, detail="Complaint text cannot be empty.")

    initial_state = {
        "raw_input_text": payload.text,
        "document_filename": None,
        "db_session": db,
        "extracted_fields": {},
        "validation": {},
        "risk_assessment": {},
        "duplicates": {},
        "root_cause_recommendations": [],
        "capa_recommendations": [],
        "executive_summary": "",
        "error_logs": []
    }

    try:
        final_state = complaint_workflow_app.invoke(initial_state)
        # Remove DB session before returning JSON
        final_state.pop("db_session", None)
        return final_state
    except Exception as e:
        logger.error(f"Error in complaint workflow execution: {e}")
        raise HTTPException(status_code=500, detail=f"AI workflow execution error: {str(e)}")

@router.post("/upload")
async def upload_complaint_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload PDF, DOCX, or TXT complaint document, parse text, and run through LangGraph pipeline.
    """
    try:
        content = await file.read()
        extracted_text = DocumentParserService.extract_text(file.filename, content)
    except Exception as e:
        logger.error(f"Document upload parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to process document: {str(e)}")

    initial_state = {
        "raw_input_text": extracted_text,
        "document_filename": file.filename,
        "db_session": db,
        "extracted_fields": {},
        "validation": {},
        "risk_assessment": {},
        "duplicates": {},
        "root_cause_recommendations": [],
        "capa_recommendations": [],
        "executive_summary": "",
        "error_logs": []
    }

    try:
        final_state = complaint_workflow_app.invoke(initial_state)
        final_state.pop("db_session", None)
        return {
            "filename": file.filename,
            "extracted_text": extracted_text,
            "analysis": final_state
        }
    except Exception as e:
        logger.error(f"Error executing graph on uploaded document: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing document content: {str(e)}")

@router.post("", response_model=ComplaintResponseSchema)
def create_complaint_record(
    payload: ComplaintCreateSchema,
    db: Session = Depends(get_db)
):
    """
    Save approved complaint record to PostgreSQL / Database.
    """
    try:
        cmp_number = generate_complaint_number()
        new_complaint = Complaint(
            complaint_number=cmp_number,
            complaint_source=payload.complaint_source,
            customer_name=payload.customer_name,
            product_name=payload.product_name or "Unspecified Product",
            product_strength_grade=payload.product_strength_grade,
            batch_lot_number=payload.batch_lot_number or "UNSPECIFIED",
            affected_quantity=payload.affected_quantity,
            manufacturing_date=payload.manufacturing_date,
            expiry_date=payload.expiry_date,
            manufacturing_site=payload.manufacturing_site,
            material_type=payload.material_type,
            complaint_date=payload.complaint_date or "2026-09-11",
            complaint_type=payload.complaint_type or "General Quality Issue",
            complaint_description=payload.complaint_description or "",
            completeness_score=payload.completeness_score or 0.0,
            is_complete=payload.is_complete or False,
            missing_fields=payload.missing_fields or [],
            severity_level=payload.severity_level or "Low",
            patient_risk_flag=payload.patient_risk_flag or False,
            risk_rationale=payload.risk_rationale,
            is_possible_duplicate=payload.is_possible_duplicate or False,
            duplicate_reasons=payload.duplicate_reasons or [],
            root_cause_recommendations=payload.root_cause_recommendations or [],
            capa_recommendations=payload.capa_recommendations or [],
            executive_summary=payload.executive_summary,
            raw_input_text=payload.raw_input_text,
            document_name=payload.document_name,
            status="Logged"
        )
        db.add(new_complaint)
        db.commit()
        db.refresh(new_complaint)
        return new_complaint
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create complaint record in DB: {e}")
        raise HTTPException(status_code=500, detail=f"Database commit error: {str(e)}")

@router.get("", response_model=ComplaintListResponse)
def list_complaints(
    search: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    List all stored complaints with search & severity filters.
    """
    query = db.query(Complaint)

    if severity and severity.upper() != "ALL":
        query = query.filter(Complaint.severity_level.ilike(severity))

    if search:
        s = f"%{search}%"
        query = query.filter(
            (Complaint.product_name.ilike(s)) |
            (Complaint.batch_lot_number.ilike(s)) |
            (Complaint.customer_name.ilike(s)) |
            (Complaint.complaint_number.ilike(s)) |
            (Complaint.complaint_description.ilike(s))
        )

    total = query.count()
    items = query.order_by(Complaint.created_at.desc()).offset(offset).limit(limit).all()

    return {"items": items, "total": total}

@router.get("/{complaint_id}", response_model=ComplaintResponseSchema)
def get_complaint_by_id(
    complaint_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve single complaint details by UUID or Complaint Number.
    """
    cmp_rec = db.query(Complaint).filter(
        (Complaint.id == complaint_id) | (Complaint.complaint_number == complaint_id)
    ).first()

    if not cmp_rec:
        raise HTTPException(status_code=404, detail="Complaint record not found.")

    return cmp_rec
