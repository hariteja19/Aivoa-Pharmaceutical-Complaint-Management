from typing import TypedDict, Optional, List, Dict, Any

class ComplaintGraphState(TypedDict):
    raw_input_text: str
    document_filename: Optional[str]
    db_session: Optional[Any]  # SQLAlchemy session passed dynamically
    
    extracted_fields: Dict[str, Any]
    validation: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    duplicates: Dict[str, Any]
    root_cause_recommendations: List[str]
    capa_recommendations: List[str]
    executive_summary: str
    
    error_logs: List[str]
