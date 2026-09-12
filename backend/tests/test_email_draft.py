from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_email_draft_endpoint_success():
    payload = {
        "complaint_number": "CMP-2026-94812",
        "customer_name": "Green Valley Pharmacy",
        "product_name": "Amoxicillin Capsules",
        "product_strength_grade": "250 mg",
        "batch_lot_number": "AMX250-B6729",
        "affected_quantity": "8 bottles",
        "complaint_type": "Packaging Defect",
        "complaint_description": "Discolored capsules observed inside sealed bottles.",
        "severity_level": "Major",
        "priority": "High"
    }
    # Test /api/complaints/email-draft
    response = client.post("/api/complaints/email-draft", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "to" in data
    assert "subject" in data
    assert "body" in data
    assert data["to"] == "Quality Assurance Team"
    assert "Amoxicillin Capsules" in data["subject"]
    assert "AMX250-B6729" in data["subject"]

    # Test /api/v1/complaints/email-draft
    response_v1 = client.post("/api/v1/complaints/email-draft", json=payload)
    assert response_v1.status_code == 200
    assert response_v1.json()["to"] == "Quality Assurance Team"

def test_zero_hallucination_missing_fields():
    # Only minimal fields provided - NO manufacturing site, NO dates, NO fabricated emails
    payload = {
        "product_name": "Metformin Tablets",
        "batch_lot_number": "MET-00192"
    }
    response = client.post("/api/complaints/email-draft", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Safe default recipient
    assert data["to"] == "Quality Assurance Team"
    # Never invent a fake email address
    assert "@" not in data["to"]

    body = data["body"]
    assert "Metformin Tablets" in body
    assert "MET-00192" in body
    # Missing fields should not be fabricated
    assert "Facility Alpha" not in body
    assert "Site Dublin" not in body
    assert "Green Valley" not in body

def test_email_content_contains_available_fields():
    payload = {
        "complaint_number": "CMP-2026-11223",
        "customer_name": "St. Jude Hospital",
        "complaint_source": "Healthcare Professional",
        "product_name": "Ceftriaxone Injection",
        "product_strength_grade": "1g",
        "batch_lot_number": "CTX-99201",
        "affected_quantity": "40 vials",
        "manufacturing_site": "Plant Beta - Cork",
        "complaint_type": "Particulate Matter",
        "complaint_description": "Small visible white fibers observed in reconstituted solution.",
        "severity_level": "Critical",
        "priority": "Urgent",
        "patient_risk_flag": True,
        "is_possible_duplicate": True,
        "duplicate_reasons": ["Recurring particulate complaint on batch CTX-99201"]
    }
    response = client.post("/api/complaints/email-draft", json=payload)
    assert response.status_code == 200
    data = response.json()
    body = data["body"]

    assert "St. Jude Hospital" in body
    assert "Healthcare Professional" in body
    assert "Ceftriaxone Injection" in body
    assert "CTX-99201" in body
    assert "40 vials" in body
    assert "Plant Beta - Cork" in body
    assert "Critical" in body
    assert "Urgent" in body
    assert "Patient Safety Risk" in body
    assert "Recurring particulate complaint" in body

def test_ai_recommendations_framed_as_recommendations():
    payload = {
        "product_name": "Insulin Glargine",
        "batch_lot_number": "INS-4401",
        "root_cause_recommendations": ["Cold chain temperature excursion during transit"],
        "capa_recommendations": ["Verify calibrated data logger records at distributor facility"]
    }
    response = client.post("/api/complaints/email-draft", json=payload)
    assert response.status_code == 200
    body = response.json()["body"]

    # Recommendations must NOT be presented as confirmed root causes
    assert "recommends" in body.lower() or "recommended" in body.lower() or "hypotheses" in body.lower()
    assert "The confirmed root cause is" not in body

def test_copilot_recognizes_email_intents():
    sample_queries = [
        "Create an email for this complaint",
        "Draft an email to QA",
        "Generate a complaint notification email",
        "Create a Gmail",
        "Create a Gmail for this complaint",
        "Write an email about this complaint",
        "Prepare an email to the quality team",
        "Draft an email summarizing this complaint",
        "Regenerate the email"
    ]

    for q in sample_queries:
        res = client.post("/api/copilot/chat", json={
            "current_fields": {"product_name": "Metformin", "batch_lot_number": "MET-123"},
            "user_message": q,
            "chat_history": []
        })
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "generate_email", f"Failed to detect generate_email intent for query: '{q}'"
        assert "generated a complaint notification email" in data["copilot_reply"]
        assert data.get("message") is not None

def test_dynamic_regeneration_uses_new_batch():
    # Initial complaint state with batch AMX250-B6729
    initial_payload = {
        "product_name": "Amoxicillin Capsules",
        "batch_lot_number": "AMX250-B6729",
        "complaint_description": "Broken capsules"
    }
    res1 = client.post("/api/complaints/email-draft", json=initial_payload)
    assert res1.status_code == 200
    draft1 = res1.json()
    assert "AMX250-B6729" in draft1["subject"]
    assert "AMX250-B6729" in draft1["body"]

    # User or Copilot modifies batch to CHG260712A
    updated_payload = {
        "product_name": "Amoxicillin Capsules",
        "batch_lot_number": "CHG260712A",
        "complaint_description": "Broken capsules"
    }
    res2 = client.post("/api/complaints/email-draft", json=updated_payload)
    assert res2.status_code == 200
    draft2 = res2.json()
    assert "CHG260712A" in draft2["subject"]
    assert "CHG260712A" in draft2["body"]
    assert "AMX250-B6729" not in draft2["subject"]
    assert "AMX250-B6729" not in draft2["body"]
