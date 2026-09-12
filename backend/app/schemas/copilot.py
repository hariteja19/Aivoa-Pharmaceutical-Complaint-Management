import re
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator

class ComplaintStructuredFields(BaseModel):
    model_config = {"extra": "forbid"}

    complaint_reference: Optional[str] = None
    complaint_number: Optional[str] = None
    complaint_source: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    product_strength_grade: Optional[str] = None
    batch_lot_number: Optional[str] = None
    affected_quantity: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    manufacturing_site: Optional[str] = None
    material_type: Optional[str] = None
    complaint_type: Optional[str] = None
    complaint_date: Optional[str] = None
    complaint_description: Optional[str] = None
    severity_level: Optional[str] = None
    priority: Optional[str] = None

    @model_validator(mode="after")
    def sync_aliases(self):
        st = self.product_strength_grade or self.product_strength
        if st:
            self.product_strength_grade = st
            self.product_strength = st
        ref = self.complaint_reference or self.complaint_number
        if ref:
            self.complaint_reference = ref
            self.complaint_number = ref
        return self

    @field_validator("complaint_reference")
    @classmethod
    def validate_reference(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        clean = re.sub(r'(?:[\.\s;,-]+|\s+)SECTION\s*\d+.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = clean.strip('.,;:#"\' ')
        # Reject instruction text or conversational fragments
        instruction_words = {
            "please", "separate", "details", "risk", "assess", "assessment",
            "keep", "instruction", "following", "task", "form", "section",
            "left-side", "populate", "invent", "below", "record"
        }
        words = clean.lower().split()
        if any(w in instruction_words for w in words):
            return None
        if len(words) > 3 or len(clean) > 40:
            return None
        return clean

    @field_validator("customer_name", "material_type", "product_name", "complaint_source", "manufacturing_site", "complaint_type")
    @classmethod
    def clean_section_headers(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        clean = re.sub(r'(?:[\.\s;,-]+|\s+)SECTION\s*\d+.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = re.sub(r'(?:[\.\s;,-]+|\s+)REQUESTED\s+ACTION.*$', '', clean, flags=re.IGNORECASE).strip()
        clean = clean.rstrip('.,;').strip()
        return clean

    @field_validator("manufacturing_site")
    @classmethod
    def validate_manufacturing_site(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip().rstrip('.,;').strip()
        # Reject single numbers or numbers-only fragments like "2"
        if re.fullmatch(r'\d+', clean) or len(clean) < 3:
            return None
        if clean.lower() in {"unknown", "not provided", "none", "null", "unspecified", "plant", "site"}:
            return None
        return clean

    @field_validator("product_name")
    @classmethod
    def validate_product_name(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        if clean.endswith(" Product") and not clean.startswith("Finished"):
            clean = clean[:-8].strip()
        return clean

    @field_validator("batch_lot_number")
    @classmethod
    def validate_batch(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        blacklist = {
            "identification", "batch identification", "product & batch identification",
            "section", "section 2", "form", "the form", "chat", "document", "uploaded",
            "none", "null", "unknown", "record", "unspecified"
        }
        if clean.lower() in blacklist:
            return None
        return clean

    @field_validator("product_strength")
    @classmethod
    def validate_strength(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        return clean

    @field_validator("material_type")
    @classmethod
    def validate_material(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        if clean.upper() == "API":
            return "Active Pharmaceutical Ingredient (API)"
        return clean

    @field_validator("complaint_description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        markers = [
            "Please analyze this complaint", "Please do TWO things", "Important:",
            "Determine the risk level", "Do not invent information", "REQUESTED ACTION:",
            "SECTION 1:", "SECTION 2:", "SECTION 3:", "Keep the complaint details separate",
            "Please fill the complaint form"
        ]
        if "Complaint Description:" in clean:
            clean = clean.split("Complaint Description:")[-1].strip()
        for marker in markers:
            if marker in clean:
                clean = clean.split(marker)[0].strip()
        return clean

    @field_validator("severity_level")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        m = re.search(r'\b(Critical|Major|Minor|Low)\b', clean, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
        return clean.capitalize()

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = str(v).strip()
        m = re.search(r'\b(Urgent|High|Medium|Low)\b', clean, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
        return clean.capitalize()

class ChatMessage(BaseModel):
    sender: str = Field(..., description="'user' or 'copilot'")
    text: str
    timestamp: Optional[str] = None

class CopilotChatRequest(BaseModel):
    current_fields: Dict[str, Any] = Field(default_factory=dict, description="Currently populated complaint form fields")
    user_message: str = Field(..., description="Correction or instruction from user")
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")
    document_text: Optional[str] = Field(None, description="Raw text of uploaded document/complaint if available")
    document_name: Optional[str] = Field(None, description="Filename of uploaded document")
    extracted_fields: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Pre-extracted structured complaint fields")

class CopilotAction(BaseModel):
    model_config = {"extra": "forbid"}
    intent: str = Field("update_form_fields", description="'update_form_fields', 'generate_email', 'clarification_needed', or 'general_chat'")
    updates: ComplaintStructuredFields = Field(default_factory=ComplaintStructuredFields, description="Canonical complaint fields to update")

class CopilotChatResponse(BaseModel):
    intent: str = Field("update_form_fields", description="'update_form_fields', 'generate_email', 'clarification_needed', or 'general_chat'")
    updates: Dict[str, Any] = Field(default_factory=dict, description="Canonical field updates dictionary")
    structured_fields: Optional[ComplaintStructuredFields] = Field(None, description="Strict structured complaint fields object")
    copilot_reply: str = Field(..., description="Assistant explanation response")
    message: Optional[str] = Field(None, description="Structured message response (alias of copilot_reply)")
    modified_field_keys: List[str] = Field(default_factory=list, description="List of field keys changed in this step")
    recalculated_analysis: Optional[Dict[str, Any]] = None
    is_new_complaint: bool = Field(False, description="True if this operation is a complete complaint intake rather than single-field edit")


