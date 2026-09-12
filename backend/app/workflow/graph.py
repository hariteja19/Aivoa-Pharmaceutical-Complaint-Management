from langgraph.graph import StateGraph, START, END
from app.workflow.state import ComplaintGraphState
from app.workflow.nodes.extraction import extraction_node
from app.workflow.nodes.validation import validation_node
from app.workflow.nodes.severity import severity_node
from app.workflow.nodes.duplicate import duplicate_node
from app.workflow.nodes.root_cause import root_cause_node
from app.workflow.nodes.capa import capa_node
from app.workflow.nodes.summary import summary_node
from app.core.logging import logger

def build_complaint_workflow():
    """
    Constructs the LangGraph StateGraph pipeline for customer complaint processing.
    Flow: START -> Extract -> Validate -> Severity -> Duplicates -> RootCause -> CAPA -> Summary -> END
    """
    workflow = StateGraph(ComplaintGraphState)

    # Add Nodes
    workflow.add_node("extract_fields", extraction_node)
    workflow.add_node("validate_completeness", validation_node)
    workflow.add_node("assess_severity", severity_node)
    workflow.add_node("check_duplicates", duplicate_node)
    workflow.add_node("recommend_root_causes", root_cause_node)
    workflow.add_node("recommend_capa", capa_node)
    workflow.add_node("generate_summary", summary_node)

    # Add Edges (Linear sequential GxP pipeline)
    workflow.add_edge(START, "extract_fields")
    workflow.add_edge("extract_fields", "validate_completeness")
    workflow.add_edge("validate_completeness", "assess_severity")
    workflow.add_edge("assess_severity", "check_duplicates")
    workflow.add_edge("check_duplicates", "recommend_root_causes")
    workflow.add_edge("recommend_root_causes", "recommend_capa")
    workflow.add_edge("recommend_capa", "generate_summary")
    workflow.add_edge("generate_summary", END)

    app = workflow.compile()
    return app

complaint_workflow_app = build_complaint_workflow()
