from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_process_text_endpoint():
    payload = {
        "text": "A customer reported that Metformin 500 mg tablets from batch MET500-KP4821 had broken tablets inside 15 blister packs. Manufactured on 18 March 2026 and expires on 17 March 2029."
    }
    response = client.post("/api/complaints/process", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "extracted_fields" in data
    assert data["extracted_fields"]["batch_lot_number"] == "MET500-KP4821"
    assert data["extracted_fields"]["manufacturing_date"] == "2026-03-18"

def test_copilot_single_field_updates():
    test_cases = [
        ("The customer name is Green Valley Pharmacy.", "customer_name", "Green Valley Pharmacy"),
        ("Change the product name to Amoxicillin Capsules.", "product_name", "Amoxicillin Capsules"),
        ("Set the strength to 250 mg.", "product_strength_grade", "250 mg"),
        ("The batch number is CHG 260712A.", "batch_lot_number", "CHG 260712A"),
        ("Change the affected quantity to 50 kg.", "affected_quantity", "50 kg"),
        ("Manufacturing date is 25 June 2026.", "manufacturing_date", "2026-06-25"),
        ("Expiry date should be 24 June 2029.", "expiry_date", "2029-06-24"),
        ("Set the manufacturing site to Facility Alpha.", "manufacturing_site", "Facility Alpha"),
        ("Material type is API.", "material_type", "Active Pharmaceutical Ingredient (API)"),
        ("Complaint date is 10 September 2026.", "complaint_date", "2026-09-10"),
        ("Change complaint type to Packaging Defect.", "complaint_type", "Packaging Defect"),
        ("Update the complaint description to broken capsules found inside blister packs.", "complaint_description", "broken capsules found inside blister packs"),
        ("Change the complaint source to Healthcare Professional.", "complaint_source", "Healthcare Professional"),
        ("Change the strength to 200 units/mL.", "product_strength_grade", "200 units/mL"),
        ("Set severity to Major.", "severity_level", "Major"),
        ("Set priority to High.", "priority", "High")
    ]

    for msg, field_key, expected_val in test_cases:
        payload = {
            "current_fields": {},
            "user_message": msg
        }
        res = client.post("/api/copilot/chat", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert body["intent"] == "update_form_fields"
        assert field_key in body["updates"]
        assert body["updates"][field_key] == expected_val
        assert field_key in body["modified_field_keys"]
        assert "I've updated the complaint record" in body["copilot_reply"]

def test_copilot_multi_field_update():
    payload = {
        "current_fields": {"product_name": "Metformin"},
        "user_message": "The batch number is CHG 260712A and the affected quantity is 50 kg."
    }
    res = client.post("/api/copilot/chat", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] == "update_form_fields"
    assert body["updates"]["batch_lot_number"] == "CHG 260712A"
    assert body["updates"]["affected_quantity"] == "50 kg"
    assert "batch_lot_number" in body["modified_field_keys"]
    assert "affected_quantity" in body["modified_field_keys"]

def test_copilot_ambiguous_update():
    payload = {
        "current_fields": {},
        "user_message": "Change it to 50 kg"
    }
    res = client.post("/api/copilot/chat", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["intent"] in ["clarification_needed", "update_form_fields"]

def test_testcase_3_pdf_extraction_mapping_and_assessment():
    text = """
Complaint Source: Pharmacist
Customer: CityCare Community Pharmacy
Product: Insulin Glargine Injection
Strength / Grade: 100 units/mL
Batch / Lot: INS100-L8834
Manufacturing Date: 03-Feb-2026
Expiry Date: 02-Feb-2028
Complaint Date: 08-Sep-2026
Complaint Type: Temperature / Storage Concern

Narrative: Four cartons were affected by a temperature indicator excursion above the recommended storage range. The exact duration of the excursion is unknown. The affected stock was segregated and not dispensed. No patient adverse event was reported.
"""
    payload = {"text": text}
    res = client.post("/api/complaints/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    extracted = data["extracted_fields"]
    
    # 1. Structured Fact Extractions
    assert extracted["complaint_source"] == "Pharmacist"
    assert extracted["customer_name"] == "CityCare Community Pharmacy"
    assert extracted["product_name"] == "Insulin Glargine Injection"
    assert extracted["product_strength_grade"] == "100 units/mL"
    assert extracted["batch_lot_number"] == "INS100-L8834"
    assert extracted["manufacturing_date"] == "2026-02-03"
    assert extracted["expiry_date"] == "2028-02-02"
    assert extracted["complaint_date"] == "2026-09-08"
    assert extracted["complaint_type"] == "Temperature / Storage Concern"
    assert extracted["affected_quantity"] == "4 cartons"
    
    # 2. Zero-hallucination checks
    assert extracted["manufacturing_site"] is None
    assert extracted["material_type"] is None

    # 3. Section 4 Assessment Checks
    risk = data["risk_assessment"]
    assert risk["severity_level"] in ["Major", "Critical"]
    assert risk["priority"] in ["High", "Urgent"]
    assert "temperature" in risk["rationale"].lower() or "excursion" in risk["rationale"].lower()
