from typing import Dict, Any
from app.core.logging import logger
from app.services.duplicate_checker import DuplicateCheckerService

def duplicate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Duplicate Detection Node (PostgreSQL Query)...")
    fields = state.get("extracted_fields", {})
    db = state.get("db_session")

    product_name = fields.get("product_name") or ""
    batch_lot = fields.get("batch_lot_number") or ""
    description = fields.get("complaint_description") or ""

    if not db:
        logger.info("No DB session in graph state. Skipping duplicate check.")
        return {
            "duplicates": {
                "is_possible_duplicate": False,
                "matching_complaint_ids": [],
                "match_reasons": []
            }
        }

    is_dup, match_ids, reasons = DuplicateCheckerService.find_potential_duplicates(
        db=db,
        product_name=product_name,
        batch_lot_number=batch_lot,
        current_description=description
    )

    duplicate_result = {
        "is_possible_duplicate": is_dup,
        "matching_complaint_ids": match_ids,
        "match_reasons": reasons
    }

    return {"duplicates": duplicate_result}
