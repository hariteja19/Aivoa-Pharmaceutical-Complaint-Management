from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.db.models import Complaint
from app.core.logging import logger

class DuplicateCheckerService:
    @staticmethod
    def find_potential_duplicates(
        db: Session,
        product_name: str,
        batch_lot_number: str,
        current_description: str = ""
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Searches PostgreSQL / DB for existing complaints with matching product and batch lot number.
        Returns: (is_duplicate: bool, matching_ids: List[str], reasons: List[str])
        """
        if not product_name or not batch_lot_number:
            return False, [], []

        try:
            # Query DB for identical product & batch
            matches = db.query(Complaint).filter(
                Complaint.product_name.ilike(f"%{product_name.strip()}%"),
                Complaint.batch_lot_number.ilike(f"%{batch_lot_number.strip()}%")
            ).all()

            if not matches:
                return False, [], []

            matching_ids = []
            reasons = []

            for match in matches:
                matching_ids.append(match.id)
                reasons.append(
                    f"Match found: Complaint #{match.complaint_number} shares Product '{match.product_name}' and Batch/Lot '{match.batch_lot_number}' (Logged on {match.complaint_date})"
                )

            return True, matching_ids, reasons
        except Exception as e:
            logger.error(f"Error checking duplicate complaints in DB: {e}")
            return False, [], []
