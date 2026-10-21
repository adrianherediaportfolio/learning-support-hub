from io import BytesIO
from textwrap import wrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def render_report_pdf(body: str, practice_name: str) -> bytes:
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    _, height = A4
    pdf.setTitle(f"Informe de {practice_name}")
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawString(50, height - 55, practice_name)
    pdf.setFont("Helvetica", 10)
    y = height - 90
    for paragraph in body.splitlines():
        for line in wrap(paragraph, 95) or [""]:
            if y < 55:
                pdf.showPage()
                y = height - 55
                pdf.setFont("Helvetica", 10)
            pdf.drawString(50, y, line.encode("latin-1", "replace").decode("latin-1"))
            y -= 16
    pdf.save()
    return output.getvalue()
