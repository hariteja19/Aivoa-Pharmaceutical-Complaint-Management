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
    mat_type = str(fields.get("material_type", "")).lower()
    combined_text = f"{product} {comp_type} {desc} {mat_type}".lower()

    # Route of administration / sterile formulation check:
    is_sterile_parenteral = bool(re.search(
        r'inject|injection|infusion|vial|ampoule|ampul|parenteral|sterile|ophthalmic|intravenous|iv|syringe|im|subcutaneous',
        combined_text
    ))

    # Check for negated adverse events or interception before administration
    has_negated_adverse = bool(
        re.search(r'\bno\b[^\.\n;]{0,60}\b(?:adverse|harm|injury|health impact|patient impact|illness|reaction)\b', desc, re.IGNORECASE) or
        re.search(r'\bwithout\b[^\.\n;]{0,60}\b(?:adverse|harm|injury|health impact|illness|reaction)\b', desc, re.IGNORECASE) or
        re.search(r'\bdenies\b[^\.\n;]{0,60}\b(?:adverse|harm|injury|health impact|illness)\b', desc, re.IGNORECASE) or
        re.search(r'\bnot\s+(?:associated with|linked to|causing|resulting in)\b[^\.\n;]{0,40}\b(?:adverse|harm|injury)\b', desc, re.IGNORECASE) or
        re.search(r'\bidentified\s+before\s+(?:patient\s+)?(?:administration|use|consumption)\b', desc, re.IGNORECASE) or
        re.search(r'\bintercepted\s+before\s+(?:patient\s+)?(?:administration|use|consumption)\b', desc, re.IGNORECASE) or
        re.search(r'\bquarantined\s+before\s+(?:patient\s+)?(?:administration|use|consumption)\b', desc, re.IGNORECASE) or
        re.search(r'\bsegregated\s+before\s+(?:patient\s+)?(?:administration|use|consumption)\b', desc, re.IGNORECASE) or
        re.search(r'\bheld\s+pending\s+quality\s+review\b', desc, re.IGNORECASE) or
        re.search(r'\bno\s+(?:patient\s+)?(?:impact|injury|complaint|harm)\b', desc, re.IGNORECASE)
    )

    # 1. CRITICAL SEVERITY:
    # A. Active adverse patient harm, toxicity, death, anaphylaxis (when not explicitly negated)
    has_active_harm = bool(
        re.search(r'\b(?:death|fatal|anaphylaxis|poisoned?|toxicity|toxic\s+reaction|hospitalized|cardiac\s+arrest|respiratory\s+depression|overdose)\b', combined_text) or
        (re.search(r'\badverse\s+(?:event|reaction|effect)|patient\s+(?:injury|harm|illness)\b', combined_text) and not has_negated_adverse)
    )

    # B. Dangerous contamination in sterile / parenteral / ophthalmic products (Class I recall hazard)
    has_sterile_contamination = is_sterile_parenteral and bool(
        re.search(r'glass|particulate|particles?|foreign\s+matter|foreign\s+body|microbial|fungal|bacterial|endotoxin|unsterile|turbidity|cloudy|precipitate|sediment', combined_text)
    )

    # C. Severe high-potency drug mix-up that was not intercepted
    has_high_potency_mixup_active = bool(re.search(r'methotrexate|chemotherapy|heparin|epinephrine|insulin|fentanyl|digoxin', product)) and bool(
        re.search(r'mix-?up|wrong\s+(?:product|drug|vial|ampoule|strength|potency|label)|incorrect\s+(?:product|drug|strength|label)', combined_text)
    ) and not has_negated_adverse

    if has_active_harm or has_sterile_contamination or has_high_potency_mixup_active:
        rationale_parts = []
        if has_active_harm:
            rationale_parts.append("reported adverse patient impact or life-threatening safety risk")
        if has_sterile_contamination:
            rationale_parts.append("critical foreign particulate or sterility hazard in sterile parenteral formulation")
        if has_high_potency_mixup_active:
            rationale_parts.append("high-potency drug product substitution/mix-up risk")
        rationale_str = f"Initial AI Risk Assessment: Critical severity assigned due to {'; '.join(rationale_parts)} under FDA 21 CFR Part 211 / GxP regulatory guidelines."
        return {
            "severity_level": "Critical",
            "priority": "Urgent",
            "patient_risk_flag": True,
            "ai_risk_classification": "Critical Patient Safety / Regulatory Risk",
            "rationale": rationale_str
        }

    # 2. MAJOR SEVERITY:
    # A. Strength / Potency Mismatch, Assay Failure, OOS
    has_strength_potency_issue = bool(
        re.search(r'wrong\s+(?:product|drug|strength|dose|dosage|potency|vial|ampoule|tablets?)|incorrect\s+(?:product|drug|strength|dose|dosage|potency|vial|ampoule)|different\s+(?:product|drug|strength)|strength\s+(?:mismatch|error|discrepancy|confusion)|potency\s+(?:failure|loss|drop|low|high|oos)|sub-?poten|super-?poten|out\s+of\s+spec|oos|assay\s+failure|dissolution\s+failure|under-?poten|degradation', combined_text) or
        re.search(r'labeled\s+(?:as\s+)?\S+.*?\bcontained\s+\S+', combined_text)
    )

    # B. Labeling Defect, Mislabeling, Product Mix-up (intercepted or non-fatal)
    has_labeling_mixup_issue = bool(
        re.search(r'mix-?up|product\s+mix|wrong\s+(?:product|drug|label|carton|packaging)|incorrect\s+(?:label|carton|packaging)|label(?:ing)?\s+(?:defect|error|issue|discrepancy|problem|mix-?up|confusion)|mislabel(?:ed|ing)?|missing\s+label|illegible\s+label|obscured\s+label', combined_text)
    )

    # C. Container Closure Integrity & Packaging Breaches (Leakage, Broken Seal, Cracking)
    has_packaging_integrity_issue = bool(
        re.search(r'leak|leaking|leakage|broken\s+seal|compromised\s+seal|seal\s+integrity|tamper\s+evident|cracked\s+(?:vial|bottle|ampoule)|fractured|punctured|container\s+breach|closure\s+defect', combined_text)
    )

    # D. Contamination / Foreign Matter in Non-Injectables or General Formulations
    has_general_contamination = bool(
        re.search(r'contamination|contaminated|foreign\s+matter|foreign\s+particle|foreign\s+object|mold|fungus|precipitate|sediment', combined_text)
    )

    # E. Temperature Excursion / Cold Chain Breach
    has_temp_excursion = bool(
        re.search(r'temperature|storage\s+concern|cold\s+chain', comp_type) or
        re.search(r'(?:temperature|temp|storage|thermal)\b.*?\b(?:excursion|abuse|deviation|spike|failure|breach|out of range|unrefrigerated)', combined_text) or
        re.search(r'cold\s+chain\s+breach|storage\s+range\s+breach|heat\s+exposure|frozen|freeze\s+damage', combined_text)
    )

    # F. Explicit Major classification or high-potency drug product issue
    has_explicit_major = bool("major" in comp_type and "minor" not in comp_type) or bool(
        re.search(r'methotrexate|chemotherapy', product)
    )

    if (has_strength_potency_issue or has_labeling_mixup_issue or has_packaging_integrity_issue or
        has_general_contamination or has_temp_excursion or has_explicit_major):
        reasons = []
        if has_strength_potency_issue:
            reasons.append("strength/potency discrepancy or out-of-specification quality failure")
        if has_labeling_mixup_issue:
            reasons.append("product mix-up or labeling discrepancy")
        if has_packaging_integrity_issue:
            reasons.append("compromised container-closure integrity or leakage")
        if has_general_contamination:
            reasons.append("physical/chemical quality defect or foreign matter concern")
        if has_temp_excursion:
            reasons.append(f"temperature excursion above validated storage limits for '{fields.get('product_name', 'product')}'")
        if not reasons and has_explicit_major:
            reasons.append("significant quality attribute defect")

        return {
            "severity_level": "Major",
            "priority": "High",
            "patient_risk_flag": False,
            "ai_risk_classification": "Major GxP Quality / Efficacy Risk",
            "rationale": f"Initial AI Risk Assessment: Major severity assigned. Significant {'; '.join(reasons)} identified under GxP regulatory standards."
        }

    # 3. LOW SEVERITY:
    # Pure inquiries, samples, general non-defect feedback
    is_low_inquiry = bool(
        re.search(r'\b(?:inquiry|question|general\s+feedback|sample\s+request|packaging\s+inquiry|survey)\b', combined_text) and
        not re.search(r'broken|defect|damage|issue|problem|concern|crack|fail', combined_text)
    )
    if is_low_inquiry:
        return {
            "severity_level": "Low",
            "priority": "Low",
            "patient_risk_flag": False,
            "ai_risk_classification": "Low / Routine Observation",
            "rationale": "Initial AI Risk Assessment: Low severity assigned. Routine customer inquiry or non-defect feedback with zero patient or product risk."
        }

    # 4. MINOR SEVERITY (Default for cosmetic flaws, minor tablet appearance, minor packaging with intact seal/integrity):
    return {
        "severity_level": "Minor",
        "priority": "Low",
        "patient_risk_flag": False,
        "ai_risk_classification": "Minor Quality / Cosmetic Observation",
        "rationale": "Initial AI Risk Assessment: Minor physical or packaging appearance issue reported with verified intact container integrity and minimal risk to patient safety."
    }

def severity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Executing LangGraph Severity Assessment Node...")
    fields = state.get("extracted_fields", {})
    raw_text = state.get("raw_input_text", "")
    
    fields_for_sev = dict(fields)
    if not fields_for_sev.get("complaint_description"):
        fields_for_sev["complaint_description"] = raw_text

    llm = get_llm()
    result = None

    if llm:
        try:
            structured_llm = llm.with_structured_output(SeverityRiskResult)
            prompt_input = f"""
Product Name: {fields_for_sev.get('product_name')}
Product Strength: {fields_for_sev.get('product_strength_grade') or fields_for_sev.get('product_strength')}
Batch: {fields_for_sev.get('batch_lot_number')}
Complaint Type: {fields_for_sev.get('complaint_type')}
Description: {fields_for_sev.get('complaint_description')}
Raw Complaint Context: {raw_text}
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
        result = fallback_severity_rules(fields_for_sev)

    # Sync severity_level and priority into extracted_fields so Redux form fields populate Section 4
    extracted_copy = dict(fields)
    if result.get("severity_level"):
        extracted_copy["severity_level"] = result["severity_level"]
    if result.get("priority"):
        extracted_copy["priority"] = result["priority"]

    return {"risk_assessment": result, "extracted_fields": extracted_copy}
