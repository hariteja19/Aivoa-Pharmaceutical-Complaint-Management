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
from app.schemas.copilot import CopilotChatRequest, CopilotChatResponse, ComplaintStructuredFields
from app.workflow.prompts import COPILOT_SYSTEM_PROMPT
from app.workflow.nodes.validation import validation_node
from app.workflow.nodes.severity import severity_node
from app.workflow.nodes.duplicate import duplicate_node
from app.workflow.nodes.root_cause import root_cause_node
from app.workflow.nodes.capa import capa_node
from app.workflow.nodes.summary import summary_node
from app.workflow.nodes.extraction import normalize_date_string, extraction_node, fallback_regex_extraction

router = APIRouter(prefix="/copilot", tags=["Copilot"])

CANONICAL_FIELDS = {
    "complaint_reference": "Complaint Reference",
    "complaint_source": "Complaint Source",
    "customer_name": "Customer Name",
    "product_name": "Product Name",
    "product_strength": "Product Strength / Grade",
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
    "severity": "Initial Severity",
    "priority": "Priority"
}

BATCH_BLACKLIST = {
    "chat", "the chat", "from the chat", "document", "the document",
    "pdf", "file", "uploaded", "form", "the form", "test case", "test case 4",
    "unspecified", "none", "null", "unknown", "left-side", "the left-side",
    "complaint", "record", "identification", "batch identification",
    "product & batch identification", "section", "section 2",
    "had", "was", "were", "have", "has", "with", "from", "that", "this",
    "label", "vial", "vials", "carton", "cartons", "details", "origin", "product", "batch",
    "lot", "number", "name", "date", "site", "strength", "information"
}

def is_valid_batch_code(val: str) -> bool:
    if not val or not isinstance(val, str):
        return False
    clean = val.strip().strip('"\'.,;:#')
    if len(clean) < 3 or len(clean) > 35:
        return False
    words = clean.split()
    if len(words) > 2:
        return False
    if clean.lower() in BATCH_BLACKLIST:
        return False
    for bad_w in ['manufactured', 'expire', 'expires', 'received', 'reported', 'patient', 'hospital', 'tablet', 'tablets', 'vial', 'vials', 'bottle', 'bottles', 'carton', 'cartons']:
        if bad_w in clean.lower():
            return False
    if re.match(r'^(?:section|requested|action|details|information|batch|lot|product|customer)\b', clean, re.IGNORECASE):
        return False
    if not re.search(r'\d', clean):
        if clean.islower():
            return False
        if clean.lower() in {"had", "was", "were", "with", "have", "has", "contains", "label", "vials", "bottles", "cartons", "pharmacy", "hospital"}:
            return False
    return True

UNIVERSAL_FIELD_MAP = {
    # Complaint Reference
    'complaint reference': 'complaint_reference',
    'complaint ref': 'complaint_reference',
    'reference number': 'complaint_reference',
    'reference': 'complaint_reference',
    'ref #': 'complaint_reference',
    'reference #': 'complaint_reference',
    'complaint number': 'complaint_reference',
    'complaint #': 'complaint_reference',

    # Complaint Source
    'complaint source': 'complaint_source',
    'source': 'complaint_source',

    # Customer Name
    'customer / complainant': 'customer_name',
    'customer/complainant': 'customer_name',
    'customer or complainant': 'customer_name',
    'complainant': 'customer_name',
    'complainant name': 'customer_name',
    'customer name': 'customer_name',
    'customer': 'customer_name',
    'client': 'customer_name',
    'reporter': 'customer_name',

    # Product Name
    'product name': 'product_name',
    'product': 'product_name',

    # Product Strength / Grade
    'product strength / grade': 'product_strength',
    'product strength/grade': 'product_strength',
    'product strength': 'product_strength',
    'strength / grade': 'product_strength',
    'strength/grade': 'product_strength',
    'strength': 'product_strength',
    'grade': 'product_strength',

    # Batch / Lot Number
    'batch / lot number': 'batch_lot_number',
    'batch/lot number': 'batch_lot_number',
    'batch / lot': 'batch_lot_number',
    'batch/lot': 'batch_lot_number',
    'batch lot number': 'batch_lot_number',
    'batch lot': 'batch_lot_number',
    'batch number': 'batch_lot_number',
    'lot number': 'batch_lot_number',
    'batch #': 'batch_lot_number',
    'lot #': 'batch_lot_number',
    'batch': 'batch_lot_number',
    'lot': 'batch_lot_number',

    # Quantity Affected
    'quantity affected': 'affected_quantity',
    'affected quantity': 'affected_quantity',
    'quantity': 'affected_quantity',
    'affected qty': 'affected_quantity',
    'qty affected': 'affected_quantity',
    'qty': 'affected_quantity',

    # Manufacturing Date
    'manufacturing date': 'manufacturing_date',
    'mfg date': 'manufacturing_date',
    'manufacture date': 'manufacturing_date',
    'mfg dt': 'manufacturing_date',
    'prod date': 'manufacturing_date',

    # Expiry Date
    'expiry date': 'expiry_date',
    'exp date': 'expiry_date',
    'expiration date': 'expiry_date',
    'exp dt': 'expiry_date',

    # Manufacturing Site
    'manufacturing site': 'manufacturing_site',
    'site': 'manufacturing_site',
    'facility': 'manufacturing_site',
    'plant': 'manufacturing_site',

    # Material Type
    'material type': 'material_type',
    'material': 'material_type',

    # Complaint Type
    'complaint type': 'complaint_type',
    'defect type': 'complaint_type',
    'type': 'complaint_type',

    # Complaint Date
    'complaint date': 'complaint_date',
    'date received': 'complaint_date',
    'received date': 'complaint_date',

    # Complaint Description
    'detailed complaint description': 'complaint_description',
    'complaint description': 'complaint_description',
    'description': 'complaint_description',
    'narrative': 'complaint_description',

    # Severity & Priority
    'initial severity': 'severity_level',
    'severity level': 'severity_level',
    'severity': 'severity_level',
    'priority': 'priority'
}

def clean_extracted_value(val: str) -> str:
    if not val:
        return ""
    val = val.strip()
    val = re.sub(r'^(?:is|=|:|\bto\b|\bshould be\b|\bset to\b|\bas\b)\s*', '', val, flags=re.IGNORECASE).strip()
    val = re.sub(r'(?:[\.\s;,-]+|\s+)SECTION\s*\d+.*$', '', val, flags=re.IGNORECASE).strip()
    val = re.sub(r'(?:[\.\s;,-]+|\s+)REQUESTED\s+ACTION.*$', '', val, flags=re.IGNORECASE).strip()
    val = re.sub(r'(?:[\.\s;,-]+|\s+)ADDITIONAL\s+INFORMATION.*$', '', val, flags=re.IGNORECASE).strip()
    val = val.rstrip('.,;').strip()
    return val

INSTRUCTION_LINE_PATTERNS = [
    r'^(?:please\s+)?(?:keep\s+)?(?:the\s+)?complaint\s+details\s+separate\b',
    r'^(?:please\s+)?(?:fill(?:\s+in)?|populate|update|load|record)\s+(?:the\s+)?(?:complaint\s+)?form\b',
    r'^(?:please\s+)?(?:assess|determine|evaluate)\s+(?:the\s+)?(?:risk|severity|priority)\b',
    r'^(?:do\s+not\s+invent|do\s+not\s+hallucinate)\b',
    r'^(?:requested\s+action|task|instructions?|important)\s*[:\-\.]',
    r'^(?:patient\s+exposure|patient\s+harm|stock\s+status|evidence\s+available)\s*[:\-\.]'
]

def is_instruction_text(text: str) -> bool:
    if not text:
        return False
    t_clean = text.strip().lower()
    for pat in INSTRUCTION_LINE_PATTERNS:
        if re.search(pat, t_clean, re.IGNORECASE):
            return True
    instruction_keywords = {"separate", "details", "risk", "assess", "assessment", "please", "keep", "instruction", "following", "form", "section"}
    words = set(t_clean.split())
    matched_kw = words.intersection(instruction_keywords)
    if len(matched_kw) >= 2 and len(words) > 3:
        return True
    return False

def extract_fields_from_text(text: str) -> Dict[str, str]:
    if not text:
        return {}
    res = {}
    lines = [l.rstrip() for l in text.splitlines()]
    labels_sorted = sorted(UNIVERSAL_FIELD_MAP.keys(), key=len, reverse=True)
    joined_labels = "|".join(re.escape(l) for l in labels_sorted)

    SECTION_HEADER_RE = re.compile(
        r'^(?:#+\s*)?(?:SECTION\s*\d+|REQUESTED\s+ACTION|ADDITIONAL\s+INFORMATION|TASK\b|IMPORTANT\b|INSTRUCTIONS?\b|STEP\s*\d+)',
        re.IGNORECASE
    )

    # PRE-PROCESS: Expand period-separated fields on a single line into virtual newlines.
    # e.g. "Customer: Acme Corp. Product: X. Batch: Y." → three virtual lines.
    # We detect lines where ". <KnownFieldLabel>:" appears and split them.
    expanded_lines = []
    field_labels_re = '|'.join(re.escape(lbl) for lbl in sorted(UNIVERSAL_FIELD_MAP.keys(), key=len, reverse=True))
    period_field_split_re = re.compile(r'\.\s*(?=' + field_labels_re + r'\s*[=:])', re.IGNORECASE)
    for raw_line in lines:
        segments = period_field_split_re.split(raw_line)
        expanded_lines.extend(s.rstrip() for s in segments if s.strip())
    lines = expanded_lines
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if SECTION_HEADER_RE.match(line):
            i += 1
            continue
        if line.isupper() and len(line) > 4 and (' ' in line or '&' in line) and not re.search(r'\d', line) and ':' not in line:
            i += 1
            continue

        if ':' in line or '=' in line:
            sep = ':' if ':' in line else '='
            k_part, v_part = line.split(sep, 1)
            k_clean = k_part.strip().lower()
            if k_clean in UNIVERSAL_FIELD_MAP:
                target_f = UNIVERSAL_FIELD_MAP[k_clean]
                if target_f == 'complaint_description':
                    desc_parts = [v_part.strip()] if v_part.strip() else []
                    i += 1
                    while i < len(lines):
                        cand = lines[i].strip()
                        if SECTION_HEADER_RE.match(cand) or (cand.isupper() and len(cand) > 4 and (' ' in cand or '&' in cand) and not re.search(r'\d', cand)):
                            break
                        if ':' in cand and cand.split(':', 1)[0].strip().lower() in UNIVERSAL_FIELD_MAP:
                            break
                        if is_instruction_text(cand):
                            break
                        if cand:
                            desc_parts.append(cand)
                        i += 1
                    val_desc = ' '.join(desc_parts).strip()
                    if val_desc and target_f not in res:
                        res[target_f] = val_desc
                    continue
                else:
                    v_raw = v_part.strip()
                    # FIX: Period-separated single-line format: "Customer: Acme Corp. Product: X"
                    # Truncate v_raw at '. <KnownLabel>:' so we don't lump following fields into the value.
                    # Build a regex that matches '. <known_field_label>:' case-insensitively.
                    period_sep_m = re.search(
                        r'\.\s*(' + '|'.join(re.escape(lbl) for lbl in UNIVERSAL_FIELD_MAP.keys()) + r')\s*:',
                        v_raw, re.IGNORECASE
                    )
                    if period_sep_m:
                        v_raw = v_raw[:period_sep_m.start()].strip()
                    if not v_raw and i + 1 < len(lines):
                        next_cand = lines[i + 1].strip()
                        if next_cand and not SECTION_HEADER_RE.match(next_cand) and not (':' in next_cand and next_cand.split(':', 1)[0].strip().lower() in UNIVERSAL_FIELD_MAP):
                            v_raw = next_cand
                            i += 1
                    v_clean = clean_extracted_value(v_raw)
                    if v_clean and v_clean.lower() not in ['not provided', 'none', 'null', 'unknown', 'unspecified']:
                        if is_instruction_text(v_clean):
                            pass
                        elif target_f == 'batch_lot_number' and not is_valid_batch_code(v_clean):
                            pass
                        elif target_f == 'manufacturing_site' and (re.fullmatch(r'\d+', v_clean) or len(v_clean) < 3):
                            pass
                        elif target_f == 'complaint_reference' and (len(v_clean.split()) > 4 or any(w in v_clean.lower() for w in ['separate', 'details', 'risk', 'please', 'keep', 'assess'])):
                            pass
                        elif target_f in ['manufacturing_date', 'expiry_date', 'complaint_date']:
                            norm = normalize_date_string(v_clean)
                            res[target_f] = norm if norm else v_clean
                        elif target_f == 'material_type':
                            if v_clean.upper() == 'API':
                                res['material_type'] = 'Active Pharmaceutical Ingredient (API)'
                            else:
                                res['material_type'] = v_clean
                        elif target_f == 'severity_level':
                            res['severity_level'] = v_clean.capitalize()
                            res['severity'] = v_clean.capitalize()
                        elif target_f == 'priority':
                            res['priority'] = v_clean.capitalize()
                        else:
                            if target_f not in res:
                                res[target_f] = v_clean
        i += 1

    # 2. Conversational update pattern matching (e.g. 'Change the batch / lot number to TEST-ABC-123.')
    # Lookahead stops at: next change/set/update/replace verb, OR " and <field_label>" (for chained updates like
    # "Change quantity to 50 vials and complaint type to Packaging Defect")
    conv_pattern = re.compile(
        rf'(?:^|\b)(?:please\s+)?(?:change|set|update|replace)\s+(?:the\s+)?(?P<label>{joined_labels})\s*(?:on\s+the\s+form\s+|in\s+the\s+form\s+|on\s+form\s+|in\s+form\s+|in\s+the\s+record\s+|on\s+the\s+record\s+)?(?:to|as|=|is|should be|with)\s+(?P<val>.+?)(?=\s+and\s+(?:{joined_labels})\s+(?:to|as|=|is\b)|\s+(?:and\s+)?(?:change|set|update|replace)\s+(?:the\s+)?(?:{joined_labels})|$|\n)',
        re.IGNORECASE
    )
    for m in conv_pattern.finditer(text):
        lbl = m.group('label').strip().lower()
        val = clean_extracted_value(m.group('val'))
        target_f = UNIVERSAL_FIELD_MAP.get(lbl)
        if target_f and target_f not in res and val:
            # For fields that don't legitimately contain commas (unlike manufacturing_site),
            # trim the value at ', <field_label> to/as' — this handles chained NL updates like:
            # "Update the reference to CC-QA-2026-0476, manufacturing site to ..."
            COMMA_SENSITIVE_FIELDS = {'complaint_reference', 'customer_name', 'product_name',
                                      'batch_lot_number', 'complaint_type', 'complaint_source',
                                      'product_strength', 'affected_quantity', 'complaint_date',
                                      'manufacturing_date', 'expiry_date', 'material_type', 'priority',
                                      'severity_level'}
            if target_f in COMMA_SENSITIVE_FIELDS and ',' in val:
                comma_field_m = re.search(
                    r',\s*(?:and\s+)?(?:the\s+)?(' + field_labels_re + r')\s+(?:to|as|=|is)\b',
                    val, re.IGNORECASE
                )
                if comma_field_m:
                    val = val[:comma_field_m.start()].strip()
                    val = clean_extracted_value(val)
            if not val:
                continue
            if target_f == 'batch_lot_number' and not is_valid_batch_code(val):
                continue
            if target_f == 'manufacturing_site' and (re.fullmatch(r'\d+', val) or len(val) < 3):
                continue
            if target_f in ['manufacturing_date', 'expiry_date', 'complaint_date']:
                norm = normalize_date_string(val)
                res[target_f] = norm if norm else val
            elif target_f == 'material_type':
                res[target_f] = 'Active Pharmaceutical Ingredient (API)' if val.upper() == 'API' else val
            else:
                res[target_f] = val

    # 2b. Comma-chained field assignment pattern:
    # "field_label to/as value, field_label to/as value, and field_label to/as value"
    # This handles NL multi-field updates like:
    # "Update the reference to CC-QA-2026-0476, manufacturing site to Asterion..., and material type to FPP"
    comma_chain_pattern = re.compile(
        rf'(?:,\s*(?:and\s+)?|^)(?:the\s+)?(?P<label>{joined_labels})\s+(?:to|as|=|is)\s+(?P<val>.+?)(?=,\s*(?:(?:and\s+)?(?:the\s+)?(?:{joined_labels})\s+(?:to|as|=|is))|$|\n)',
        re.IGNORECASE
    )
    for m in comma_chain_pattern.finditer(text):
        lbl = m.group('label').strip().lower()
        val = clean_extracted_value(m.group('val'))
        target_f = UNIVERSAL_FIELD_MAP.get(lbl)
        if target_f and target_f not in res and val:
            if target_f == 'batch_lot_number' and not is_valid_batch_code(val):
                continue
            if target_f == 'manufacturing_site' and (re.fullmatch(r'\d+', val) or len(val) < 3):
                continue
            if target_f in ['manufacturing_date', 'expiry_date', 'complaint_date']:
                norm = normalize_date_string(val)
                res[target_f] = norm if norm else val
            elif target_f == 'material_type':
                res[target_f] = 'Active Pharmaceutical Ingredient (API)' if val.upper() == 'API' else val
            else:
                res[target_f] = val

    # 3. Comma/and-separated inline assignments fallback
    # e.g. 'Fill the complaint form with product name Metformin, batch MET123, customer John, quantity 50 vials'
    # or 'The batch number is CHG 260712A and the affected quantity is 50 kg'
    # Stops at comma, semicolon, newline, OR " and <field_label>"
    if len(res) <= 1:
        inline_pattern = rf'\b(?P<label>{joined_labels})\b\s*(?:is|=|:|\bto\b|\bas\b)?\s+(?P<val>.+?)(?=[,;\n]|\s+and\s+(?:the\s+)?(?:{joined_labels})\b|$)'
        for m in re.finditer(inline_pattern, text, re.IGNORECASE):
            lbl = m.group('label').strip().lower()
            val = clean_extracted_value(m.group('val'))
            target_f = UNIVERSAL_FIELD_MAP.get(lbl)
            if target_f and target_f not in res and val and not is_instruction_text(val):
                if target_f == 'batch_lot_number' and not is_valid_batch_code(val):
                    continue
                if target_f == 'manufacturing_site' and (re.fullmatch(r'\d+', val) or len(val) < 3):
                    continue
                if target_f in ['manufacturing_date', 'expiry_date', 'complaint_date']:
                    norm = normalize_date_string(val)
                    res[target_f] = norm if norm else val
                elif target_f == 'material_type':
                    res[target_f] = 'Active Pharmaceutical Ingredient (API)' if val.upper() == 'API' else val
                else:
                    res[target_f] = val

    # 4. Product name fallback if not found
    if 'product_name' not in res:
        prod_simple = re.search(r'\b(Methotrexate Injection|Methotrexate|Ceftriaxone for Injection|Ceftriaxone|Insulin Glargine Injection|Insulin Glargine|Metformin HCI|Metformin|Amoxicillin Capsules|Amoxicillin|Paracetamol|Ibuprofen|Atorvastatin|Omeprazole|Ciprofloxacin|Lisinopril|Vancomycin|Gentamicin|Meropenem)(?:\s+(?:for\s+Injection|Injection|Capsules|Tablets|Syrup|Solution))?\b', text, re.IGNORECASE)
        if prod_simple:
            res['product_name'] = prod_simple.group(0).strip()

    return res

def extract_labeled_document_fields(text: str) -> Dict[str, Any]:
    """
    Deterministically parses key:value pairs from complaint documents (e.g. Test Case 4).
    Guarantees zero hallucination and does not invent missing fields.
    """
    return extract_fields_from_text(text)

def parse_generic_copilot_updates(
    msg: str,
    current_fields: Dict[str, Any],
    chat_history: List[Any] = None
) -> Tuple[str, Dict[str, Any], List[str], str]:
    """
    Form-aware AI parser supporting all canonical fields.
    Returns: (intent, updates_dict, modified_keys, copilot_reply)
    """
    # 1. Check for Email Generation Intent
    email_patterns = [
        r'\b(?:create|draft|generate|write|prepare|make|compose)\b.*?\b(?:email|gmail|e-mail)\b',
        r'\b(?:email|gmail|e-mail)\b.*?\b(?:draft|notification|summary|to qa|quality team|complaint)\b',
        r'\bregenerate\s+(?:the\s+)?email\b',
        r'\bcreate\s+(?:a\s+)?gmail\b',
        r'\bdraft\s+(?:an\s+)?email\b',
        r'\bgenerate\s+(?:an\s+)?email\b'
    ]
    if any(re.search(pat, msg, re.IGNORECASE) for pat in email_patterns):
        return (
            "generate_email",
            {},
            [],
            "I generated a complaint notification email using the current complaint details."
        )

    # 2. Universal field extraction from user message (supports multi-field, single-field, and conversational)
    updates = extract_fields_from_text(msg)

    # 3. If no key-value pairs matched, check if the user message is a free-form complaint narrative
    if not updates and len(msg.strip()) > 20:
        try:
            narrative_res = extraction_node({"raw_input_text": msg}).get("extracted_fields", {})
            # A valid complaint narrative must contain at least one core pharmaceutical attribute
            core_narrative_fields = [
                narrative_res.get("product_name"),
                narrative_res.get("batch_lot_number"),
                narrative_res.get("affected_quantity"),
                narrative_res.get("complaint_type"),
                narrative_res.get("customer_name"),
                narrative_res.get("manufacturing_date"),
                narrative_res.get("complaint_date")
            ]
            has_core_fields = any(v and str(v).strip().lower() not in ["none", "null", "not provided", "unspecified", "unknown"] for v in core_narrative_fields)
            if has_core_fields:
                for k, v in narrative_res.items():
                    if v and str(v).strip() and str(v).strip().lower() not in ["none", "null", "not provided", "unspecified", "unknown"]:
                        if k == "batch_lot_number" and str(v).strip().lower() in BATCH_BLACKLIST:
                            continue
                        updates[k] = str(v).strip()
                        if k in ["product_strength", "product_strength_grade"]:
                            updates["product_strength"] = str(v).strip()
                            updates["product_strength_grade"] = str(v).strip()
                        if k in ["complaint_reference", "complaint_number"]:
                            updates["complaint_reference"] = str(v).strip()
                            updates["complaint_number"] = str(v).strip()
                        if k in ["severity_level", "severity"]:
                            updates["severity_level"] = str(v).strip().capitalize()
                            updates["severity"] = str(v).strip().capitalize()
        except Exception as e:
            logger.warning(f"Narrative extraction error: {e}")

    # 4. Check for Full Form Population Intent (only if no specific field updates were found above)
    if not updates:
        populate_doc_patterns = [
            r'\b(?:populate|fill(?:\s+in)?|load|transfer|apply)\b.*?\b(?:complaint\s+)?(?:form|fields?|record)\b',
            r'\b(?:use|from)\b.*?\b(?:uploaded|document|pdf|file|complaint)\b.*?\b(?:form|populate|fill|update)\b',
            r'\bextract\s+all\s+(?:complaint\s+)?details\b',
            r'\buse\s+(?:the\s+)?uploaded\s+complaint\b',
            r'^\s*(?:please\s+)?(?:update|fill|populate)\s+(?:the\s+)?(?:complaint\s+)?form\s*$',
            r'\b(?:update|fill|populate)\s+(?:the\s+)?(?:complaint\s+)?form\b'
        ]
        if any(re.search(pat, msg, re.IGNORECASE) for pat in populate_doc_patterns):
            return ("populate_form", {}, [], "Populate full form intent detected.")

    modified_keys = list(updates.keys())

    # 5. Ambiguity Resolution (e.g. "Change it to 50 kg")
    if not modified_keys:
        m_it = re.search(r'(?:change it to|set it to|update it to|it is)\s*(.+)', msg, re.IGNORECASE)
        if m_it:
            val_raw = clean_extracted_value(m_it.group(1))
            if re.search(r'\d+\s*(?:kg|g|mg|lbs|packs|bottles|boxes|units|vials)', val_raw, re.IGNORECASE):
                updates["affected_quantity"] = val_raw
                modified_keys.append("affected_quantity")
            elif "site" in str(chat_history).lower() or "facility" in str(chat_history).lower():
                updates["manufacturing_site"] = val_raw
                modified_keys.append("manufacturing_site")
            else:
                return "clarification_needed", {}, [], "Which field would you like me to update?"

    if not modified_keys:
        return "general_chat", {}, [], "I received your message. You can instruct me to update any complaint field (e.g. 'The customer is Green Valley Pharmacy', 'Set strength to 250 mg', or 'Manufacturing date is 25 June 2026')."

    # Build structured confirmation message
    confirm_lines = ["I've updated the complaint record:"]
    seen_labels = set()
    for k in modified_keys:
        title = CANONICAL_FIELDS.get(k, k.replace("_", " ").title())
        if title in seen_labels:
            continue
        seen_labels.add(title)
        new_val = updates[k]
        confirm_lines.append(f"• {title} → {new_val}")

    reply = "\n".join(confirm_lines)

    return "update_form_fields", updates, modified_keys, reply

CANONICAL_FIELD_KEYS = [
    "complaint_reference",
    "complaint_source",
    "customer_name",
    "product_name",
    "product_strength",
    "batch_lot_number",
    "affected_quantity",
    "manufacturing_date",
    "expiry_date",
    "manufacturing_site",
    "material_type",
    "complaint_type",
    "complaint_date",
    "complaint_description",
    "severity_level",
    "priority"
]

@router.post("/chat", response_model=CopilotChatResponse)
def copilot_chat_correction(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db)
):
    """
    Copilot natural language interaction endpoint.
    Executes the 5-step pipeline:
    RAW USER MESSAGE -> LLM / Copilot -> RAW LLM RESPONSE -> STRUCTURED OBJECT -> REDUX UPDATE -> REACT FORM
    """
    current_fields = payload.current_fields or {}
    user_msg = payload.user_message.strip()

    if not user_msg:
        raise HTTPException(status_code=400, detail="User message cannot be empty.")

    # =========================================================================
    # STEP 1 & 2: LOG RAW USER INPUT AND CURRENT COMPLAINT BEFORE COPILOT
    # =========================================================================
    logger.info("[COPILOT DEBUG STEP 1 - RAW USER INPUT]\n%s", user_msg)
    logger.info("[COPILOT DEBUG STEP 2 - CURRENT COMPLAINT BEFORE COPILOT]\n%s", json.dumps(current_fields, indent=2))

    # Check for email generation intent
    email_patterns = [
        r'\b(?:create|draft|generate|write|prepare|make|compose)\b.*?\b(?:email|gmail|e-mail)\b',
        r'\b(?:email|gmail|e-mail)\b.*?\b(?:draft|notification|summary|to qa|quality team|complaint)\b',
        r'\bregenerate\s+(?:the\s+)?email\b',
        r'\bcreate\s+(?:a\s+)?gmail\b',
        r'\bdraft\s+(?:an\s+)?email\b',
        r'\bgenerate\s+(?:an\s+)?email\b'
    ]
    if any(re.search(pat, user_msg, re.IGNORECASE) for pat in email_patterns):
        reply = "I generated a complaint notification email using the current complaint details."
        return CopilotChatResponse(
            intent="generate_email",
            updates={},
            structured_fields=None,
            copilot_reply=reply,
            message=reply,
            modified_field_keys=[],
            recalculated_analysis=None
        )

    # Check for full form population request
    populate_doc_patterns = [
        r'\b(?:populate|fill(?:\s+in)?|load|transfer|apply)\b.*?\b(?:complaint\s+)?(?:form|fields?|record)\b',
        r'\b(?:use|from)\b.*?\b(?:uploaded|document|pdf|file|complaint)\b.*?\b(?:form|populate|fill|update)\b',
        r'\bextract\s+all\s+(?:complaint\s+)?details\b',
        r'\buse\s+(?:the\s+)?uploaded\s+complaint\b',
        r'^\s*(?:please\s+)?(?:update|fill|populate)\s+(?:the\s+)?(?:complaint\s+)?form\s*$',
        r'\b(?:update|fill|populate)\s+(?:the\s+)?(?:complaint\s+)?form\b'
    ]
    is_populate_request = any(re.search(pat, user_msg, re.IGNORECASE) for pat in populate_doc_patterns)

    # =========================================================================
    # RAW LLM / PARSER CANDIDATE EXTRACTION
    # =========================================================================
    raw_llm_response_text = None
    llm_candidate_updates = {}

    if settings.GROQ_API_KEY and not settings.GROQ_API_KEY.startswith("gsk_demo"):
        try:
            llm = ChatGroq(groq_api_key=settings.GROQ_API_KEY, model_name=settings.GROQ_MODEL, temperature=0.0)
            llm_prompt = f"""You are AIVOA Copilot for pharmaceutical complaint management.
Extract structured complaint fields from the user request.
Allowed canonical fields:
{CANONICAL_FIELD_KEYS}

RULES:
1. Do NOT create 'complaint_number'.
2. NEVER extract section headers like 'SECTION 2: PRODUCT & BATCH IDENTIFICATION' as batch_lot_number. Only 'Batch / Lot Number: ...' is a batch number.
3. Keep complete product strength (e.g. '50 mg/2 mL', do not truncate to '50 mg').
4. Keep complete material type (e.g. 'Finished Pharmaceutical Product', do not drop 'Product').
5. Strip prompt instructions from complaint_description.

User Message:
{user_msg}

Return ONLY a valid JSON object:
{{
  "intent": "update_form_fields",
  "updates": {{
    "canonical_field": "value"
  }}
}}"""
            llm_res = llm.invoke([SystemMessage(content=COPILOT_SYSTEM_PROMPT), HumanMessage(content=llm_prompt)])
            raw_llm_response_text = llm_res.content.strip()
            if "```json" in raw_llm_response_text:
                raw_llm_response_text = raw_llm_response_text.split("```json")[1].split("```")[0].strip()
            parsed_json = json.loads(raw_llm_response_text)
            llm_candidate_updates = parsed_json.get("updates", {})
        except Exception as e:
            logger.warning(f"Groq LLM invocation bypassed/error: {e}")

    # Deterministic parser extraction (ensures zero hallucination and ground truth preservation)
    deterministic_updates = extract_fields_from_text(user_msg)

    has_prompt_fields = bool(deterministic_updates and any(k != "complaint_description" or v != user_msg for k, v in deterministic_updates.items()))

    # If user message is a free-form complaint narrative or partially extracted:
    is_short_command = bool(re.match(r'^\s*(?:change|set|update|replace)\s+(?:the\s+)?[A-Za-z0-9\s/]+?\s+(?:to|as|=)\s+', user_msg, re.IGNORECASE))
    if not is_populate_request and not is_short_command and (not has_prompt_fields or len(deterministic_updates) <= 2) and len(user_msg.strip()) > 20:
        narrative_res = fallback_regex_extraction(user_msg)
        for k, v in narrative_res.items():
            if v and str(v).strip() and str(v).strip().lower() not in ["none", "null", "not provided", "unspecified", "unknown"]:
                if k == "batch_lot_number" and not is_valid_batch_code(str(v).strip()):
                    continue
                if k not in deterministic_updates or (k == "complaint_description" and deterministic_updates.get(k) == user_msg):
                    deterministic_updates[k] = str(v).strip()
                if k == "product_strength_grade" and "product_strength" not in deterministic_updates:
                    deterministic_updates["product_strength"] = str(v).strip()

    # Re-evaluate has_prompt_fields after narrative check
    has_prompt_fields = bool(deterministic_updates and any(k != "complaint_description" or v != user_msg for k, v in deterministic_updates.items()))

    # If user asks to populate from document/uploaded file or previous history (and prompt did not provide these fields)
    if (is_populate_request or not has_prompt_fields) and (payload.document_text or payload.extracted_fields or payload.chat_history):
        if payload.document_text:
            parsed_doc = extract_fields_from_text(payload.document_text)
            if "complaint_description" not in parsed_doc or not parsed_doc["complaint_description"]:
                try:
                    ext_doc = fallback_regex_extraction(payload.document_text)
                    if ext_doc.get("complaint_description"):
                        parsed_doc["complaint_description"] = ext_doc["complaint_description"]
                except Exception:
                    pass
            for k, v in parsed_doc.items():
                if k not in deterministic_updates or (k == "complaint_description" and deterministic_updates.get(k) == user_msg):
                    deterministic_updates[k] = v
        if payload.extracted_fields:
            for k, v in payload.extracted_fields.items():
                if v and str(v).strip():
                    val_s = str(v).strip()
                    if k not in deterministic_updates or (k == "complaint_description" and deterministic_updates.get(k) == user_msg):
                        deterministic_updates[k] = val_s
                    if k == "product_strength_grade" and "product_strength" not in deterministic_updates:
                        deterministic_updates["product_strength"] = val_s
                    elif k == "product_strength" and "product_strength_grade" not in deterministic_updates:
                        deterministic_updates["product_strength_grade"] = val_s

    # Step 3 Log: Raw LLM or Parser output
    step_2_raw_log = raw_llm_response_text if raw_llm_response_text else json.dumps(deterministic_updates, indent=2)
    logger.info("[COPILOT DEBUG STEP 3 - RAW LLM RESPONSE]\n%s", step_2_raw_log)

    # =========================================================================
    # STEP 4: STRUCTURED OBJECT & VALIDATION
    # =========================================================================
    combined_updates = {}
    if llm_candidate_updates:
        combined_updates.update(llm_candidate_updates)
    if deterministic_updates:
        combined_updates.update(deterministic_updates)

    logger.info("[COPILOT DEBUG STEP 4 - STRUCTURED COPILOT ACTION]\nIntent: update_form_fields | Combined Updates: %s", json.dumps(combined_updates, indent=2))

    # Filter to canonical fields only (STRICTLY NO complaint_number)
    filtered_canonical = {}
    for k in CANONICAL_FIELD_KEYS:
        val = combined_updates.get(k)
        if val is not None:
            val_str = str(val).strip()
            if val_str and val_str.lower() not in ["none", "null", "not provided", "unspecified", "unknown"]:
                filtered_canonical[k] = val_str

    # Date normalization
    for date_field in ["manufacturing_date", "expiry_date", "complaint_date"]:
        if date_field in filtered_canonical:
            norm = normalize_date_string(filtered_canonical[date_field])
            if norm:
                filtered_canonical[date_field] = norm

    # Strict Field-Level Validation Guards:
    if "batch_lot_number" in filtered_canonical:
        if not is_valid_batch_code(filtered_canonical["batch_lot_number"]):
            logger.warning("[VALIDATION REJECT] Invalid batch_lot_number: %s", filtered_canonical["batch_lot_number"])
            del filtered_canonical["batch_lot_number"]

    if "manufacturing_site" in filtered_canonical:
        if re.fullmatch(r'\d+', filtered_canonical["manufacturing_site"]) or len(filtered_canonical["manufacturing_site"]) < 3:
            logger.warning("[VALIDATION REJECT] Invalid manufacturing_site: %s", filtered_canonical["manufacturing_site"])
            del filtered_canonical["manufacturing_site"]

    if "complaint_reference" in filtered_canonical:
        if is_instruction_text(filtered_canonical["complaint_reference"]):
            logger.warning("[VALIDATION REJECT] Invalid complaint_reference: %s", filtered_canonical["complaint_reference"])
            del filtered_canonical["complaint_reference"]

    if "complaint_description" in filtered_canonical:
        desc = filtered_canonical["complaint_description"]
        for marker in ["Please analyze this complaint", "Please do TWO things", "Important:", "Determine the risk level", "SECTION 1:", "Keep the complaint details separate", "Please fill the complaint form", "REQUESTED ACTION:"]:
            if marker in desc:
                if "Complaint Description:" in desc:
                    desc = desc.split("Complaint Description:")[-1].strip()
                else:
                    desc = desc.split(marker)[0].strip()
        filtered_canonical["complaint_description"] = desc.strip()

    # Validate against ComplaintStructuredFields Pydantic schema
    structured_fields_obj = ComplaintStructuredFields(**filtered_canonical)
    validated_payload = structured_fields_obj.model_dump(exclude_none=True)

    if "product_strength" in validated_payload:
        validated_payload["product_strength_grade"] = validated_payload["product_strength"]

    # STEP 5 & 6 Logs: Validated Structured Fields & Final Copilot Update Object
    logger.info("[COPILOT DEBUG STEP 5 - VALIDATED STRUCTURED FIELDS]\n%s", json.dumps(validated_payload, indent=2))
    logger.info("[COPILOT DEBUG STEP 6 - FINAL COPILOT UPDATE OBJECT]\n%s", json.dumps(validated_payload, indent=2))

    if not validated_payload:
        empty_reply = "I received your message. You can instruct me to update any complaint field or upload a complaint document to populate the form."
        return CopilotChatResponse(
            intent="clarification_needed",
            updates={},
            structured_fields=None,
            copilot_reply=empty_reply,
            message=empty_reply,
            modified_field_keys=[],
            recalculated_analysis=None
        )

    # =========================================================================
    # STEP 10 & 11: RISK ASSESSMENT & COMPLETE PIPELINE RECALCULATION
    # =========================================================================
    is_new_complaint = (
        len(validated_payload) >= 4 or
        ("product_name" in validated_payload and "batch_lot_number" in validated_payload) or
        is_populate_request
    )
    if is_new_complaint:
        merged_fields = dict(validated_payload)
    else:
        merged_fields = dict(current_fields)
        merged_fields.update(validated_payload)

    logger.info("[COPILOT DEBUG STEP 10 - RISK-ASSESSMENT INPUT]\n%s", json.dumps(merged_fields, indent=2))

    state_mock = {"extracted_fields": merged_fields, "raw_input_text": merged_fields.get("complaint_description", "")}
    val_res = validation_node(state_mock)["validation"]
    sev_res = severity_node(state_mock)["risk_assessment"]

    # Recalculate root causes, CAPA, executive summary, and duplicate checks for the CURRENT complaint
    rc_res = root_cause_node(state_mock).get("root_cause_recommendations", [])
    capa_res = capa_node({**state_mock, "risk_assessment": sev_res}).get("capa_recommendations", [])
    sum_res = summary_node({**state_mock, "risk_assessment": sev_res}).get("executive_summary", "")
    dup_res = duplicate_node({**state_mock, "db_session": db}).get("duplicates", {})

    logger.info("[COPILOT DEBUG STEP 11 - RISK-ASSESSMENT OUTPUT]\n%s", json.dumps(sev_res, indent=2))

    # Sync severity & priority
    if "severity_level" in validated_payload:
        validated_payload["severity"] = validated_payload["severity_level"]
    elif sev_res.get("severity_level"):
        validated_payload["severity_level"] = sev_res["severity_level"]
        validated_payload["severity"] = sev_res["severity_level"]
    if "priority" not in validated_payload and sev_res.get("priority"):
        validated_payload["priority"] = sev_res["priority"]

    if validated_payload.get("severity_level"):
        structured_fields_obj.severity_level = validated_payload["severity_level"]
    if validated_payload.get("priority"):
        structured_fields_obj.priority = validated_payload["priority"]

    recalculated_analysis = {
        "validation": val_res,
        "risk_assessment": sev_res,
        "root_cause_recommendations": rc_res,
        "capa_recommendations": capa_res,
        "executive_summary": sum_res,
        "duplicates": dup_res
    }

    # Build natural language confirmation strictly from validated fields
    confirm_lines = ["I've updated the complaint record:"]
    for k in CANONICAL_FIELD_KEYS:
        if k in validated_payload:
            title = CANONICAL_FIELDS.get(k, k.replace("_", " ").title())
            confirm_lines.append(f"• {title} → {validated_payload[k]}")
    copilot_reply = "\n".join(confirm_lines)

    return CopilotChatResponse(
        intent="update_form_fields",
        updates=validated_payload,
        structured_fields=structured_fields_obj,
        copilot_reply=copilot_reply,
        message=copilot_reply,
        modified_field_keys=list(validated_payload.keys()),
        recalculated_analysis=recalculated_analysis,
        is_new_complaint=is_new_complaint
    )
