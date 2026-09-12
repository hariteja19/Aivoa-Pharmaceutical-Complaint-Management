class AIVOAException(Exception):
    """Base exception for AIVOA application"""
    pass

class DocumentParsingException(AIVOAException):
    """Raised when text cannot be extracted from a document"""
    pass

class AIWorkflowException(AIVOAException):
    """Raised when LangGraph or LLM processing fails"""
    pass

class ComplaintNotFoundException(AIVOAException):
    """Raised when a requested complaint is not found in DB"""
    pass
