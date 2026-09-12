from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai_analysis import ExecutiveSummaryResult
from app.workflow.prompts import SUMMARY_SYSTEM_PROMPT

def get_llm():
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.1
        )
    return None

def fallback_summary(fields: Dict[str, Any], risk: Dict[str, Any]) -> str:
    product = fields.get("product_name") or "Pharmaceutical Product"
    strength = fields.get("product_strength_grade") or ""
    batch = fields.get("batch_lot_number") or "N/A"
    complaint_type = fields.get("complaint_type") or "Quality Defect"
    severity = risk.get("severity_level") or "Low"
    qty = fields.get("affected_quantity") or "unspecified quantity"
    cmp_date = fields.get("complaint_date") or "today"

    return f"A {severity}-severity customer complaint regarding {product} {strength} (Batch: {batch}) was received on {cmp_date} involving {complaint_type} affecting {qty}. Quality Risk Assessment evaluated patient safety risk with a classification of {severity}. Immediate containment actions including retain sample inspection and batch record review have been initiated."

def summary_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Executive Summary Node...")
    fields = state.get("extracted_fields", {})
    risk = state.get("risk_assessment", {})
    
    llm = get_llm()
    summary_text = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(ExecutiveSummaryResult)
            prompt_input = f"""
Product: {fields.get('product_name')} {fields.get('product_strength_grade')}
Batch: {fields.get('batch_lot_number')}
Quantity: {fields.get('affected_quantity')}
Complaint Date: {fields.get('complaint_date')}
Complaint Type: {fields.get('complaint_type')}
Severity Level: {risk.get('severity_level')}
Description: {fields.get('complaint_description')}
"""
            response = structured_llm.invoke([
                SystemMessage(content=SUMMARY_SYSTEM_PROMPT),
                HumanMessage(content=prompt_input)
            ])
            if response and response.summary:
                summary_text = response.summary
        except Exception as e:
            logger.error(f"LLM summary node error: {e}. Using fallback summary generator.")

    if not summary_text:
        summary_text = fallback_summary(fields, risk)

    return {"executive_summary": summary_text}
