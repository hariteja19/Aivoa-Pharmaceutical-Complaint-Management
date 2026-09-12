from typing import Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai_analysis import CAPAResult
from app.workflow.prompts import CAPA_SYSTEM_PROMPT

def get_llm():
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.2
        )
    return None

def fallback_capa_recommendations(fields: Dict[str, Any], risk: Dict[str, Any]) -> List[str]:
    severity = risk.get("severity_level", "Low")
    batch = fields.get("batch_lot_number", "Unknown Batch")
    
    if severity in ["Critical", "Major"]:
        return [
            f"[Immediate Corrective Action] Place remaining warehouse stock for batch '{batch}' on Quality Hold/Quarantine pending investigation.",
            "[Immediate Corrective Action] Issue Quality Alert to distribution channels and evaluate field health hazards.",
            f"[Immediate Corrective Action] Retrieve and visually inspect retained retention samples for batch '{batch}'.",
            "[Preventive Action] Perform full batch production record audit and review equipment logbooks for anomalies.",
            "[Preventive Action] Re-verify online sensor calibration and update operator In-Process Control (IPC) checklist SOP."
        ]
    else:
        return [
            f"[Immediate Corrective Action] Inspect retention samples for batch '{batch}' to evaluate product baseline quality.",
            "[Corrective Action] Review packaging line logbooks and in-process inspection records for batch integrity.",
            "[Preventive Action] Verify vision inspection system parameters and packaging illumination standards.",
            "[Preventive Action] Reinforce visual inspection SOPs and packaging line clearance procedures with operators."
        ]

def capa_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph CAPA Recommendations Node...")
    fields = state.get("extracted_fields", {})
    risk = state.get("risk_assessment", {})
    
    llm = get_llm()
    recs = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(CAPAResult)
            prompt_input = f"""
Product: {fields.get('product_name')}
Batch: {fields.get('batch_lot_number')}
Severity: {risk.get('severity_level')}
Complaint Type: {fields.get('complaint_type')}
Description: {fields.get('complaint_description')}
"""
            response = structured_llm.invoke([
                SystemMessage(content=CAPA_SYSTEM_PROMPT),
                HumanMessage(content=prompt_input)
            ])
            if response and response.recommendations:
                recs = response.recommendations
        except Exception as e:
            logger.error(f"LLM CAPA node error: {e}. Using fallback GxP actions.")

    if not recs:
        recs = fallback_capa_recommendations(fields, risk)

    return {"capa_recommendations": recs}
