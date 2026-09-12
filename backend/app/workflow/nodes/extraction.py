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
        "complaint_reference": None,
        "complaint_number": None,
        "complaint_source": None,
        "customer_name": None,
        "product_name": None,
        "product_strength_grade": None,
        "product_strength": None,
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

    # First, extract any explicit labeled key-value lines
    KEY_LINE_MAP = {
        'complaint reference': 'complaint_reference',
        'complaint ref': 'complaint_reference',
        'reference number': 'complaint_reference',
        'reference': 'complaint_reference',
        'ref #': 'complaint_reference',
        'reference #': 'complaint_reference',
        'complaint number': 'complaint_reference',
        'complaint #': 'complaint_reference',
        'complaint no': 'complaint_reference',
        'complaint no.': 'complaint_reference',
        'ref no': 'complaint_reference',
        'ref no.': 'complaint_reference',
        'ref number': 'complaint_reference',
        'case number': 'complaint_reference',
        'case id': 'complaint_reference',
        'report id': 'complaint_reference',
        'incident #': 'complaint_reference',
        'tracking number': 'complaint_reference',
        'complaint source': 'complaint_source',
        'source of complaint': 'complaint_source',
        'source': 'complaint_source',
        'reported by': 'complaint_source',
        'customer name': 'customer_name',
        'customer / complainant': 'customer_name',
        'customer/complainant': 'customer_name',
        'customer': 'customer_name',
        'complainant': 'customer_name',
        'reporting customer': 'customer_name',
        'client': 'customer_name',
        'reporter': 'customer_name',
        'product name': 'product_name',
        'product': 'product_name',
        'drug name': 'product_name',
        'drug': 'product_name',
        'product strength / grade': 'product_strength_grade',
        'product strength/grade': 'product_strength_grade',
        'product strength': 'product_strength_grade',
        'strength / grade': 'product_strength_grade',
        'strength/grade': 'product_strength_grade',
        'strength': 'product_strength_grade',
        'grade': 'product_strength_grade',
        'dosage': 'product_strength_grade',
        'dose': 'product_strength_grade',
        'concentration': 'product_strength_grade',
        'potency': 'product_strength_grade',
        'batch / lot number': 'batch_lot_number',
        'batch/lot number': 'batch_lot_number',
        'batch lot number': 'batch_lot_number',
        'batch / lot': 'batch_lot_number',
        'batch/lot': 'batch_lot_number',
        'batch lot': 'batch_lot_number',
        'batch number': 'batch_lot_number',
        'lot number': 'batch_lot_number',
        'batch #': 'batch_lot_number',
        'lot #': 'batch_lot_number',
        'batch no': 'batch_lot_number',
        'batch no.': 'batch_lot_number',
        'lot no': 'batch_lot_number',
        'lot no.': 'batch_lot_number',
        'batch': 'batch_lot_number',
        'lot': 'batch_lot_number',
        'manufacturing date': 'manufacturing_date',
        'date of manufacture': 'manufacturing_date',
        'date of manufacturing': 'manufacturing_date',
        'mfg date': 'manufacturing_date',
        'manufacture date': 'manufacturing_date',
        'mfg dt': 'manufacturing_date',
        'mfg. date': 'manufacturing_date',
        'prod date': 'manufacturing_date',
        'production date': 'manufacturing_date',
        'expiry date': 'expiry_date',
        'date of expiry': 'expiry_date',
        'exp date': 'expiry_date',
        'exp. date': 'expiry_date',
        'expiration date': 'expiry_date',
        'exp dt': 'expiry_date',
        'use before': 'expiry_date',
        'shelf life date': 'expiry_date',
        'manufacturing site': 'manufacturing_site',
        'manufacturing facility': 'manufacturing_site',
        'manufacturing / packaging site': 'manufacturing_site',
        'manufacturing/packaging site': 'manufacturing_site',
        'production site': 'manufacturing_site',
        'production facility': 'manufacturing_site',
        'manufacturing plant': 'manufacturing_site',
        'site': 'manufacturing_site',
        'facility': 'manufacturing_site',
        'plant': 'manufacturing_site',
        'material type': 'material_type',
        'material / product type': 'material_type',
        'material/product type': 'material_type',
        'dosage form / material type': 'material_type',
        'dosage form': 'material_type',
        'material': 'material_type',
        'complaint date': 'complaint_date',
        'date of complaint': 'complaint_date',
        'complaint received date': 'complaint_date',
        'date received': 'complaint_date',
        'received date': 'complaint_date',
        'receipt date': 'complaint_date',
        'intake date': 'complaint_date',
        'report date': 'complaint_date',
        'date reported': 'complaint_date',
        'complaint type': 'complaint_type',
        'complaint category': 'complaint_type',
        'defect type': 'complaint_type',
        'defect category': 'complaint_type',
        'incident type': 'complaint_type',
        'nature of complaint': 'complaint_type',
        'nature of defect': 'complaint_type',
        'classification of defect': 'complaint_type',
        'type': 'complaint_type',
        'category': 'complaint_type',
        'affected quantity': 'affected_quantity',
        'quantity affected': 'affected_quantity',
        'quantity of product': 'affected_quantity',
        'quantity received': 'affected_quantity',
        'quantity': 'affected_quantity',
        'affected qty': 'affected_quantity',
        'qty affected': 'affected_quantity',
        'qty': 'affected_quantity',
        'detailed complaint description': 'complaint_description',
        'complaint description': 'complaint_description',
        'description of complaint': 'complaint_description',
        'complaint details': 'complaint_description',
        'description': 'complaint_description',
        'problem description': 'complaint_description',
        'event description': 'complaint_description',
        'complaint narrative': 'complaint_description',
        'narrative': 'complaint_description'
    }

    BATCH_BLACKLIST = {
        "chat", "the chat", "from the chat", "document", "the document",
        "pdf", "file", "uploaded", "form", "the form", "from the form",
        "test case", "test case 4", "unspecified", "none", "null",
        "unknown", "left-side", "the left-side", "complaint", "record",
        "identification", "batch identification", "product & batch identification",
        "section", "section 2", "had", "was", "were", "have", "has", "with",
        "from", "that", "this", "label", "vial", "vials", "carton", "cartons",
        "details", "origin", "product", "batch", "lot", "number", "name",
        "date", "site", "strength", "information"
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
            if clean.lower() in {'had', 'was', 'were', 'with', 'have', 'has', 'contains', 'label', 'vials', 'bottles', 'cartons', 'pharmacy', 'hospital'}:
                return False
        return True

    keys_sorted = sorted(KEY_LINE_MAP.keys(), key=len, reverse=True)
    NON_FIELD_PREFIXES = {'action', 'stated', 'reported', 'impact', 'assessment', 'specification', 'follow-up', 'details', 'information', 'name', 'number', 'product', 'complaint', 'report', '&'}

    # Expand lines if multiple fields appear on single line (e.g. period/semicolon delimited)
    pattern_keys = '|'.join(sorted([re.escape(k) for k in KEY_LINE_MAP.keys()], key=len, reverse=True))
    inline_split_pat = re.compile(rf'(?<=[.;,\n])\s*(?=(?:{pattern_keys})\s*(?:[:=|\t]|\s-\s))', re.IGNORECASE)

    raw_lines = text.splitlines()
    lines_list = []
    for raw_l in raw_lines:
        raw_l = raw_l.strip()
        if not raw_l:
            continue
        parts = inline_split_pat.split(raw_l)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                lines_list.append(p_clean)

    line_idx = 0
    section_header_pat = re.compile(
        r'^(?:#+\s*)?(?:SECTION\s*\d+|REQUESTED\s+ACTION|ADDITIONAL\s+INFORMATION|TASK\b|IMPORTANT\b|INSTRUCTIONS?\b|STEP\s*\d+)',
        re.IGNORECASE
    )

    def parse_line_kv(l_str: str):
        # 1. Pipe-delimited table row: | Key | Value |
        if '|' in l_str:
            cells = [c.strip() for c in l_str.split('|') if c.strip()]
            if len(cells) >= 2:
                col1 = cells[0].lower()
                for k in keys_sorted:
                    if col1 == k:
                        return k, cells[1]

        # 2. Check standard delimiters: ':', '=', '\t', ' - '
        delimiters = [':', '=', '\t', ' - ']
        for delim in delimiters:
            if delim in l_str:
                k_candidate, v_candidate = l_str.split(delim, 1)
                k_clean = k_candidate.strip().lower()
                for k in keys_sorted:
                    if k_clean == k:
                        return k, v_candidate.strip()

        # 3. Space-separated key-value on form/PDF lines without punctuation
        # (e.g. "Customer Name Greenfield Retail Pharmacy", "Product Name Vitamin B12 Tablets")
        l_stripped = l_str.strip()
        l_lower = l_stripped.lower()
        for k in keys_sorted:
            if l_lower.startswith(k):
                after = l_stripped[len(k):]
                if after and after[0] in [' ', ':', '=', '\t', '-']:
                    rest = after.lstrip(' :=-\t').strip()
                    if rest and not rest.lower().startswith(('section', 'requested', 'task', 'step')):
                        return k, rest

        return None, None

    while line_idx < len(lines_list):
        line_str = lines_list[line_idx].strip()
        if not line_str or section_header_pat.match(line_str):
            line_idx += 1
            continue
        # Also skip all-caps headers without delimiters
        if line_str.isupper() and len(line_str) > 4 and (' ' in line_str or '&' in line_str) and not re.search(r'\d', line_str) and ':' not in line_str:
            line_idx += 1
            continue

        matched_k, val = parse_line_kv(line_str)
        if matched_k:
            target_f = KEY_LINE_MAP[matched_k]
            # Multi-line complaint description
            if target_f == 'complaint_description':
                desc_parts = [val] if val else []
                next_i = line_idx + 1
                while next_i < len(lines_list):
                    cand_line = lines_list[next_i].strip()
                    if section_header_pat.match(cand_line) or (cand_line.isupper() and len(cand_line) > 4 and (' ' in cand_line or '&' in cand_line)):
                        break
                    cand_k, _ = parse_line_kv(cand_line)
                    if cand_k:
                        break
                    if cand_line:
                        desc_parts.append(cand_line)
                    next_i += 1
                line_idx = next_i - 1
                fields['complaint_description'] = ' '.join(desc_parts).strip()
            else:
                # If val is empty, check next line
                if not val:
                    next_i = line_idx + 1
                    while next_i < len(lines_list) and not lines_list[next_i].strip():
                        next_i += 1
                    if next_i < len(lines_list):
                        cand_line = lines_list[next_i].strip()
                        if not section_header_pat.match(cand_line):
                            cand_k, _ = parse_line_kv(cand_line)
                            if not cand_k:
                                val = cand_line
                                line_idx = next_i
                if val:
                    val = val.strip().rstrip('.;,')
                if val and val.lower() not in ['not provided', 'none', 'null', 'n/a', 'unknown', 'unspecified']:
                    if target_f == 'batch_lot_number' and not is_valid_batch_code(val):
                        line_idx += 1
                        continue
                    if target_f == 'manufacturing_site' and (re.fullmatch(r'\d+', val) or len(val) < 3):
                        line_idx += 1
                        continue
                    if target_f == 'complaint_reference' and (len(val.split()) > 3 or any(w in val.lower() for w in ['separate', 'details', 'risk', 'please', 'keep', 'assess'])):
                        line_idx += 1
                        continue
                    if target_f == 'material_type' and val.upper() == 'API':
                        val = 'Active Pharmaceutical Ingredient (API)'
                    if target_f in ['manufacturing_date', 'expiry_date', 'complaint_date']:
                        norm = normalize_date_string(val)
                        fields[target_f] = norm if norm else val
                    else:
                        fields[target_f] = val
        line_idx += 1
    
    # 1. Extract Complaint Source e.g. "Complaint Source: Pharmacist", "Source: Pharmacist"
    if fields.get("complaint_source") is None:
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
            elif re.search(r'\b(?:hospital pharmacy|hospital clinic)\b', text, re.IGNORECASE):
                fields["complaint_source"] = "Hospital Pharmacy"
            elif re.search(r'\b(?:reported by a hospital|contacted by a hospital)\b', text, re.IGNORECASE):
                fields["complaint_source"] = "Hospital"
            elif re.search(r'\b(?:distributor)\b', text, re.IGNORECASE):
                fields["complaint_source"] = "Distributor"

    # 2. Extract Customer Name e.g. "Customer Name Greenfield Retail Pharmacy", "Customer: CityCare Community Pharmacy"
    if fields.get("customer_name") is None:
        cust_match = re.search(r'(?:^|[\n\r]|;\s*|\.\s*)\s*(?:Customer\s*Name|Customer\s*/\s*Complainant|Customer|Client|Complainant|Reporting\s*Customer)\s*:?\s+([A-Za-z0-9\s,\'\.\-]+?)(?=\s*\.|\s+(?:reported|product|batch|lot|date|manufacturing|with|had)|$|[\n\r])', text, re.IGNORECASE)
        if cust_match:
            val = cust_match.group(1).strip()
            if len(val) > 2 and not val.lower().startswith("that") and val.lower() not in ["none", "null", "not provided", "unknown", "n/a"]:
                fields["customer_name"] = val

    # 3. Extract Batch/Lot e.g. "batch MET500-KP4821", "Batch / Lot: INS100-L8834"
    if fields.get("batch_lot_number") is None:
        batch_match = re.search(r'(?:^|[\n\r]|;\s*|\.\s*)\s*(?:batch\s*/\s*lot\s*(?:number)?|batch\s*(?:number|#)?|lot\s*(?:number|#)?|b/n)\s*:\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
        if not batch_match:
            batch_match = re.search(r'\bbatch\s*(?:number|#)?\s*(?:is|=|:|\bto\b|\bshould be\b)\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
        if not batch_match:
            cand_matches = re.finditer(r'\b(?:batch|lot)\s*(?:number|#)?\s*:?\s*([A-Za-z0-9\-_]+)', text, re.IGNORECASE)
            for cm in cand_matches:
                cand = cm.group(1).strip()
                if is_valid_batch_code(cand):
                    fields["batch_lot_number"] = cand
                    break
        elif batch_match:
            cand = batch_match.group(1).strip()
            if is_valid_batch_code(cand):
                fields["batch_lot_number"] = cand
        
    # 4. Extract Product Name & Strength
    if fields.get("product_name") is None:
        prod_labeled = re.search(r'(?:^|[\n\r]|;\s*|\.\s*)\s*(?:product\s*name|drug\s*name|product|drug)\s*:?\s+([A-Za-z0-9\s,\'\.\-]+?)(?=\s+(?:strength|grade|batch|lot|manufacturing|expiry|date)|$|[\n\r])', text, re.IGNORECASE)
        if prod_labeled and len(prod_labeled.group(1).strip()) > 2 and not prod_labeled.group(1).lower().strip().startswith("type") and prod_labeled.group(1).lower().strip() not in ["none", "null", "not provided", "unknown", "n/a"]:
            fields["product_name"] = prod_labeled.group(1).strip()
        else:
            prod_simple = re.search(r'\b(Vitamin B12 Tablets|Vitamin B12|Methotrexate Injection|Methotrexate|Ceftriaxone for Injection|Ceftriaxone|Insulin Glargine Injection|Insulin Glargine|Metformin HCI|Metformin|Amoxicillin Capsules|Amoxicillin|Paracetamol|Ibuprofen|Atorvastatin|Omeprazole|Ciprofloxacin|Lisinopril|Vancomycin|Gentamicin|Meropenem)(?:\s+(?:for\s+Injection|Injection|Capsules|Tablets|Syrup|Solution))?\b', text, re.IGNORECASE)
            if prod_simple:
                fields["product_name"] = prod_simple.group(0).strip()

    # 5. Extract Strength / Grade if specified separately e.g. "Strength / Grade: 100 units/mL" or "500 mg"
    if fields.get("product_strength_grade") is None:
        strength_match = re.search(r'(?:strength\s*/\s*grade|strength|grade)\s*:?\s*(\d+\s*(?:units/mL|units/ml|units per mL|mg\s*/\s*\d+\s*m[Ll]|mg/\d+\s*m[Ll]|mg/mL|mg/ml|mg/vial|g/vial|mg|g|ml|mcg|IU/ml|IU)|USP|BP)', text, re.IGNORECASE)
        if strength_match:
            fields["product_strength_grade"] = strength_match.group(1).strip()
        else:
            str_inline = re.search(r'\b(\d+\s*(?:units/mL|units/ml|units per mL|mg\s*/\s*\d+\s*m[Ll]|mg/\d+\s*m[Ll]|mg/mL|mg/ml|mg/vial|g/vial|mg|g|mcg|IU/ml|IU))\b', text, re.IGNORECASE)
            if str_inline:
                fields["product_strength_grade"] = str_inline.group(1).strip()

    # 6. Extract Quantity e.g. "15 blister packs", "50 kg", "8 bottles", "4 cartons", "Four cartons"
    if fields.get("affected_quantity") is None:
        qty_word_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        text_processed_qty = text
        for word, num in qty_word_map.items():
            text_processed_qty = re.sub(rf'\b{word}\b', num, text_processed_qty, flags=re.IGNORECASE)

        qty_match = re.search(r'\b((?:approximately|approx\.?|about)?\s*\d+\s*(?:cartons|boxes|vials|bottles|blister packs|blisters|packs|tablets|kg|g(?!\s*/|\s*per|\s*vial|\s*tab|\s*capsule)|units(?!\s*/\s*m[Ll]|\s*per)))\b', text_processed_qty, re.IGNORECASE)
        if qty_match:
            fields["affected_quantity"] = qty_match.group(1).strip()

    # 7. Extract Dates
    if fields.get("manufacturing_date") is None:
        mfg_match = re.search(r'(?:manufactured|manufacturing date|mfg|prod date)\s*(?:on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
        if mfg_match:
            fields["manufacturing_date"] = normalize_date_string(mfg_match.group(1))

    if fields.get("expiry_date") is None:
        exp_match = re.search(r'(?:expires|expiry|expiry date|exp)\s*(?:on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
        if exp_match:
            fields["expiry_date"] = normalize_date_string(exp_match.group(1))

    if fields.get("complaint_date") is None:
        cmp_date_match = re.search(r'(?:complaint date|received|received on)\s*(?:was received on|on|:)?\s*([0-9]{1,2}[-/\s][A-Za-z0-9]+[-/\s][0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})', text, re.IGNORECASE)
        if cmp_date_match:
            fields["complaint_date"] = normalize_date_string(cmp_date_match.group(1))

    # 8. Extract Complaint Type e.g. "Temperature / Storage Concern", "broken tablets", "contamination", "labeling defect"
    if fields.get("complaint_type") is None:
        cmp_type_labeled = re.search(r'(?:^|[\n\r]|;\s*|\.\s*)\s*complaint\s*type\s*:\s*([^\n\r]+)', text, re.IGNORECASE)
        if cmp_type_labeled:
            fields["complaint_type"] = cmp_type_labeled.group(1).strip()
        elif re.search(r'mix-up|product mix|different strength', text, re.IGNORECASE):
            fields["complaint_type"] = "Suspected Product Mix-Up / Labeling Defect"
        elif re.search(r'temperature|storage|excursion|cold chain|heat', text, re.IGNORECASE):
            fields["complaint_type"] = "Temperature / Storage Concern"
        elif re.search(r'broken|cracked|chipped', text, re.IGNORECASE):
            fields["complaint_type"] = "Broken / Damaged Product"
        elif re.search(r'color|discoloration|stain|appearance', text, re.IGNORECASE):
            fields["complaint_type"] = "Packaging / Product Appearance"
        elif re.search(r'label|labeling|mislabel|obscured|illegible', text, re.IGNORECASE):
            fields["complaint_type"] = "Labeling / Information Defect"
        elif re.search(r'seal|leaking|leak|blister', text, re.IGNORECASE):
            fields["complaint_type"] = "Packaging / Seal Integrity Failure"
        elif re.search(r'contamination|foreign matter|particle', text, re.IGNORECASE):
            fields["complaint_type"] = "Contamination / Foreign Matter"

    # 9. Extract Complaint Reference if not already found
    if fields.get("complaint_reference") is None:
        ref_match = re.search(r'(?:complaint reference|complaint ref|reference number|reference|ref\s*#)\s*:?\s*([A-Za-z0-9\-_/]+)', text, re.IGNORECASE)
        if ref_match:
            val = ref_match.group(1).strip()
            if val.lower() not in ["not provided", "none", "null", "unknown", "n/a", "unspecified"]:
                if len(val.split()) <= 3 and not any(w in val.lower() for w in ["separate", "details", "risk", "please", "keep", "assess"]):
                    fields["complaint_reference"] = val

    # 10. Extract Material Type if not already found
    if fields.get("material_type") is None:
        mat_match = re.search(r'(?:material type|material)\s*(?:is|=|:|\bwas\b)?\s*([A-Za-z0-9\s\-_/()]+?)(?=\s*[\n\r]|\s+(?:site|manufacturing|date|with|batch|lot)|$)', text, re.IGNORECASE)
        if mat_match:
            val = mat_match.group(1).strip()
            if val.upper() == "API":
                val = "Active Pharmaceutical Ingredient (API)"
            if val.lower() not in ["not provided", "none", "null", "unknown", "n/a", "unspecified"]:
                fields["material_type"] = val

    # 11. Extract Manufacturing Site if not already found
    if fields.get("manufacturing_site") is None:
        site_match = re.search(r'(?:manufacturing site|facility|site|plant)\s*(?:is|=|:|\bwas\b)?\s*([A-Za-z0-9\s\.,\-_/()]+?)(?=\s*[\n\r]|\s+(?:material|date|with|batch|lot)|$)', text, re.IGNORECASE)
        if site_match and not site_match.group(1).lower().startswith("date"):
            val = site_match.group(1).strip().strip(".,;")
            if not re.fullmatch(r'\d+', val) and len(val) >= 3 and val.lower() not in ["not provided", "none", "null", "unknown", "n/a", "unspecified", "plant", "site"]:
                fields["manufacturing_site"] = val

    # 12. Extract Complaint Description if explicitly labeled
    if fields.get("complaint_description") is None or fields.get("complaint_description") == text:
        desc_match = re.search(
            r'(?:detailed complaint description|complaint description|description)\s*:\s*(.+?)(?=\s*(?:SECTION\s*\d+|REQUESTED\s+ACTION|ADDITIONAL\s+INFORMATION|TASK\b|IMPORTANT\b|INSTRUCTIONS?\b|Please\s+do|Determine\s+the\s+risk)|$)',
            text, re.IGNORECASE | re.DOTALL
        )
        if desc_match:
            cand_desc = desc_match.group(1).strip()
            # Remove any trailing section headings or instruction footers
            cand_desc = re.sub(r'(?:SECTION\s*\d+|REQUESTED\s+ACTION|ADDITIONAL\s+INFORMATION|TASK\b|IMPORTANT\b).*$', '', cand_desc, flags=re.IGNORECASE | re.DOTALL).strip()
            fields["complaint_description"] = cand_desc
        else:
            # Strip instruction boilerplate
            cleaned = text
            for instr in [
                "Please analyze this complaint", "Please do TWO things", "Important:",
                "Determine the risk level", "Do not invent information", "Keep the complaint details separate",
                "Please fill the complaint form", "REQUESTED ACTION:", "SECTION 1:"
            ]:
                if instr in cleaned:
                    if "Complaint Description:" in cleaned:
                        cleaned = cleaned.split("Complaint Description:")[-1]
                    else:
                        cleaned = cleaned.split(instr)[0]
            fields["complaint_description"] = cleaned.strip()

    # Synchronize aliases in fallback extraction
    st_val = fields.get("product_strength_grade") or fields.get("product_strength")
    if st_val:
        fields["product_strength_grade"] = st_val
        fields["product_strength"] = st_val
    ref_val = fields.get("complaint_reference") or fields.get("complaint_number")
    if ref_val:
        fields["complaint_reference"] = ref_val
        fields["complaint_number"] = ref_val

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

    fallback_fields = fallback_regex_extraction(raw_text)
    if not extracted:
        extracted = fallback_fields
    else:
        # Merge: If LLM left any field None/empty/unspecified, but fallback extracted it directly from labeled text in raw_text, use the fallback!
        for k, fb_val in fallback_fields.items():
            if fb_val and (not extracted.get(k) or str(extracted.get(k)).lower() in ["not provided", "none", "null", "unknown", "n/a", "unspecified"]):
                extracted[k] = fb_val

    # Clean up empty strings or non-provided placeholders to None and normalize dates
    for k, v in extracted.items():
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped == "" or v_stripped.lower() in ["not provided", "none", "null", "unknown", "n/a", "unspecified"]:
                extracted[k] = None
        if k in ["manufacturing_date", "expiry_date", "complaint_date"] and v:
            extracted[k] = normalize_date_string(str(v))

    # Synchronize canonical aliases in final extracted dict
    st_val = extracted.get("product_strength_grade") or extracted.get("product_strength")
    if st_val:
        extracted["product_strength_grade"] = st_val
        extracted["product_strength"] = st_val

    ref_val = extracted.get("complaint_reference") or extracted.get("complaint_number")
    if ref_val:
        extracted["complaint_reference"] = ref_val
        extracted["complaint_number"] = ref_val

    return {"extracted_fields": extracted}

