from app.workflow.nodes.extraction import extraction_node
from app.workflow.nodes.validation import validation_node
from app.workflow.nodes.severity import severity_node
from app.workflow.graph import complaint_workflow_app

def test_extraction_and_validation():
    raw_text = "A customer reported that Metformin 500 mg batch MET500-KP4821 had 15 blister packs of broken tablets received on 11 September 2026."
    
    state = {"raw_input_text": raw_text}
    res = extraction_node(state)
    fields = res["extracted_fields"]
    
    assert fields["product_name"] == "Metformin"
    assert fields["batch_lot_number"] == "MET500-KP4821"
    
    val_state = {"extracted_fields": fields}
    val_res = validation_node(val_state)["validation"]
    assert val_res["completeness_score"] > 0
    assert "Customer Name" in val_res["missing_fields"]

def test_full_graph_execution():
    raw_text = "A customer reported that several Metformin 500 mg tablets from batch MET500-KP4821 had broken tablets inside 15 blister packs. The batch was manufactured on 18 March 2026 and expires on 17 March 2029. The complaint was received on 11 September 2026. No patient injury was reported."
    
    initial_state = {
        "raw_input_text": raw_text,
        "document_filename": None,
        "db_session": None,
        "extracted_fields": {},
        "validation": {},
        "risk_assessment": {},
        "duplicates": {},
        "root_cause_recommendations": [],
        "capa_recommendations": [],
        "executive_summary": "",
        "error_logs": []
    }
    
    final_state = complaint_workflow_app.invoke(initial_state)
    assert final_state["extracted_fields"]["batch_lot_number"] == "MET500-KP4821"
    assert final_state["risk_assessment"]["severity_level"] in ["Critical", "Major", "Minor", "Low"]
    assert len(final_state["root_cause_recommendations"]) > 0
    assert len(final_state["capa_recommendations"]) > 0
    assert len(final_state["executive_summary"]) > 0
