from __future__ import annotations

from datetime import date

from app.collectors.pdf_collector import extract_facts_from_pdf_text


def test_extracts_aicte_nsp_extension_date_truthfully() -> None:
    sample_official_text = """
    ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
    Sub: Extension of last date for submission of Online Application forms under AICTE Pragati,
    Saksham and Swanath Scholarship schemes (Degree & Diploma) 2026-27 through National
    Scholarship Portal (NSP) has been extended upto 30th November 2026.
    """
    upd = extract_facts_from_pdf_text(sample_official_text, "aicte-pragati-degree")
    assert upd is not None
    assert upd.application_deadline == date(2026, 11, 30)
    assert upd.confidence == "high"


def test_extracts_aicte_saraswati_schedule_truthfully() -> None:
    sample_text = """
    AICTE SARSWATI SCHOLARSHIP SCHEME FOR A/Y 2026-27
    Opening of portal for students (Fresh and Renewal)
    15th October 2026
    Portal to be closed on 28th February 2027
    """
    upd = extract_facts_from_pdf_text(sample_text, "aicte-saraswati-2026-27")
    assert upd is not None
    assert upd.application_start_date == date(2026, 10, 15)
    assert upd.application_deadline == date(2027, 2, 28)
