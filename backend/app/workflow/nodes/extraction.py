import json
import re
from datetime import datetime
from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.ai_analysis import ExtractedComplaintFields
from app.workflow.prompts import EXTRACTION_SYSTEM_PROMPT

def get_llm():
    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        return ChatGroq(
            groq_api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.0
        )
    return None

def normalize_date_string(date_str: str) -> str:
    if not date_str:
        return None
    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return date_str

def fallback_regex_extraction(text: str) -> Dict[str, Any]:
    """
    Fallback deterministic regex extraction if LLM key is absent or offline.
    Extracts strictly present facts with zero hallucinated defaults.
    """
    fields = {
        "complaint_source": None,
        "customer_name": None,
        "product_name": None,
        "product_strength_grade": None,
        "batch_lot_number": None,
        "affected_quantity": None,
        "manufacturing_date": None,
        "expiry_date": None,
        "manufacturing_site": None,
        "material_type": None,
        "complaint_date": None,
        "complaint_type": None,
        "complaint_description": text
    }
    
    # 1. Extract Complaint Source e.g. "Complaint Source: Pharmacist", "Source: Pharmacist"
    src_match = re.search(r'(?:complaint source|source)\s*:?\s*([A-Za-z0-9\s/]+?)(?=\s+(?:customer|product|batch|lot|date|manufacturing|with|had)|$|\n)', text, re.IGNORECASE)
    if src_match:
        val = src_match.group(1).strip()
        if len(val) >= 3 and not val.lower().startswith("that"):
            fields["complaint_source"] = val
    else:
        if re.search(r'\b(?:reported by a pharmacist|contacted by a pharmacist|pharmacist)\b', text, re.IGNORECASE):
            fields["complaint_source"] = "Pharmacist"
        elif re.search(r'\b(?:physician|doctor)\b', text, re.IGNORECASE):
            fields["complaint_source"] = "Physician"
        elif re.search(r'\b(?:hospital|clinic)\b', text, re.IGNORECASE):
            fields["complaint_source"] = "Hospital"
        elif re.search(r'\b(?:distributor)\b', text, re.IGNORECASE):
            fields["complaint_source"] = "Distributor"

    # 2. Extract Customer Name e.g. "Customer: CityCare Community Pharmacy", "Customer: Green Valley Pharmacy"
    cust_match = re.search(r'(?:Customer|Pharmacy|Client)\s*:?\s*([A-Z][A-Za-z0-9\.\s,\'-]+?)(?=\s+(?:reported|product|batch|lot|date|manufacturing|with|had)|$|\n)', text)
    if cust_match:
        val = cust_match.group(1).strip()
        if len(val) > 2 and not val.lower().startswith("that"):
            fields["customer_name"] = val

    # 3. Extract Batch/Lot e.g. "batch MET500-KP4821", "Batch / Lot: INS100-L8834"
    batch_match = re.search(r'(?:batch|lot|batch\s*/\s*lot|lot\s*#|b/n)\s*:?\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
    if batch_match:
        fields["batch_lot_number"] = batch_match.group(1).strip()
        
    # 4. Extract Product Name & Strength
    prod_labeled = re.search(r'product\s*(?:name)?\s*:?\s*([A-Za-z0-9\s]+?)(?=\s+(?:strength|grade|batch|lot|manufacturing|expiry|date)|$|\n)', text, re.IGNORECASE)
    if prod_labeled and len(prod_labeled.group(1).strip()) > 2 and not prod_labeled.group(1).lower().strip().startswith("type"):
        fields["product_name"] = prod_labeled.group(1).strip()
    else:
        prod_simple = re.search(r'\b(Insulin Glargine Injection|Insulin Glargine|Metformin HCI|Metformin|Amoxicillin Capsules|Amoxicillin|Paracetamol|Ibuprofen|Atorvastatin|Omeprazole|Ciprofloxacin|Lisinopril)(?:\s+(?:Injection|Capsules|Tablets|Syrup|Solution))?\b', text, re.IGNORECASE)
        if prod_simple:
            fields["product_name"] = prod_simple.group(0).strip()

    # 5. Extract Strength / Grade if specified separately e.g. "Strength / Grade: 100 units/mL" or "500 mg"
    strength_match = re.search(r'(?:strength\s*/\s*grade|strength|grade)\s*:?\s*(\d+\s*(?:units/mL|units/ml|units per mL|mg/mL|mg/ml|mg|g|ml|mcg|IU/ml|IU)|USP|BP)', text, re.IGNORECASE)
    if strength_match:
        fields["product_strength_grade"] = strength_match.group(1).strip()
    else:
        str_inline = re.search(r'(\d+\s*(?:units/mL|units/ml|units per mL|mg/mL|mg/ml|mcg|IU/ml|IU))', text, re.IGNORECASE)
        if str_inline:
            fields["product_strength_grade"] = str_inline.group(1).strip()

    # 6. Extract Quantity e.g. "15 blister packs", "50 kg", "8 bottles", "4 cartons", "Four cartons"
    qty_word_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
    text_processed_qty = text
    for word, num in qty_word_map.items():
        text_processed_qty = re.sub(rf'\b{word}\b', num, text_processed_qty, flags=re.IGNORECASE)

    qty_match = re.search(r'(\d+\s*(?:cartons|boxes|vials|bottles|blister packs|blisters|packs|tablets|kg|g|units(?!\s*/\s*m[Ll]|\s*per)))', text_processed_qty, re.IGNORECASE)
    if qty_match:
        fields["affected_quantity"] = qty_match.group(1).strip()

    # 7. Extract Dates
    mfg_match = re.search(r'(?:manufactured|manufacturing date|mfg|prod date)\s*(?:on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if mfg_match:
        fields["manufacturing_date"] = normalize_date_string(mfg_match.group(1))

    exp_match = re.search(r'(?:expires|expiry|expiry date|exp)\s*(?:on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if exp_match:
        fields["expiry_date"] = normalize_date_string(exp_match.group(1))

    cmp_date_match = re.search(r'(?:complaint date|received|received on)\s*(?:was received on|on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
    if cmp_date_match:
        fields["complaint_date"] = normalize_date_string(cmp_date_match.group(1))

    # 8. Extract Complaint Type e.g. "Temperature / Storage Concern", "broken tablets", "contamination"
    if re.search(r'temperature|storage|excursion|cold chain|heat', text, re.IGNORECASE):
        fields["complaint_type"] = "Temperature / Storage Concern"
    elif re.search(r'broken|cracked|chipped', text, re.IGNORECASE):
        fields["complaint_type"] = "Broken / Damaged Product"
    elif re.search(r'color|discoloration|stain|appearance', text, re.IGNORECASE):
        fields["complaint_type"] = "Packaging / Product Appearance"
    elif re.search(r'seal|leaking|leak|blister', text, re.IGNORECASE):
        fields["complaint_type"] = "Packaging / Seal Integrity Failure"
    elif re.search(r'contamination|foreign matter|particle', text, re.IGNORECASE):
        fields["complaint_type"] = "Contamination / Foreign Matter"
    elif re.search(r'complaint type\s*:?\s*([A-Za-z0-9\s/]+)', text, re.IGNORECASE):
        fields["complaint_type"] = re.search(r'complaint type\s*:?\s*([A-Za-z0-9\s/]+)', text, re.IGNORECASE).group(1).strip()

    # 9. Extract Material Type if explicitly mentioned
    mat_match = re.search(r'material\s*(?:type)?\s*:?\s*(Finished Product|API|Active Pharmaceutical Ingredient|Excipient|Packaging Material|Raw Material)', text, re.IGNORECASE)
    if mat_match:
        fields["material_type"] = mat_match.group(1).strip()

    # 10. Extract Manufacturing Site if explicitly mentioned
    site_match = re.search(r'(?:manufacturing site|facility|site|plant)\s*:?\s*([A-Za-z0-9\s\-_]+?)(?=\s+(?:material|date|with)|$|\n)', text, re.IGNORECASE)
    if site_match and not site_match.group(1).lower().startswith("date"):
        fields["manufacturing_site"] = site_match.group(1).strip()

    return fields

def extraction_node(state: Dict[str, Any]) -> Dict[str, Any]:
    raw_text = state.get("raw_input_text", "")
    logger.info("Executing LangGraph Extraction Node...")
    
    llm = get_llm()
    extracted = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(ExtractedComplaintFields)
            response = structured_llm.invoke([
                SystemMessage(content=EXTRACTION_SYSTEM_PROMPT),
                HumanMessage(content=f"Extract complaint details from the text below:\n\n{raw_text}")
            ])
            if response:
                extracted = response.model_dump()
        except Exception as e:
            logger.error(f"Groq LLM extraction node error: {e}. Switching to fallback regex extraction.")

    if not extracted:
        extracted = fallback_regex_extraction(raw_text)

    # Clean up empty strings to None and normalize dates
    for k, v in extracted.items():
        if isinstance(v, str) and v.strip() == "":
            extracted[k] = None
        if k in ["manufacturing_date", "expiry_date", "complaint_date"] and v:
            extracted[k] = normalize_date_string(str(v))

    return {"extracted_fields": extracted}

