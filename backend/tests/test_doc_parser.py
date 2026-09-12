import pytest
from app.services.doc_parser import DocumentParserService

def test_txt_parsing():
    sample_text = "Metformin 500 mg batch MET500-KP4821 broken tablets inside blister pack."
    raw_bytes = sample_text.encode("utf-8")
    extracted = DocumentParserService.extract_text("complaint.txt", raw_bytes)
    assert "Metformin 500 mg" in extracted
    assert "MET500-KP4821" in extracted
