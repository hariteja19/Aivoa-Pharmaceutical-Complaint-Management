import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_regression_vitamin_b12_with_user_instructions():
    """
    REGRESSION TEST: Vitamin B12 complaint with user instructions.
    Verifies that:
    1. complaint_reference is 'QMS-CC-2026-0924', NOT 'int details separate...'
    2. manufacturing_site is 'Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad', NOT '2'
    3. User instructions ('Keep the complaint details separate...', 'Please fill...') are NOT parsed into fields
    4. severity_level is 'Minor' or 'Low', NOT 'Major'
    5. CAPA does NOT issue 'Quality Alert' for minor appearance issues
    """
    prompt = """Keep the complaint details separate from the risk assessment.
Please fill the complaint form with the following details:

Complaint Reference:
QMS-CC-2026-0924

Complaint Source:
Retail Pharmacy

Customer Name:
Greenfield Retail Pharmacy

Product Name:
Vitamin B12 Tablets

Product Strength / Grade:
500 mcg

Batch / Lot Number:
VB12-500-M3182

Quantity Affected:
Approximately 10 tablets

Manufacturing Date:
21-Jun-2026

Expiry Date:
20-Jun-2029

Manufacturing Site:
Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad

Material Type:
Finished Pharmaceutical Product

Complaint Type:
Tablet Appearance Concern

Complaint Date:
12-Sep-2026

Complaint Description:
A retail pharmacy reported that approximately 10 tablets from one bottle had slight variation in surface color compared with the other tablets in the same bottle. The tablets were intact, dry, and not broken or chipped. The bottle, label, and outer packaging were intact and clearly readable. The pharmacy did not dispense any of the affected tablets to customers. The bottle was retained at the pharmacy and photographs were taken for quality review.

Patient Exposure:
No affected tablets were dispensed.

Patient Harm:
No patient complaint, adverse event, or health impact reported.

Stock Status:
Affected bottle retained and removed from sale.

Evidence Available:
Photographs of tablets, bottle, and packaging.
"""
    res = client.post("/api/copilot/chat", json={
        "user_message": prompt,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    
    assert updates["complaint_reference"] == "QMS-CC-2026-0924"
    assert "separate" not in updates["complaint_reference"].lower()
    assert "details" not in updates["complaint_reference"].lower()
    
    assert updates["complaint_source"] == "Retail Pharmacy"
    assert updates["customer_name"] == "Greenfield Retail Pharmacy"
    assert updates["product_name"] == "Vitamin B12 Tablets"
    assert updates["product_strength"] == "500 mcg"
    assert updates["batch_lot_number"] == "VB12-500-M3182"
    assert updates["affected_quantity"] == "Approximately 10 tablets"
    assert updates["manufacturing_date"] in ["2026-06-21", "21-06-2026", "21-Jun-2026"]
    assert updates["expiry_date"] in ["2029-06-20", "20-06-2029", "20-Jun-2029"]
    assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
    assert updates["manufacturing_site"] != "2"
    assert updates["material_type"] == "Finished Pharmaceutical Product"
    assert updates["complaint_type"] == "Tablet Appearance Concern"
    assert updates["complaint_date"] in ["2026-09-12", "12-09-2026", "12-Sep-2026"]
    assert "A retail pharmacy reported that approximately 10 tablets" in updates["complaint_description"]
    assert "Keep the complaint details separate" not in updates["complaint_description"]
    
    # Verify assessment fields are separate and fresh
    recalc = data["recalculated_analysis"]
    assert recalc is not None
    assert recalc["risk_assessment"]["severity_level"] in ["Minor", "Low"]
    assert recalc["risk_assessment"]["severity_level"] != "Critical"
    assert recalc["risk_assessment"]["severity_level"] != "Major"
    
    # Verify CAPA does not issue Quality Alert for minor appearance concern
    capas = recalc["capa_recommendations"]
    assert not any("Quality Alert" in c for c in capas)
    assert any("VB12-500-M3182" in c for c in capas)


def test_regression_single_field_updates():
    """
    TEST 2: Single-field updates.
    Verifies that changing batch, site, or material type modifies ONLY that target field.
    """
    current = {
        "complaint_reference": "QMS-CC-2026-0924",
        "complaint_source": "Retail Pharmacy",
        "customer_name": "Greenfield Retail Pharmacy",
        "product_name": "Vitamin B12 Tablets",
        "product_strength": "500 mcg",
        "batch_lot_number": "VB12-500-M3182",
        "affected_quantity": "Approximately 10 tablets",
        "manufacturing_date": "2026-06-21",
        "expiry_date": "2029-06-20",
        "manufacturing_site": "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad",
        "material_type": "Finished Pharmaceutical Product",
        "complaint_type": "Tablet Appearance Concern",
        "complaint_date": "2026-09-12",
        "complaint_description": "Slight variation in surface color."
    }
    
    # 1. Change batch
    res1 = client.post("/api/copilot/chat", json={
        "user_message": "Change the batch / lot number to TEST-ABC-123.",
        "current_fields": current
    })
    assert res1.status_code == 200
    u1 = res1.json()["updates"]
    assert u1.get("batch_lot_number") == "TEST-ABC-123"
    assert "product_name" not in res1.json()["modified_field_keys"]
    assert "customer_name" not in res1.json()["modified_field_keys"]

    # 2. Change manufacturing site
    res2 = client.post("/api/copilot/chat", json={
        "user_message": "Change the manufacturing site to Asterion Pharmaceuticals Ltd., Plant 3, Hyderabad.",
        "current_fields": current
    })
    assert res2.status_code == 200
    u2 = res2.json()["updates"]
    assert u2.get("manufacturing_site") == "Asterion Pharmaceuticals Ltd., Plant 3, Hyderabad"
    assert u2.get("manufacturing_site") != "2"
    assert u2.get("manufacturing_site") != "3"
    assert "product_name" not in res2.json()["modified_field_keys"]

    # 3. Change material type
    res3 = client.post("/api/copilot/chat", json={
        "user_message": "Change the material type to Finished Pharmaceutical Product.",
        "current_fields": current
    })
    assert res3.status_code == 200
    u3 = res3.json()["updates"]
    assert u3.get("material_type") == "Finished Pharmaceutical Product"
    assert "product_name" not in res3.json()["modified_field_keys"]


def test_regression_new_complaint_reset_isolation():
    """
    TEST 3: Context isolation between consecutive complaints.
    Verifies that loading Insulin Glargine does not leave Vitamin B12 data,
    and loading Vitamin B12 again does not retain Insulin Glargine data.
    """
    # 1. Load Insulin Glargine
    insulin_prompt = """
Product Name: Insulin Glargine Injection
Batch / Lot Number: INS100-L8834
Complaint Type: Temperature / Storage Concern
Complaint Description: Temperature excursion occurred with vials stored above cold-chain limits.
"""
    res_ins = client.post("/api/copilot/chat", json={
        "user_message": insulin_prompt,
        "current_fields": {}
    })
    assert res_ins.status_code == 200
    ins_recalc = res_ins.json()["recalculated_analysis"]
    assert ins_recalc["risk_assessment"]["severity_level"] == "Major"
    assert any("INS100-L8834" in c for c in ins_recalc["capa_recommendations"])
    assert not any("VB12" in c for c in ins_recalc["capa_recommendations"])
    
    # 2. Now load Vitamin B12
    b12_prompt = """
Product Name: Vitamin B12 Tablets
Batch / Lot Number: VB12-500-M3182
Complaint Type: Tablet Appearance Concern
Complaint Description: Slight variation in surface color of tablets in one bottle.
"""
    res_b12 = client.post("/api/copilot/chat", json={
        "user_message": b12_prompt,
        "current_fields": {}
    })
    assert res_b12.status_code == 200
    b12_recalc = res_b12.json()["recalculated_analysis"]
    assert b12_recalc["risk_assessment"]["severity_level"] in ["Minor", "Low"]
    assert not any("INS100-L8834" in c for c in b12_recalc["capa_recommendations"])
    assert any("VB12-500-M3182" in c for c in b12_recalc["capa_recommendations"])


def test_regression_document_and_copilot_parity():
    """
    TEST 4: Parity between document processing and Copilot structured extraction.
    """
    doc_text = """Complaint Reference: QMS-CC-2026-0924
Complaint Source: Retail Pharmacy
Customer Name: Greenfield Retail Pharmacy
Product Name: Vitamin B12 Tablets
Product Strength / Grade: 500 mcg
Batch / Lot Number: VB12-500-M3182
Quantity Affected: Approximately 10 tablets
Manufacturing Date: 21-Jun-2026
Expiry Date: 20-Jun-2029
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad
Material Type: Finished Pharmaceutical Product
Complaint Type: Tablet Appearance Concern
Complaint Date: 12-Sep-2026
Complaint Description: Slight variation in surface color."""

    res_proc = client.post("/api/complaints/process", json={"text": doc_text})
    assert res_proc.status_code == 200
    proc_fields = res_proc.json()["extracted_fields"]
    
    res_cop = client.post("/api/copilot/chat", json={
        "user_message": doc_text,
        "current_fields": {}
    })
    assert res_cop.status_code == 200
    cop_fields = res_cop.json()["updates"]
    
    assert proc_fields["complaint_reference"] == cop_fields["complaint_reference"] == "QMS-CC-2026-0924"
    assert proc_fields["manufacturing_site"] == cop_fields["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
    assert proc_fields["batch_lot_number"] == cop_fields["batch_lot_number"] == "VB12-500-M3182"
    assert proc_fields["product_name"] == cop_fields["product_name"] == "Vitamin B12 Tablets"


def test_regression_user_paracetamol_complaint_form_fill():
    """
    TEST 5: Full complaint intake from user prompt with meta-instructions,
    stopping headers, and previous stale form fields.
    """
    prompt = """Please fill the complaint form using all the details from this complaint.

Complaint Reference: QMS-CC-2026-0816
Complaint Source: Community Pharmacy
Customer Name: WellCare Community Pharmacy
Product Name: Paracetamol Tablets
Product Strength / Grade: 500 mg
Batch / Lot Number: PCM500-T2846
Quantity Affected: Approximately 15 tablets
Manufacturing Date: 10-Jun-2026
Expiry Date: 09-Jun-2029
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 1, Hyderabad
Material Type: Finished Pharmaceutical Product
Complaint Type: Tablet Appearance Concern
Complaint Date: 12-Sep-2026
Complaint Description: The pharmacy reported that approximately 15 tablets from one bottle had minor surface discoloration. The tablets remained intact and were not broken or chipped. The bottle label and packaging were clear, legible, and intact. The pharmacy confirmed that no tablets from the affected bottle had been dispensed to a patient. The bottle was retained at the pharmacy for review.

Patient Exposure: No patient received tablets from the affected bottle.
Patient Harm: No patient harm or adverse event reported.
Stock Status: Affected bottle retained and not dispensed.
Evidence Available: Photographs of tablets and bottle label.

Requested Action: Review the reported tablet appearance concern against the approved product specification, inspect the retained sample, and review relevant batch records as appropriate.

Please do the following:
1. Populate every matching field on the left-side complaint form.
2. Assess the complaint based only on the facts provided.
3. Determine the AI Risk Classification.
4. Determine the Initial Severity.
5. Determine the Priority.
6. Identify the key risk factors.
7. Provide recommended actions.

Do not invent, change, truncate, or mix any information. Do not use a pre-defined severity or priority. Determine the risk from the actual complaint facts. Keep the complaint information separate from the risk assessment.
"""
    res = client.post("/api/copilot/chat", json={
        "user_message": prompt,
        "current_fields": {
            "product_name": "Vitamin B12 Tablets",
            "batch_lot_number": "VB12-500-M3182",
            "manufacturing_site": "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["is_new_complaint"] is True
    updates = data["updates"]
    assert updates["complaint_reference"] == "QMS-CC-2026-0816"
    assert updates["complaint_source"] == "Community Pharmacy"
    assert updates["customer_name"] == "WellCare Community Pharmacy"
    assert updates["product_name"] == "Paracetamol Tablets"
    assert updates["product_strength"] == "500 mg"
    assert updates["batch_lot_number"] == "PCM500-T2846"
    assert updates["affected_quantity"] == "Approximately 15 tablets"
    assert updates["manufacturing_date"] == "2026-06-10"
    assert updates["expiry_date"] == "2029-06-09"
    assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 1, Hyderabad"
    assert updates["material_type"] == "Finished Pharmaceutical Product"
    assert updates["complaint_type"] == "Tablet Appearance Concern"
    assert updates["complaint_date"] == "2026-09-12"
    assert "minor surface discoloration" in updates["complaint_description"]
    assert "Please do the following" not in updates["complaint_description"]
    assert "Patient Exposure" not in updates["complaint_description"]

    # Verify risk assessment is Minor / Low without adverse events
    recalc = data["recalculated_analysis"]
    assert recalc["risk_assessment"]["severity_level"] in ["Minor", "Low"]
    assert recalc["risk_assessment"]["patient_risk_flag"] is False

