import re
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai_analysis import SeverityRiskResult
from app.workflow.prompts import SEVERITY_SYSTEM_PROMPT

def get_llm():
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.1
        )
    return None

def fallback_severity_rules(fields: Dict[str, Any]) -> Dict[str, Any]:
    desc = str(fields.get("complaint_description", "")).lower()
    comp_type = str(fields.get("complaint_type", "")).lower()
    product = str(fields.get("product_name", "")).lower()
    
    # 1. Critical keywords: patient harm, hospital, death, contamination, incorrect drug, broken glass
    has_negated_adverse = re.search(r'\bno\s+(?:patient\s+)?(?:adverse|harm|injury)\b', desc, re.IGNORECASE)
    critical_pattern = r'death|fatal|hospital|anaphylaxis|poison|contamination|glass|wrong drug|wrong strength'
    is_critical = re.search(critical_pattern, desc) or re.search(critical_pattern, comp_type)
    if not is_critical and (re.search(r'\badverse\b|\binjury\b|\bharm\b', desc, re.IGNORECASE) or re.search(r'\badverse\b|\binjury\b|\bharm\b', comp_type, re.IGNORECASE)):
        if not has_negated_adverse:
            is_critical = True

    if is_critical:
        return {
            "severity_level": "Critical",
            "priority": "Urgent",
            "patient_risk_flag": True,
            "rationale": "Initial AI Risk Assessment: Critical risk flagged due to potential patient safety impact, adverse event, or severe product contamination under FDA 21 CFR Part 211 guidelines."
        }
        
    # 2. Temperature excursion / Cold chain breach e.g. Insulin / Biologics
    if re.search(r'temperature|excursion|cold chain|storage range|heat', desc) or re.search(r'temperature|storage', comp_type):
        patient_flag = "adverse" in desc or "harm" in desc or "injury" in desc
        return {
            "severity_level": "Major",
            "priority": "High",
            "patient_risk_flag": patient_flag,
            "rationale": f"Initial AI Risk Assessment: Major severity assigned due to temperature excursion above recommended storage range for '{fields.get('product_name', 'product')}'. High priority investigation recommended due to potential potency loss, though affected stock is segregated and no adverse events reported."
        }

    # 3. Major physical/quality defect: broken, sub-potency, seal breach, dissolved, discolored
    major_pattern = r'broken|cracked|sub-potency|seal|dissolution|leak|potency|discolor'
    if re.search(major_pattern, desc) or re.search(major_pattern, comp_type):
        patient_flag = "injury" in desc or "harm" in desc
        return {
            "severity_level": "Major",
            "priority": "High" if patient_flag else "Medium",
            "patient_risk_flag": patient_flag,
            "rationale": "Initial AI Risk Assessment: Major physical integrity or quality attribute failure detected requiring investigation, though no direct patient injury was reported."
        }

    # 4. Minor / Low default
    return {
        "severity_level": "Minor",
        "priority": "Low",
        "patient_risk_flag": False,
        "rationale": "Initial AI Risk Assessment: Minor physical or packaging cosmetic issue reported with minimal risk to patient safety."
    }

def severity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Severity Assessment Node...")
    fields = state.get("extracted_fields", {})
    
    llm = get_llm()
    result = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(SeverityRiskResult)
            prompt_input = f"""
Product Name: {fields.get('product_name')}
Batch: {fields.get('batch_lot_number')}
Complaint Type: {fields.get('complaint_type')}
Description: {fields.get('complaint_description')}
"""
            response = structured_llm.invoke([
                SystemMessage(content=SEVERITY_SYSTEM_PROMPT),
                HumanMessage(content=prompt_input)
            ])
            if response:
                result = response.model_dump()
        except Exception as e:
            logger.error(f"LLM severity node error: {e}. Falling back to rule engine.")

    if not result:
        result = fallback_severity_rules(fields)

    # Sync severity_level and priority into extracted_fields so Redux form fields populate Section 4
    extracted_copy = dict(fields)
    if result.get("severity_level"):
        extracted_copy["severity_level"] = result["severity_level"]
    if result.get("priority"):
        extracted_copy["priority"] = result["priority"]

    return {"risk_assessment": result, "extracted_fields": extracted_copy}
