import json
from datetime import date
from decimal import Decimal

from django.http import HttpResponse, JsonResponse

from .models import AuditLog, Employee, Invoice


def parse_json(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def get_actor(request):
    if request.user.is_authenticated:
        return Employee.objects.filter(user=request.user).first()
    return None


def create_audit_log(request, action, target_type, target_id, details=None):
    AuditLog.objects.create(
        actor=get_actor(request),
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        details=details or {},
    )


def next_invoice_number(is_estimate=False):
    prefix = "EST" if is_estimate else "INV"
    year = date.today().year
    latest = (
        Invoice.objects.filter(number__startswith=f"{prefix}-{year}-")
        .order_by("-number")
        .values_list("number", flat=True)
        .first()
    )
    if not latest:
        sequence = 1
    else:
        sequence = int(latest.split("-")[-1]) + 1
    return f"{prefix}-{year}-{sequence:04d}"


def invoice_pdf_response(invoice):
    lines = [
        "%PDF-1.1",
        "1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj",
        "2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj",
        "3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj",
    ]

    text_lines = [
        f"Invoice Number: {invoice.number}",
        f"Client: {invoice.client.name}",
        f"Project: {invoice.project.name}",
        f"Issued: {invoice.issued_date}",
        f"Due: {invoice.due_date}",
        f"Status: {invoice.status}",
        "",
    ]
    for item in invoice.items.all():
        text_lines.append(f"- {item.description}: {item.quantity} x {item.unit_price} = {item.line_total}")
    text_lines.extend(
        [
            "",
            f"Subtotal: {invoice.subtotal}",
            f"Tax: {invoice.tax_amount}",
            f"Total: {invoice.total_amount}",
            f"Paid: {invoice.paid_amount}",
            f"Balance: {invoice.balance_due}",
        ]
    )
    pdf_text = "\\n".join(text_lines).replace("(", "[").replace(")", "]")
    content_stream = f"BT /F1 12 Tf 50 750 Td ({pdf_text}) Tj ET"
    lines.append(f"4 0 obj<</Length {len(content_stream)}>>stream\n{content_stream}\nendstream endobj")
    lines.append("5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj")
    xref_start = sum(len(line) + 1 for line in lines)
    xref = ["xref", "0 6", "0000000000 65535 f "]
    offset = 0
    for line in lines:
        xref.append(f"{offset:010d} 00000 n ")
        offset += len(line) + 1
    trailer = ["trailer<</Size 6/Root 1 0 R>>", "startxref", str(xref_start), "%%EOF"]
    pdf_body = "\n".join(lines + xref + trailer).encode("latin-1", errors="replace")
    response = HttpResponse(pdf_body, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{invoice.number}.pdf"'
    return response


def decimal_from_payload(payload_value, default="0.00"):
    try:
        return Decimal(str(payload_value))
    except Exception:
        return Decimal(default)
