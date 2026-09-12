import json
from typing import Optional, Dict, Any, List
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from app.core.config import settings
from app.core.logging import logger
from app.schemas.email import EmailDraftRequest, EmailDraftResponse

EMAIL_SYSTEM_PROMPT = """You are an enterprise Pharmaceutical Quality Assurance (QA) Communications Specialist adhering to FDA 21 CFR Part 211 and ISO 13485 guidelines.
Your role is to draft professional, objective, and regulatory-compliant complaint notification emails to the Quality Assurance / Quality Control team based strictly on the provided complaint data.

CRITICAL ZERO-HALLUCINATION RULES:
1. ONLY use information explicitly provided in the input payload.
2. DO NOT invent recipient email addresses (e.g., do NOT invent qa@pharma.com). The recipient "To" must remain "Quality Assurance Team" unless a recipient is explicitly specified in the data.
3. DO NOT invent missing product names, batch numbers, customer names, sites, dates, or injury reports. If a field is null, empty, or missing, simply omit it.
4. AI RECOMMENDATION FRAMING: Never state an AI recommendation as an established fact or confirmed root cause.
   - WRONG: "The root cause is temperature excursion."
   - CORRECT: "The AI assessment recommends investigating reported temperature excursion as a potential contributing factor."
   - State CAPA recommendations as proposed action items for the quality unit's review.
5. Output format must be strictly valid JSON with keys: "to", "subject", "body".
"""

class EmailGeneratorService:
    @staticmethod
    def _generate_fallback_draft(req: EmailDraftRequest) -> EmailDraftResponse:
        """
        Deterministic, zero-hallucination email generation engine.
        Ensures 100% reliable GxP formatting even if LLM is unavailable.
        """
        to_field = "Quality Assurance Team"

        # Build dynamic Subject Line based on available identifiers
        subject_parts = ["Customer Complaint Notification"]
        if req.complaint_number:
            subject_parts.append(f"[{req.complaint_number}]")
        if req.product_name:
            prod_str = req.product_name
            if req.product_strength_grade:
                prod_str += f" ({req.product_strength_grade})"
            subject_parts.append(f"- {prod_str}")
        if req.batch_lot_number:
            subject_parts.append(f"- Batch {req.batch_lot_number}")
        
        subject = " ".join(subject_parts)

        # Build Body Sections
        lines: List[str] = []
        lines.append(f"Dear {to_field},")
        lines.append("")
        
        opening = "A customer complaint has been logged and reviewed in the AIVOA Quality Management System for triage and quality assessment."
        if req.complaint_number:
            opening = f"Customer complaint record {req.complaint_number} has been logged in the AIVOA Quality Management System for triage and quality assessment."
        lines.append(opening)
        lines.append("")

        # 1. Product & Batch Information
        details: List[str] = []
        if req.product_name:
            details.append(f"• Product Name: {req.product_name}")
        if req.product_strength_grade:
            details.append(f"• Strength / Grade: {req.product_strength_grade}")
        if req.batch_lot_number:
            details.append(f"• Batch / Lot Number: {req.batch_lot_number}")
        if req.customer_name:
            details.append(f"• Customer / Facility: {req.customer_name}")
        if req.complaint_source:
            details.append(f"• Complaint Source: {req.complaint_source}")
        if req.complaint_date:
            details.append(f"• Complaint Received Date: {req.complaint_date}")
        if req.affected_quantity:
            details.append(f"• Affected Quantity: {req.affected_quantity}")
        if req.manufacturing_site:
            details.append(f"• Manufacturing Site: {req.manufacturing_site}")
        if req.manufacturing_date:
            details.append(f"• Manufacturing Date: {req.manufacturing_date}")
        if req.expiry_date:
            details.append(f"• Expiry Date: {req.expiry_date}")
        if req.material_type:
            details.append(f"• Material Type: {req.material_type}")
        if req.complaint_type:
            details.append(f"• Defect Classification: {req.complaint_type}")

        if details:
            lines.append("SUMMARY OF COMPLAINT DETAILS:")
            lines.extend(details)
            lines.append("")

        # 2. Complaint Description
        if req.complaint_description:
            lines.append("COMPLAINT NARRATIVE / REPORTED DEFECT:")
            lines.append(req.complaint_description.strip())
            lines.append("")

        # 3. Severity & Safety Risk Findings
        findings: List[str] = []
        if req.severity_level:
            findings.append(f"• Severity Classification: {req.severity_level}")
        if req.priority:
            findings.append(f"• Priority: {req.priority}")
        if req.patient_risk_flag is not None:
            if req.patient_risk_flag:
                findings.append("• Patient Safety Risk: YES — Potential patient safety concern flagged for expedited triage.")
            else:
                findings.append("• Patient Safety Risk: NO — No direct patient injury reported.")
        if req.risk_rationale:
            findings.append(f"• Regulatory Assessment Rationale: {req.risk_rationale}")

        if req.is_possible_duplicate:
            dup_msg = "• Duplicate Complaint Alert: Potential recurring issue detected for this batch."
            if req.duplicate_reasons:
                dup_msg += f" Reasons: {'; '.join(req.duplicate_reasons)}"
            findings.append(dup_msg)

        if findings:
            lines.append("ASSESSMENT & RISK FINDINGS:")
            lines.extend(findings)
            lines.append("")

        # 4. Recommended Actions / Hypotheses (strictly as recommendations)
        recs: List[str] = []
        if req.root_cause_recommendations:
            recs.append("Potential Root Cause Hypotheses (Recommended for Investigation):")
            for rc in req.root_cause_recommendations:
                recs.append(f"  - The AI assessment recommends evaluating: {rc}")
        if req.capa_recommendations:
            recs.append("Proposed CAPA / Containment Actions (For QA Unit Review):")
            for capa in req.capa_recommendations:
                recs.append(f"  - Recommended Action: {capa}")

        if recs:
            lines.append("PRELIMINARY INVESTIGATION & ACTION RECOMMENDATIONS:")
            lines.extend(recs)
            lines.append("")

        lines.append("Please initiate the formal complaint investigation protocol and confirm containment actions as appropriate under SOP guidelines.")
        lines.append("")
        lines.append("Regards,")
        lines.append("AIVOA Pharmaceutical Complaint Management System")

        body = "\n".join(lines)
        return EmailDraftResponse(to=to_field, subject=subject, body=body)

    @classmethod
    def generate_draft(cls, req: EmailDraftRequest) -> EmailDraftResponse:
        """
        Generates a professional complaint notification email.
        Uses Groq LLM if available; gracefully falls back to deterministic zero-hallucination builder.
        """
        if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
            try:
                llm = ChatGroq(
                    groq_api_key=settings.GROQ_API_KEY,
                    model_name=settings.GROQ_MODEL,
                    temperature=0.0
                )
                
                # Filter out null values for LLM clarity
                payload_dict = {k: v for k, v in req.model_dump().items() if v is not None and v != "" and v != []}
                
                user_content = f"""Generate a professional pharmaceutical complaint notification email using strictly the following complaint data:

Complaint Data:
{json.dumps(payload_dict, indent=2)}

Remember:
- "to": Safe default "Quality Assurance Team".
- Never fabricate missing fields or email addresses.
- Present root causes/CAPAs carefully as recommendations for quality investigation.
- Return ONLY JSON with keys: "to", "subject", "body".
"""
                response = llm.invoke([
                    SystemMessage(content=EMAIL_SYSTEM_PROMPT),
                    HumanMessage(content=user_content)
                ])

                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()

                parsed = json.loads(content)
                return EmailDraftResponse(
                    to=parsed.get("to") or "Quality Assurance Team",
                    subject=parsed.get("subject", "Customer Complaint Notification"),
                    body=parsed.get("body", "")
                )
            except Exception as e:
                logger.warning(f"Groq LLM email generation failed, falling back to deterministic builder: {e}")

        # Fallback deterministic generator
        return cls._generate_fallback_draft(req)
