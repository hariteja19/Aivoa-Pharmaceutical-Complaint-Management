from typing import Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai_analysis import RootCauseAnalysisResult
from app.workflow.prompts import ROOT_CAUSE_SYSTEM_PROMPT

def get_llm():
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.2
        )
    return None

def fallback_root_causes(fields: Dict[str, Any]) -> List[str]:
    comp_type = str(fields.get("complaint_type", "")).lower()
    
    if "broken" in comp_type or "damage" in comp_type:
        return [
            "Material (Tableting): Excessive compression force or improper binder ratio during compression batch setup.",
            "Machine (Blister Packaging): Mechanical misalignment or excessive sealing pressure in blister station feeding feeder.",
            "Handling (Logistics): Mechanical impact during secondary packaging or transit vibration.",
            "Method (In-Process Control): Insufficient friability testing frequency during batch manufacturing."
        ]
    elif "seal" in comp_type or "packag" in comp_type:
        return [
            "Machine (Heat Sealer): Temperature fluctuation in heat sealing bar causing defective blister foil seal.",
            "Material (Foil/Film): Out-of-spec lamination thickness or pinhole defects in aluminum foil supply roll.",
            "Method (IPC): Inadequate vacuum leak testing performed on production line samples."
        ]
    elif "color" in comp_type or "appear" in comp_type:
        return [
            "Material (Raw Material): Pigment or dye batch-to-batch variation from raw material supplier.",
            "Milieu (Storage): Humidity or temperature excursion during bulk tablet holding stage.",
            "Machine (Coating Pan): Non-uniform spray distribution during pan coating process."
        ]
    else:
        return [
            "Method (SOP Execution): Deviation from standard operating procedure during batch formulation.",
            "Machine (Equipment Calibration): Minor drift in line sensor or dosage feeder calibration.",
            "Material (Excipient Quality): Sub-standard excipients or raw material variance."
        ]

def root_cause_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Root Cause Analysis Node...")
    fields = state.get("extracted_fields", {})
    
    llm = get_llm()
    recs = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(RootCauseAnalysisResult)
            prompt_input = f"""
Product: {fields.get('product_name')}
Strength: {fields.get('product_strength_grade')}
Complaint Type: {fields.get('complaint_type')}
Description: {fields.get('complaint_description')}
"""
            response = structured_llm.invoke([
                SystemMessage(content=ROOT_CAUSE_SYSTEM_PROMPT),
                HumanMessage(content=prompt_input)
            ])
            if response and response.recommendations:
                recs = response.recommendations
        except Exception as e:
            logger.error(f"LLM root cause node error: {e}. Using domain fallback rules.")

    if not recs:
        recs = fallback_root_causes(fields)

    return {"root_cause_recommendations": recs}
