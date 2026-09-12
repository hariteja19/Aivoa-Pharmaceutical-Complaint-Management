import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_CASE_4_DOCUMENT_TEXT = """
Complaint Reference: CC-QA-2026-0476
Complaint Source: Hospital Pharmacy
Customer: Lakeside General Hospital
Product: Ceftriaxone for Injection
Strength/Grade: 1 g/vial
Batch/Lot: CFT1G-R4516
Manufacturing Date: 12-Apr-2026
Expiry Date: 11-Apr-2028
Complaint Date: 09-Sep-2026
Complaint Type: Labeling / Information Defect
Affected Quantity: Approximately 20 vials

Complaint Description:
The hospital pharmacy reported that several cartons of Ceftriaxone for Injection contained vial labels with incomplete administration information. The dosage strength was visible, but the reconstitution instructions were partially obscured on some labels. Approximately 20 vials were identified during an internal pharmacy check. The affected stock has been segregated and is being held pending quality review.
"""

def test_copilot_populate_form_from_uploaded_test_case_4():
    """
    Test Case 4 Regression Test:
    Simulates user asking: 'Please use the uploaded Test Case 4 complaint and populate the left-side complaint form with all information available in the document.'
    """
    payload = {
        "user_message": "Please use the uploaded Test Case 4 complaint and populate the left-side complaint form with all information available in the document.",
        "document_text": TEST_CASE_4_DOCUMENT_TEXT,
        "document_name": "TestCase4_Complaint.pdf",
        "current_fields": {}
    }
    response = client.post("/api/copilot/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    
    # Check all canonical fields
    assert updates["complaint_reference"] == "CC-QA-2026-0476"
    assert updates["complaint_source"] == "Hospital Pharmacy"
    assert updates["customer_name"] == "Lakeside General Hospital"
    assert updates["product_name"] == "Ceftriaxone for Injection"
    assert updates["product_strength"] == "1 g/vial"
    assert updates["batch_lot_number"] == "CFT1G-R4516"
    assert updates["affected_quantity"] == "Approximately 20 vials"
    assert updates["manufacturing_date"] == "2026-04-12"
    assert updates["expiry_date"] == "2028-04-11"
    assert updates["complaint_date"] == "2026-09-09"
    assert updates["complaint_type"] == "Labeling / Information Defect"
    assert "reconstitution instructions were partially obscured" in updates["complaint_description"]
    
    # Zero hallucination check: manufacturing_site and material_type must NOT be hallucinated
    assert "manufacturing_site" not in updates or updates["manufacturing_site"] is None
    assert "material_type" not in updates or updates["material_type"] is None
    
    # Verify batch is never "chat"
    assert updates["batch_lot_number"] != "chat"


def test_copilot_populate_form_using_extracted_fields():
    """
    Simulates frontend passing extracted_fields already parsed in Redux.
    """
    extracted = {
        "complaint_reference": "CC-QA-2026-0476",
        "complaint_source": "Hospital Pharmacy",
        "customer_name": "Lakeside General Hospital",
        "product_name": "Ceftriaxone for Injection",
        "product_strength_grade": "1 g/vial",
        "batch_lot_number": "CFT1G-R4516",
        "affected_quantity": "Approximately 20 vials",
        "manufacturing_date": "2026-04-12",
        "expiry_date": "2028-04-11",
        "complaint_date": "2026-09-09",
        "complaint_type": "Labeling / Information Defect",
        "complaint_description": "The hospital pharmacy reported that several cartons of Ceftriaxone for Injection contained vial labels with incomplete administration information."
    }
    payload = {
        "user_message": "Populate the left-side form using the uploaded complaint.",
        "extracted_fields": extracted,
        "current_fields": {}
    }
    response = client.post("/api/copilot/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    assert updates["batch_lot_number"] == "CFT1G-R4516"
    assert updates["product_strength"] == "1 g/vial"
    assert updates["complaint_source"] == "Hospital Pharmacy"
    assert updates["customer_name"] == "Lakeside General Hospital"


def test_copilot_never_generates_chat_as_batch():
    """
    Section 4 Requirement:
    User asks: 'Please populate the form from the chat'
    'chat' must NEVER become batch_lot_number.
    """
    payload = {
        "user_message": "Please populate the form from the chat",
        "current_fields": {"batch_lot_number": "CFT1G-R4516"},
        "document_text": ""
    }
    response = client.post("/api/copilot/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    updates = data.get("updates", {})
    if "batch_lot_number" in updates:
        assert updates["batch_lot_number"].lower() != "chat"


def test_copilot_direct_field_updates():
    """
    Section 12: TEST DIRECT COPILOT UPDATE
    1. 'Change the batch number to DEMO-BATCH-123.' -> batch_lot_number = DEMO-BATCH-123
    2. 'Change the product strength to 2 g/vial.' -> product_strength = 2 g/vial
    3. 'Change the quantity to 50 vials and complaint type to Packaging Defect.' -> affected_quantity = 50 vials, complaint_type = Packaging Defect
    """
    # 1. Batch number update
    res1 = client.post("/api/copilot/chat", json={
        "user_message": "Change the batch number to DEMO-BATCH-123.",
        "current_fields": {}
    })
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["intent"] == "update_form_fields"
    assert data1["updates"]["batch_lot_number"] == "DEMO-BATCH-123"

    # 2. Product strength update
    res2 = client.post("/api/copilot/chat", json={
        "user_message": "Change the product strength to 2 g/vial.",
        "current_fields": {}
    })
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["intent"] == "update_form_fields"
    assert (data2["updates"].get("product_strength") == "2 g/vial" or 
            data2["updates"].get("product_strength_grade") == "2 g/vial")

    # 3. Multi-field update: quantity and complaint type
    res3 = client.post("/api/copilot/chat", json={
        "user_message": "Change the quantity to 50 vials and complaint type to Packaging Defect.",
        "current_fields": {}
    })
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["intent"] == "update_form_fields"
    assert data3["updates"]["affected_quantity"] == "50 vials"
    assert data3["updates"]["complaint_type"] == "Packaging Defect"


def test_document_extraction_with_3_fields():
    """
    TEST 1: Document extraction of complaint_reference, manufacturing_site, and material_type.
    """
    doc_text = """
Complaint Reference: CC-QA-2026-0476
Complaint Source: Hospital Pharmacy
Customer: Lakeside General Hospital
Product: Ceftriaxone for Injection
Strength/Grade: 1 g/vial
Batch/Lot: CFT1G-R4516
Manufacturing Date: 12-Apr-2026
Expiry Date: 11-Apr-2028
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad
Material Type: Finished Pharmaceutical Product
Complaint Date: 09-Sep-2026
Complaint Type: Labeling / Information Defect
Affected Quantity: Approximately 20 vials

Complaint Description:
Vial labels contained partially obscured reconstitution instructions.
"""
    res = client.post("/api/complaints/process", json={"text": doc_text})
    assert res.status_code == 200
    data = res.json()
    extracted = data["extracted_fields"]
    
    assert extracted["complaint_reference"] == "CC-QA-2026-0476"
    assert extracted["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
    assert extracted["material_type"] == "Finished Pharmaceutical Product"


def test_copilot_update_3_fields_natural_language():
    """
    TEST 2: Copilot natural language update of complaint_reference, manufacturing_site, and material_type.
    """
    msg = "Update the complaint reference to CC-QA-2026-0476, manufacturing site to Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad, and material type to Finished Pharmaceutical Product."
    res = client.post("/api/copilot/chat", json={
        "user_message": msg,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    
    assert updates["complaint_reference"] == "CC-QA-2026-0476"
    assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
    assert updates["material_type"] == "Finished Pharmaceutical Product"
    assert "complaint_reference" in data["modified_field_keys"]
    assert "manufacturing_site" in data["modified_field_keys"]
    assert "material_type" in data["modified_field_keys"]


def test_missing_fields_remain_null_and_not_hallucinated():
    """
    TEST 3: Missing manufacturing_site and material_type must remain null/blank with zero hallucination.
    """
    doc_text = """
Complaint Source: Clinic
Customer: City Clinic
Product: Amoxicillin Capsules
Strength/Grade: 250 mg
Batch/Lot: AMX250-9901
Complaint Date: 10-Sep-2026
Complaint Type: Broken Capsules
Affected Quantity: 5 bottles
Manufacturing Site: not provided
Material Type: not provided

Complaint Description:
Broken capsules were observed upon opening the seal.
"""
    res = client.post("/api/complaints/process", json={"text": doc_text})
    assert res.status_code == 200
    data = res.json()
    extracted = data["extracted_fields"]
    
    assert extracted.get("manufacturing_site") is None
    assert extracted.get("material_type") is None
    assert extracted.get("complaint_reference") is None


def test_copilot_all_complaint_details_field_mapping_regression():
    """
    CRITICAL REGRESSION TEST:
    Verifies that when Copilot is given all complaint details, every field maps to its exact canonical field:
    - batch_lot_number is CFT1G-R4516 (NEVER 'form' or 'Number')
    - affected_quantity is 'Approximately 20 vials' (NEVER '1 g')
    - product_strength is '1 g/vial'
    - complaint_type is 'Labeling/Information Defect' (NEVER concatenated with date)
    - material_type is 'Finished Pharmaceutical Product'
    - complaint_reference is 'CC-QA-2026-0476'
    - manufacturing_site is 'Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad'
    """
    prompt = """Complaint Reference: CC-QA-2026-0476
Complaint Source: Hospital Pharmacy
Customer Name: Lakeside General Hospital
Product Name: Ceftriaxone for Injection
Product Strength / Grade: 1 g/vial
Batch / Lot Number: CFT1G-R4516
Quantity Affected: Approximately 20 vials
Manufacturing Date: 12-Apr-2026
Expiry Date: 11-Apr-2028
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad
Material Type: Finished Pharmaceutical Product
Complaint Type: Labeling/Information Defect
Complaint Date: 09-Sep-2026
Complaint Description: Approximately 20 vials were found with partially obscured reconstitution instructions on the label. No patient harm was reported. The affected stock was segregated, and photos/samples are available."""
    
    res = client.post("/api/copilot/chat", json={
        "user_message": prompt,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    
    assert updates["complaint_reference"] == "CC-QA-2026-0476"
    assert updates["complaint_source"] == "Hospital Pharmacy"
    assert updates["customer_name"] == "Lakeside General Hospital"
    assert updates["product_name"] == "Ceftriaxone for Injection"
    assert updates["product_strength"] == "1 g/vial"
    assert updates["batch_lot_number"] == "CFT1G-R4516"
    assert updates["batch_lot_number"] != "form"
    assert updates["affected_quantity"] == "Approximately 20 vials"
    assert updates["affected_quantity"] != "1 g"
    assert updates["manufacturing_date"] == "2026-04-12"
    assert updates["expiry_date"] == "2028-04-11"
    assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
    assert updates["material_type"] == "Finished Pharmaceutical Product"
    assert updates["complaint_type"] == "Labeling/Information Defect"
    assert "Complaint Date" not in updates["complaint_type"]
    assert updates["complaint_date"] == "2026-09-09"


def test_copilot_order_independence_and_preservation():
    """
    Verifies that re-ordering fields does not affect extraction accuracy,
    and partial updates preserve unmentioned fields.
    """
    msg = "Batch is CFT1G-R4516, product strength is 1 g/vial, quantity is 20 vials"
    res = client.post("/api/copilot/chat", json={
        "user_message": msg,
        "current_fields": {
            "customer_name": "Lakeside General Hospital",
            "complaint_reference": "CC-QA-2026-0476"
        }
    })
    assert res.status_code == 200
    data = res.json()
    updates = data["updates"]
    assert updates["batch_lot_number"] == "CFT1G-R4516"
    assert updates["product_strength"] == "1 g/vial"
    assert updates["affected_quantity"] == "20 vials"
    assert "form" not in updates.values()


def test_copilot_update_the_complaint_form_prompt():
    """
    Verifies that conversational prompts like 'Update the complaint form'
    or 'Please update the complaint form' successfully trigger form population
    from the loaded document or chat history.
    """
    doc_text = """Complaint Reference: CC-QA-2026-0476
Complaint Source: Hospital Pharmacy
Customer Name: Lakeside General Hospital
Product Name: Ceftriaxone for Injection
Product Strength / Grade: 1 g/vial
Batch / Lot Number: CFT1G-R4516
Quantity Affected: Approximately 20 vials
Manufacturing Date: 12-Apr-2026
Expiry Date: 11-Apr-2028
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad
Material Type: Finished Pharmaceutical Product
Complaint Type: Labeling/Information Defect
Complaint Date: 09-Sep-2026
Complaint Description: Partially obscured reconstitution instructions."""

    for prompt in ["Update the complaint form", "Please update the complaint form", "Update the form with the complaint details", "Fill the complaint form"]:
        res = client.post("/api/copilot/chat", json={
            "user_message": prompt,
            "document_text": doc_text,
            "current_fields": {}
        })
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "update_form_fields"
        updates = data["updates"]
        assert updates["batch_lot_number"] == "CFT1G-R4516"
        assert updates["complaint_reference"] == "CC-QA-2026-0476"
        assert updates["product_strength"] == "1 g/vial"
        assert updates["affected_quantity"] == "Approximately 20 vials"
        assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Hyderabad"
        assert updates["material_type"] == "Finished Pharmaceutical Product"


def test_copilot_narrative_prompt_updates_form():
    """
    Verifies that when a user gives a free-form complaint narrative in a Copilot prompt,
    the Copilot extracts the complaint attributes and returns update_form_fields.
    """
    narrative = (
        "A customer reported that several Metformin 500 mg tablets from batch MET500-KP4821 "
        "had broken tablets inside 15 blister packs. The batch was manufactured on 18 March 2026 "
        "and expires on 17 March 2029. The complaint was received on 11 September 2026. "
        "No patient injury was reported."
    )
    res = client.post("/api/copilot/chat", json={
        "user_message": narrative,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    assert updates["product_name"] == "Metformin"
    assert "MET500-KP4821" in updates["batch_lot_number"]
    assert "15 blister packs" in updates["affected_quantity"]
    assert updates["manufacturing_date"] == "2026-03-18"
    assert updates["expiry_date"] == "2029-03-17"
    assert updates["complaint_date"] == "2026-09-11"
    assert "broken" in updates["complaint_type"].lower()


def test_copilot_on_the_form_qualifiers():
    """
    Verifies that prompts like 'Update the batch number on the form to ABC-123'
    update the target field rather than triggering full form overwrite.
    """
    res = client.post("/api/copilot/chat", json={
        "user_message": "Update the batch number on the form to CFT1G-R9999",
        "current_fields": {"product_name": "Ceftriaxone for Injection"}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    assert data["updates"]["batch_lot_number"] == "CFT1G-R9999"
    assert "batch_lot_number" in data["modified_field_keys"]


def test_copilot_major_severity_propagation_and_directory_registration():
    """
    REGRESSION TEST:
    Verifies that when a prompt with a major risk factor is analyzed:
    1. Copilot assesses severity as 'Major' (not Critical when no adverse event occurred).
    2. updates and structured_fields carry severity_level='Major'.
    3. When saved, the complaint is stored as 'Major' in the database.
    4. The complaints directory filter for 'Major' returns the complaint record.
    5. A true critical prompt (e.g. fatal / severe anaphylaxis) correctly registers as 'Critical'.
    """
    prompt_major = """SECTION 1: ORIGIN & CUSTOMER DETAILS
Complaint Reference: QMS-PV-2026-0738
Complaint Source: Oncology Ward Pharmacy
Customer Name: North Valley Medical Center

SECTION 2: PRODUCT & BATCH IDENTIFICATION
Product Name: Methotrexate Injection
Product Strength / Grade: 50 mg/2 mL
Batch / Lot Number: MTX50-H9154
Quantity Affected: Approximately 6 vials
Manufacturing Date: 14-May-2026
Expiry Date: 13-May-2028
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Chennai
Material Type: Finished Pharmaceutical Product

SECTION 3: COMPLAINT DETAILS
Complaint Type: Suspected Product Mix-Up / Labeling Defect
Complaint Date: 12-Sep-2026

Complaint Description:
The oncology ward pharmacy reported that one vial from the batch had a label showing a different strength from the strength expected for the order. The outer carton also showed inconsistent product information. The vial was identified before administration to any patient, and no adverse patient event occurred. The hospital requested immediate batch investigation and replacement stock.

REQUESTED ACTION:
1. Populate all fields into the complaint form accurately.
2. Determine the risk level and regulatory severity for this complaint."""

    res = client.post("/api/copilot/chat", json={
        "user_message": prompt_major,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]
    structured = data["structured_fields"]
    recalc = data["recalculated_analysis"]
    
    assert updates["severity_level"] == "Major"
    assert structured["severity_level"] == "Major"
    assert recalc["risk_assessment"]["severity_level"] == "Major"

    # Save to directory
    save_payload = {
        **updates,
        "raw_input_text": prompt_major
    }
    create_res = client.post("/api/complaints", json=save_payload)
    assert create_res.status_code == 200
    saved_cmp = create_res.json()
    assert saved_cmp["severity_level"] == "Major"

    # Check directory listing with Major filter
    dir_res = client.get("/api/complaints?severity=Major")
    assert dir_res.status_code == 200
    dir_data = dir_res.json()
    assert dir_data["total"] >= 1
    major_ids = [item["complaint_number"] for item in dir_data["items"]]
    assert saved_cmp["complaint_number"] in major_ids

    # Verify Critical situation still classifies as Critical
    prompt_critical = "Patient suffered fatal anaphylaxis after receiving contaminated injection from batch CRIT-999."
    crit_res = client.post("/api/copilot/chat", json={
        "user_message": prompt_critical,
        "current_fields": {}
    })
    assert crit_res.status_code == 200
    crit_data = crit_res.json()
    assert crit_data["updates"]["severity_level"] == "Critical"


def test_copilot_huge_structured_prompt_with_requested_action():
    """
    Verifies that a huge prompt with sections and requested action like:
    '1. Populate all fields into the complaint form accurately'
    extracts all fields directly from the prompt and does NOT get overwritten
    by stale/empty payload extracted_fields.
    """
    huge_prompt = """Please analyze this complaint and update the complaint form with all the details below.

SECTION 1: ORIGIN & CUSTOMER DETAILS

Complaint Reference: QMS-PV-2026-0738
Complaint Source: Oncology Ward Pharmacy
Customer Name: North Valley Medical Center

SECTION 2: PRODUCT & BATCH IDENTIFICATION

Product Name: Methotrexate Injection
Product Strength / Grade: 50 mg/2 mL
Batch / Lot Number: MTX50-H9154
Quantity Affected: Approximately 6 vials
Manufacturing Date: 14-May-2026
Expiry Date: 13-May-2028
Manufacturing Site: Asterion Pharmaceuticals Ltd., Plant 2, Chennai
Material Type: Finished Pharmaceutical Product

SECTION 3: COMPLAINT DETAILS

Complaint Type: Suspected Product Mix-Up / Labeling Defect
Complaint Date: 12-Sep-2026

Complaint Description:
The oncology ward pharmacy reported that one vial from the batch had a label showing a different strength from the strength expected for the order. The outer carton also showed inconsistent product information. The vial was identified before administration and quarantined immediately. No patient was exposed.

REQUESTED ACTION:
1. Populate all fields into the complaint form accurately.
2. Determine the risk level and update severity.
"""
    # Simulate payload containing stale extracted_fields from previous document/action
    stale_extracted = {
        "complaint_source": "Hospital",
        "batch_lot_number": "OLD-999"
    }
    res = client.post("/api/copilot/chat", json={
        "user_message": huge_prompt,
        "extracted_fields": stale_extracted,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "update_form_fields"
    updates = data["updates"]

    # Newly passed prompt fields MUST take precedence over stale extracted_fields
    assert updates["complaint_reference"] == "QMS-PV-2026-0738"
    assert updates["complaint_source"] == "Oncology Ward Pharmacy"
    assert updates["customer_name"] == "North Valley Medical Center"
    assert updates["product_name"] == "Methotrexate Injection"
    assert updates["product_strength"] == "50 mg/2 mL"
    assert updates["batch_lot_number"] == "MTX50-H9154"
    assert updates["batch_lot_number"] != "OLD-999"
    assert updates["affected_quantity"] == "Approximately 6 vials"
    assert updates["manufacturing_date"] == "2026-05-14"
    assert updates["expiry_date"] == "2028-05-13"
    assert updates["manufacturing_site"] == "Asterion Pharmaceuticals Ltd., Plant 2, Chennai"
    assert updates["material_type"] == "Finished Pharmaceutical Product"
    assert updates["complaint_type"] == "Suspected Product Mix-Up / Labeling Defect"
    assert updates["complaint_date"] == "2026-09-12"
    assert "quarantined immediately" in updates["complaint_description"]


def test_copilot_single_line_period_separated():
    """
    Verifies that single-line prompts with period-separated fields properly segment
    and do not lump following fields into the customer_name.
    """
    msg = "Customer: North Valley Medical Center. Product: Methotrexate Injection. Batch: MTX50-H9154. Quantity: Approximately 6 vials."
    res = client.post("/api/copilot/chat", json={
        "user_message": msg,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    updates = data["updates"]
    assert updates["customer_name"] == "North Valley Medical Center"
    assert updates["product_name"] == "Methotrexate Injection"
    assert updates["batch_lot_number"] == "MTX50-H9154"
    assert updates["affected_quantity"] == "Approximately 6 vials"


def test_copilot_conversational_colonless_prompt():
    """
    Verifies that prompts without colons (e.g. 'Fill the complaint form with product name Metformin, batch MET123, customer John, quantity 50 vials')
    extract the stated fields correctly.
    """
    msg = "Fill the complaint form with product name Metformin, batch MET123, customer John, quantity 50 vials"
    res = client.post("/api/copilot/chat", json={
        "user_message": msg,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    updates = data["updates"]
    assert updates["product_name"] == "Metformin"
    assert updates["batch_lot_number"] == "MET123"
    assert updates["customer_name"] == "John"
    assert updates["affected_quantity"] == "50 vials"


def test_copilot_preamble_with_colons():
    """
    Verifies that preambles like 'Please fill the complaint form with following details: ...'
    do not swallow the first key-value pair.
    """
    msg = "Please fill the complaint form with following details: Product Name: Ceftriaxone for Injection, Batch / Lot Number: CFT1G-R4516, Customer: Lakeside Hospital"
    res = client.post("/api/copilot/chat", json={
        "user_message": msg,
        "current_fields": {}
    })
    assert res.status_code == 200
    data = res.json()
    updates = data["updates"]
    assert updates["product_name"] == "Ceftriaxone for Injection"
    assert updates["batch_lot_number"] == "CFT1G-R4516"
    assert updates["customer_name"] == "Lakeside Hospital"


