from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    sender: str = Field(..., description="'user' or 'copilot'")
    text: str
    timestamp: Optional[str] = None

class CopilotChatRequest(BaseModel):
    current_fields: Dict[str, Any] = Field(..., description="Currently populated complaint form fields")
    user_message: str = Field(..., description="Correction or instruction from user")
    chat_history: Optional[List[ChatMessage]] = Field(default=[], description="Previous conversation turns")

class CopilotChatResponse(BaseModel):
    intent: str = Field("update_form_fields", description="'update_form_fields', 'clarification_needed', or 'general_chat'")
    updates: Dict[str, Any] = Field(default_factory=dict, description="Canonical field updates dictionary")
    copilot_reply: str = Field(..., description="Assistant explanation response")
    modified_field_keys: List[str] = Field(default_factory=list, description="List of field keys changed in this step")
    recalculated_analysis: Optional[Dict[str, Any]] = None
