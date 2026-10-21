from pypdf import PdfReader

from src.services.pdf import render_report_pdf


def test_report_pdf_contains_practice_name_student_name_and_long_accented_text() -> None:
    body = "Informe para Lucía. " + ("La práctica acompaña su evolución. " * 700)
    reader = PdfReader(__import__("io").BytesIO(render_report_pdf(body, "Gabinete Águila")))
    extracted = "\n".join(page.extract_text() or "" for page in reader.pages)

    assert len(reader.pages) > 1
    assert "Gabinete Águila" in extracted
    assert "Lucía" in extracted
    assert "práctica" in extracted
