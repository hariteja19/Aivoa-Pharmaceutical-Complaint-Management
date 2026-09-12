from typing import Dict, Any
from app.core.logging import logger

REQUIRED_PHARMA_FIELDS = [
    "customer_name",
    "product_name",
    "batch_lot_number",
    "affected_quantity",
    "complaint_date",
    "complaint_type",
    "complaint_description"
]

ALL_FIELDS = [
    "complaint_reference",
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength_grade",
    "batch_lot_number",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "manufacturing_site",
    "material_type",
    "complaint_date",
    "complaint_type",
    "complaint_description"
]

def validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Validation Node (Pure Python Rules)...")
    fields = state.get("extracted_fields", {})
    
    missing_fields = []
    filled_count = 0

    for field_key in ALL_FIELDS:
        val = fields.get(field_key)
        if val is not None and str(val).strip() != "":
            filled_count += 1
        else:
            if field_key in REQUIRED_PHARMA_FIELDS:
                # Readable field name formatting
                readable = field_key.replace("_", " ").title()
                missing_fields.append(readable)

    completeness_score = round((filled_count / len(ALL_FIELDS)) * 100.0, 1)
    is_complete = len(missing_fields) == 0

    validation_result = {
        "is_complete": is_complete,
        "missing_fields": missing_fields,
        "completeness_score": completeness_score,
        "filled_count": filled_count,
        "total_fields": len(ALL_FIELDS)
    }

    return {"validation": validation_result}
