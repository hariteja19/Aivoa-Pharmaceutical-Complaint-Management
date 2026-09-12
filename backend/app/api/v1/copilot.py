import re
import json
from datetime import datetime
from typing import Dict, Any, List, Tuple
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_db
from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse
from app.workflow.prompts import COPILOT_SYSTEM_PROMPT
from app.workflow.nodes.validation import validation_node
from app.workflow.nodes.severity import severity_node
from app.workflow.nodes.extraction import normalize_date_string

router = APIRouter(prefix="/copilot", tags=["Copilot"])

CANONICAL_FIELDS = {
    "complaint_source": "Complaint Source",
    "customer_name": "Customer Name",
    "product_name": "Product Name",
    "product_strength_grade": "Product Strength / Grade",
    "batch_lot_number": "Batch / Lot Number",
    "affected_quantity": "Quantity Affected",
    "manufacturing_date": "Manufacturing Date",
    "expiry_date": "Expiry Date",
    "manufacturing_site": "Manufacturing Site",
    "material_type": "Material Type",
    "complaint_date": "Complaint Date",
    "complaint_type": "Complaint Type",
    "complaint_description": "Detailed Complaint Description",
    "severity_level": "Initial Severity",
    "priority": "Priority"
}

def clean_extracted_value(val: str) -> str:
    if not val:
        return ""
    val = val.strip()
    # Remove leading colons, equals, 'is', 'to'
    val = re.sub(r'^(?:is|=|:|\bto\b|\bshould be\b|\bset to\b)\s*', '', val, flags=re.IGNORECASE).strip()
    # Strip trailing punctuation
    val = val.rstrip('.').strip()
    return val

def parse_generic_copilot_updates(
    msg: str,
    current_fields: Dict[str, Any],
    chat_history: List[Any] = None
) -> Tuple[str, Dict[str, Any], List[str], str]:
    """
    Form-aware AI parser supporting all 13 canonical fields.
    Returns: (intent, updates_dict, modified_keys, copilot_reply)
    """
    updates = {}
    modified_keys = []
    
    # 1. Customer Name
    m_cust = re.search(r'(?:customer name|change customer name to|set customer name to|set customer to|customer is|customer)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\.\s,\'-]+?)(?=\s+(?:and|with|set|change|batch|quantity|expiry|product)|$|\.)', msg, re.IGNORECASE)
    if m_cust:
        val = clean_extracted_value(m_cust.group(1))
        if len(val) >= 2 and not val.lower().startswith("is"):
            updates["customer_name"] = val
            modified_keys.append("customer_name")

    # 2. Product Name
    m_prod = re.search(r'(?:product name|change product name to|the product is|set product name to|set product to|product)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\s]+?)(?=\s+(?:and|with|set|change|batch|quantity|strength|expiry)|$|\.)', msg, re.IGNORECASE)
    if m_prod and not m_prod.group(1).lower().strip() in ["number", "date", "site", "type", "description", "source", "name"]:
        val = clean_extracted_value(m_prod.group(1))
        if len(val) >= 2:
            updates["product_name"] = val
            modified_keys.append("product_name")

    # 3. Product Strength / Grade
    m_str = re.search(r'(?:product strength|strength|grade|set strength to|strength is)\s*(?:is|=|:|\bto\b)?\s*(\d+\s*(?:units/mL|units/ml|units per mL|mg/mL|mg/ml|mg|g|ml|mcg|IU/ml|IU)|USP|BP|[A-Za-z0-9\s/]+?)(?=\s+(?:and|with|set|change|batch|quantity)|$|\.)', msg, re.IGNORECASE)
    if m_str:
        val = clean_extracted_value(m_str.group(1))
        if val:
            updates["product_strength_grade"] = val
            modified_keys.append("product_strength_grade")

    # 4. Batch / Lot Number
    m_batch = re.search(r'(?:batch number|batch lot number|batch|lot number|lot|change batch number to|batch is)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\-_]+(?:\s+[A-Za-z0-9\-_]+)?)(?=\s+(?:and|with|affected|quantity|for|expiry|mfg|site)|$|\.)', msg, re.IGNORECASE)
    if m_batch:
        val = clean_extracted_value(m_batch.group(1))
        if val:
            updates["batch_lot_number"] = val
            modified_keys.append("batch_lot_number")

    # 5. Affected Quantity
    m_qty = re.search(r'(?:affected quantity|quantity|qty|change affected quantity to)\s*(?:is|=|:|\bto\b)?\s*(\d+\s*(?:kg|g|mg|lbs|packs|blister packs|boxes|units|tablets|bottles))', msg, re.IGNORECASE)
    if m_qty:
        val = clean_extracted_value(m_qty.group(1))
        if val:
            updates["affected_quantity"] = val
            modified_keys.append("affected_quantity")

    # 6. Manufacturing Date
    m_mfg = re.search(r'(?:manufacturing date|mfg date|prod date|manufactured date)\s*(?:should be|is|=|:|\bto\b)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', msg, re.IGNORECASE)
    if m_mfg:
        val = normalize_date_string(clean_extracted_value(m_mfg.group(1)))
        if val:
            updates["manufacturing_date"] = val
            modified_keys.append("manufacturing_date")

    # 7. Expiry Date
    m_exp = re.search(r'(?:expiry date|expiration date|exp date|expires|expires on)\s*(?:should be|is|=|:|\bto\b)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', msg, re.IGNORECASE)
    if m_exp:
        val = normalize_date_string(clean_extracted_value(m_exp.group(1)))
        if val:
            updates["expiry_date"] = val
            modified_keys.append("expiry_date")

    # 8. Manufacturing Site
    m_site = re.search(r'(?:manufacturing site|site|facility|plant|set manufacturing site to)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\s\-_]+?)(?=\s+(?:and|with|batch|date)|$|\.)', msg, re.IGNORECASE)
    if m_site and not m_site.group(1).lower().strip().startswith("date"):
        val = clean_extracted_value(m_site.group(1))
        if len(val) >= 2:
            updates["manufacturing_site"] = val
            modified_keys.append("manufacturing_site")

    # 9. Material Type
    m_mat = re.search(r'(?:material type|material)\s*(?:is|=|:|\bto\b)?\s*(Finished Product|Active Pharmaceutical Ingredient|API|Excipient|Packaging Material|Raw Material|Clinical Trial Supply)', msg, re.IGNORECASE)
    if m_mat:
        val = clean_extracted_value(m_mat.group(1))
        if val.upper() == "API":
            val = "Active Pharmaceutical Ingredient (API)"
        updates["material_type"] = val
        modified_keys.append("material_type")

    # 10. Complaint Date
    m_cdate = re.search(r'(?:complaint date|received date|date received)\s*(?:is|=|:|\bto\b)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', msg, re.IGNORECASE)
    if m_cdate:
        val = normalize_date_string(clean_extracted_value(m_cdate.group(1)))
        if val:
            updates["complaint_date"] = val
            modified_keys.append("complaint_date")

    # 11. Complaint Type
    m_ctype = re.search(r'(?:complaint type|defect type|change complaint type to)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\s/]+?)(?=\s+(?:and|with|for)|$|\.)', msg, re.IGNORECASE)
    if m_ctype:
        val = clean_extracted_value(m_ctype.group(1))
        if len(val) >= 3:
            updates["complaint_type"] = val
            modified_keys.append("complaint_type")

    # 12. Complaint Description
    m_desc = re.search(r'(?:complaint description|update complaint description to|update description to|description is)\s*(?:is|=|:|\bto\b)?\s*(.+)', msg, re.IGNORECASE)
    if m_desc and not any(k in msg.lower() for k in ["batch", "customer", "product name", "quantity"]):
        val = clean_extracted_value(m_desc.group(1))
        if len(val) >= 4:
            updates["complaint_description"] = val
            modified_keys.append("complaint_description")

    # 13. Complaint Source
    m_src = re.search(r'(?:complaint source|change complaint source to|set complaint source to|source)\s*(?:is|=|:|\bto\b)?\s*([A-Za-z0-9\s/]+?)(?=\s+(?:and|with)|$|\.)', msg, re.IGNORECASE)
    if m_src and not any(k in msg.lower() for k in ["batch", "date", "description", "type"]):
        val = clean_extracted_value(m_src.group(1))
        if len(val) >= 3:
            updates["complaint_source"] = val
            modified_keys.append("complaint_source")

    # 14. Initial Severity
    m_sev = re.search(r'(?:initial severity|severity level|severity)\s*(?:is|=|:|\bto\b)?\s*(Critical|Major|Minor|Low)', msg, re.IGNORECASE)
    if m_sev:
        val = clean_extracted_value(m_sev.group(1)).capitalize()
        updates["severity_level"] = val
        modified_keys.append("severity_level")

    # 15. Priority
    m_prio = re.search(r'(?:priority)\s*(?:is|=|:|\bto\b)?\s*(Urgent|High|Medium|Low)', msg, re.IGNORECASE)
    if m_prio:
        val = clean_extracted_value(m_prio.group(1)).capitalize()
        updates["priority"] = val
        modified_keys.append("priority")

    # 14. Ambiguity Resolution (Requirement 5)
    # e.g. "Change it to 50 kg" or "Actually change it to Facility Alpha"
    m_it = re.search(r'(?:change it to|set it to|update it to|it is)\s*(.+)', msg, re.IGNORECASE)
    if m_it and not modified_keys:
        val_raw = clean_extracted_value(m_it.group(1))
        # If value has units e.g. "50 kg" -> resolve to affected_quantity
        if re.search(r'\d+\s*(?:kg|g|mg|lbs|packs|bottles|boxes|units)', val_raw, re.IGNORECASE):
            updates["affected_quantity"] = val_raw
            modified_keys.append("affected_quantity")
        elif "site" in str(chat_history).lower() or "facility" in str(chat_history).lower():
            updates["manufacturing_site"] = val_raw
            modified_keys.append("manufacturing_site")
        else:
            return "clarification_needed", {}, [], "Which field would you like me to update?"

    if not modified_keys:
        return "general_chat", {}, [], "I received your message. You can instruct me to update any complaint field (e.g. 'The customer is Green Valley Pharmacy', 'Set strength to 250 mg', or 'Manufacturing date is 25 June 2026')."

    # Build explicit structured confirmation message (Requirement 11)
    confirm_lines = ["I've updated the complaint record:"]
    for k in modified_keys:
        title = CANONICAL_FIELDS.get(k, k.replace("_", " ").title())
        new_val = updates[k]
        confirm_lines.append(f"• {title} → {new_val}")

    reply = "\n".join(confirm_lines)

    return "update_form_fields", updates, modified_keys, reply

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat_correction(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db)
):
    """
    Copilot natural language interaction endpoint.
    Parses user correction text, updates structured fields, recalculates completeness/severity, and returns updated form state.
    """
    current_fields = payload.current_fields or {}
    user_msg = payload.user_message.strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="User message cannot be empty.")

    intent, updates, modified_keys, copilot_reply = parse_generic_copilot_updates(
        user_msg, current_fields, payload.chat_history
    )

    # Try LLM enhancement if Groq key available
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        try:
            llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL, temperature=0.0)
            prompt = f"""
Current Structured Form Fields:
{json.dumps(current_fields, indent=2)}

Canonical Field Names allowed:
{list(CANONICAL_FIELDS.keys())}

User Correction Request:
"{user_msg}"

Task:
1. Identify if user wants to update any of the 13 canonical fields.
2. Extract the new values. Normalize dates to YYYY-MM-DD format.
3. Return ONLY a JSON object:
{{
  "intent": "update_form_fields",
  "updates": {{
     "field_name": "new_value"
  }},
  "copilot_reply": "I've updated the complaint record:\n• Field Name → new_value"
}}
If ambiguous without context, set intent to "clarification_needed" and copilot_reply to "Which field would you like me to update?".
"""
            llm_res = llm.invoke([SystemMessage(content=COPILOT_SYSTEM_PROMPT), HumanMessage(content=prompt)])
            cleaned_res = llm_res.content.strip()
            if "```json" in cleaned_res:
                cleaned_res = cleaned_res.split("```json")[1].split("```")[0].strip()
            parsed_res = json.loads(cleaned_res)

            llm_updates = parsed_res.get("updates", {})
            if llm_updates:
                intent = parsed_res.get("intent", "update_form_fields")
                for k, v in llm_updates.items():
                    if k in CANONICAL_FIELDS and v is not None:
                        updates[k] = str(v).strip()
                        if k not in modified_keys:
                            modified_keys.append(k)
                if modified_keys:
                    confirm_lines = ["I've updated the complaint record:"]
                    for k in modified_keys:
                        title = CANONICAL_FIELDS.get(k, k)
                        confirm_lines.append(f"• {title} → {updates[k]}")
                    copilot_reply = "\n".join(confirm_lines)
        except Exception as e:
            logger.warning(f"Copilot LLM parsing fallback due to: {e}")

    # Merge updates into current_fields for validation/severity recalculation
    merged_fields = dict(current_fields)
    for k, v in updates.items():
        merged_fields[k] = v

    state_mock = {"extracted_fields": merged_fields, "raw_input_text": merged_fields.get("complaint_description", "")}
    val_res = validation_node(state_mock)["validation"]
    sev_res = severity_node(state_mock)["risk_assessment"]

    recalculated_analysis = {
        "validation": val_res,
        "risk_assessment": sev_res
    }

    return CopilotChatResponse(
        intent=intent,
        updates=updates,
        copilot_reply=copilot_reply,
        modified_field_keys=modified_keys,
        recalculated_analysis=recalculated_analysis
    )
