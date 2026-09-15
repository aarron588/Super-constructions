from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .models import (
    AttendanceBillingLink,
    AttendanceLock,
    AttendanceRecord,
    Client,
    Employee,
    Expense,
    Invoice,
    InvoiceItem,
    Payment,
    Project,
)
from .utils import create_audit_log, decimal_from_payload, invoice_pdf_response, json_error, next_invoice_number, parse_json


ROLE_PERMISSIONS = {
    "admin": {"admin", "accountant", "site_manager", "worker"},
    "accountant": {"accountant", "admin"},
    "site_manager": {"site_manager", "admin"},
    "worker": {"worker", "site_manager", "admin"},
}


def _json_success(data=None, status=200):
    return JsonResponse({"ok": True, "data": data or {}}, status=status)


def _parse_date(value, field_name):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid {field_name}, use YYYY-MM-DD")


def _user_role(request):
    if request.user.is_superuser:
        return "admin"
    employee = Employee.objects.filter(user=request.user).first()
    return employee.role if employee else None


def _user_employee(request):
    if request.user.is_superuser:
        return Employee.objects.filter(role=Employee.ROLE_ADMIN).first()
    return Employee.objects.filter(user=request.user).first()


def _require_roles(request, *roles):
    user_role = _user_role(request)
    if not user_role:
        return json_error("User role not configured", 403)
    allowed = set()
    for role in roles:
        allowed.update(ROLE_PERMISSIONS.get(role, {role}))
    if user_role not in allowed:
        return json_error("Insufficient permissions", 403)
    return None


def _month_locked(attendance_date):
    month_start = attendance_date.replace(day=1)
    return AttendanceLock.objects.filter(month=month_start).exists()


def _attendance_dict(record):
    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "project_id": record.project_id,
        "check_in": record.effective_check_in.isoformat(),
        "check_out": record.effective_check_out.isoformat() if record.effective_check_out else None,
        "duration_hours": float(record.duration_hours),
        "status": record.status,
    }


@require_POST
def register(request):
    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")

    bootstrap = User.objects.count() == 0
    if not bootstrap:
        if not request.user.is_authenticated:
            return json_error("Authentication required", 401)
        denied = _require_roles(request, "admin")
        if denied:
            return denied

    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role", Employee.ROLE_WORKER)

    if not username or not password:
        return json_error("username and password are required")
    if role not in dict(Employee.ROLE_CHOICES):
        return json_error("Invalid role")
    if User.objects.filter(username=username).exists():
        return json_error("Username already exists")

    user = User.objects.create_user(
        username=username,
        **{
            "password": password,
            "first_name": payload.get("first_name", ""),
            "last_name": payload.get("last_name", ""),
            "email": payload.get("email", ""),
        },
    )
    employee = Employee.objects.create(
        user=user,
        role=role,
        hourly_rate=decimal_from_payload(payload.get("hourly_rate", "0")),
    )
    create_audit_log(request, "register_user", "employee", employee.id, {"role": role})
    return _json_success({"employee_id": employee.id, "role": employee.role}, status=201)


@require_POST
def login_view(request):
    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    auth_kwargs = {
        "username": payload.get("username"),
        "password": payload.get("password"),
    }
    user = authenticate(request, **auth_kwargs)
    if not user:
        return json_error("Invalid credentials", 401)
    login(request, user)
    return _json_success({"username": user.username, "role": _user_role(request)})


@require_POST
@login_required
def logout_view(request):
    logout(request)
    return _json_success({"message": "Logged out"})


@require_http_methods(["GET", "POST"])
@login_required
def employees(request):
    denied = _require_roles(request, "admin")
    if denied:
        return denied

    if request.method == "GET":
        data = [
            {
                "id": emp.id,
                "username": emp.user.username,
                "name": emp.user.get_full_name(),
                "role": emp.role,
                "hourly_rate": float(emp.hourly_rate),
                "active": emp.is_active,
            }
            for emp in Employee.objects.select_related("user").all()
        ]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    return register(request)


@require_http_methods(["GET", "POST"])
@login_required
def clients(request):
    denied = _require_roles(request, "site_manager")
    if denied:
        return denied

    if request.method == "GET":
        data = [
            {"id": client.id, "name": client.name, "email": client.email, "phone": client.phone}
            for client in Client.objects.all()
        ]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    if not payload.get("name"):
        return json_error("name is required")
    client = Client.objects.create(
        name=payload["name"],
        email=payload.get("email", ""),
        phone=payload.get("phone", ""),
        address=payload.get("address", ""),
    )
    create_audit_log(request, "create_client", "client", client.id)
    return _json_success({"id": client.id}, status=201)


@require_http_methods(["GET", "POST"])
@login_required
def projects(request):
    denied = _require_roles(request, "site_manager")
    if denied:
        return denied

    if request.method == "GET":
        data = [
            {
                "id": project.id,
                "name": project.name,
                "client_id": project.client_id,
                "start_date": project.start_date.isoformat(),
                "end_date": project.end_date.isoformat() if project.end_date else None,
                "active": project.is_active,
            }
            for project in Project.objects.select_related("client").all()
        ]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    if not payload.get("name") or not payload.get("client_id") or not payload.get("start_date"):
        return json_error("name, client_id, start_date are required")
    try:
        start_date = _parse_date(payload["start_date"], "start_date")
        end_date = _parse_date(payload["end_date"], "end_date") if payload.get("end_date") else None
    except ValueError:
        return json_error("Invalid start_date/end_date format, use YYYY-MM-DD")

    project = Project.objects.create(
        name=payload["name"],
        client_id=payload["client_id"],
        description=payload.get("description", ""),
        start_date=start_date,
        end_date=end_date,
    )
    create_audit_log(request, "create_project", "project", project.id)
    return _json_success({"id": project.id}, status=201)


@require_http_methods(["GET", "POST"])
@login_required
def expenses(request):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    if request.method == "GET":
        data = [
            {
                "id": expense.id,
                "project_id": expense.project_id,
                "amount": float(expense.amount),
                "category": expense.category,
                "incurred_on": expense.incurred_on.isoformat(),
            }
            for expense in Expense.objects.all()
        ]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    required = ["project_id", "amount", "category", "incurred_on"]
    if any(field not in payload for field in required):
        return json_error("project_id, amount, category, incurred_on are required")
    try:
        incurred_on = _parse_date(payload["incurred_on"], "incurred_on")
    except ValueError:
        return json_error("Invalid incurred_on format, use YYYY-MM-DD")
    expense = Expense.objects.create(
        project_id=payload["project_id"],
        amount=decimal_from_payload(payload["amount"]),
        category=payload["category"],
        incurred_on=incurred_on,
        notes=payload.get("notes", ""),
    )
    create_audit_log(request, "create_expense", "expense", expense.id)
    return _json_success({"id": expense.id}, status=201)


@require_http_methods(["GET", "POST"])
@login_required
def attendance(request):
    denied = _require_roles(request, "worker")
    if denied:
        return denied

    if request.method == "GET":
        queryset = AttendanceRecord.objects.select_related("employee", "project")
        if _user_role(request) == Employee.ROLE_WORKER:
            queryset = queryset.filter(employee__user=request.user)
        if request.GET.get("employee_id"):
            queryset = queryset.filter(employee_id=request.GET["employee_id"])
        if request.GET.get("project_id"):
            queryset = queryset.filter(project_id=request.GET["project_id"])
        data = [_attendance_dict(record) for record in queryset[:200]]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    project_id = payload.get("project_id")
    if not project_id:
        return json_error("project_id is required")

    employee = _user_employee(request)
    if _user_role(request) != Employee.ROLE_WORKER and payload.get("employee_id"):
        employee = Employee.objects.filter(id=payload["employee_id"]).first() or employee
    if not employee:
        return json_error("Employee mapping required", 400)

    now = timezone.now()
    if _month_locked(now.date()):
        return json_error("Current month attendance is locked", 409)

    record = AttendanceRecord.objects.create(employee=employee, project_id=project_id, check_in=now)
    create_audit_log(request, "attendance_check_in", "attendance_record", record.id)
    return _json_success(_attendance_dict(record), status=201)


@require_POST
@login_required
def attendance_checkout(request, record_id):
    denied = _require_roles(request, "worker")
    if denied:
        return denied

    record = AttendanceRecord.objects.filter(id=record_id).select_related("employee").first()
    if not record:
        return json_error("Attendance record not found", 404)
    if _user_role(request) == Employee.ROLE_WORKER and record.employee.user_id != request.user.id:
        return json_error("Cannot check out another worker", 403)
    if record.check_out:
        return json_error("Already checked out", 409)
    if _month_locked(record.check_in.date()):
        return json_error("Attendance month is locked", 409)

    record.check_out = timezone.now()
    record.save(update_fields=["check_out", "updated_at"])
    create_audit_log(request, "attendance_check_out", "attendance_record", record.id)
    return _json_success(_attendance_dict(record))


@require_POST
@login_required
def attendance_correct(request, record_id):
    denied = _require_roles(request, "site_manager")
    if denied:
        return denied

    record = AttendanceRecord.objects.filter(id=record_id).first()
    if not record:
        return json_error("Attendance record not found", 404)
    if _month_locked(record.check_in.date()):
        return json_error("Attendance month is locked", 409)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    if not payload.get("reason"):
        return json_error("reason is required")

    try:
        if payload.get("check_in"):
            record.corrected_check_in = datetime.fromisoformat(payload["check_in"])
        if payload.get("check_out"):
            record.corrected_check_out = datetime.fromisoformat(payload["check_out"])
    except ValueError:
        return json_error("check_in/check_out must be ISO datetime")

    record.correction_reason = payload["reason"]
    record.status = AttendanceRecord.STATUS_PENDING
    record.approved_by = None
    record.save()
    create_audit_log(request, "attendance_corrected", "attendance_record", record.id, {"reason": payload["reason"]})
    return _json_success(_attendance_dict(record))


@require_POST
@login_required
def attendance_approve(request, record_id):
    denied = _require_roles(request, "site_manager")
    if denied:
        return denied
    record = AttendanceRecord.objects.filter(id=record_id).first()
    if not record:
        return json_error("Attendance record not found", 404)
    if _month_locked(record.check_in.date()):
        return json_error("Attendance month is locked", 409)

    payload = parse_json(request) or {}
    action = payload.get("action", "approve")
    if action not in {"approve", "reject"}:
        return json_error("action must be approve or reject")

    record.status = AttendanceRecord.STATUS_APPROVED if action == "approve" else AttendanceRecord.STATUS_REJECTED
    record.approved_by = _user_employee(request)
    record.save(update_fields=["status", "approved_by", "updated_at"])
    create_audit_log(request, f"attendance_{action}", "attendance_record", record.id)
    return _json_success(_attendance_dict(record))


@require_POST
@login_required
def attendance_lock(request):
    denied = _require_roles(request, "admin")
    if denied:
        return denied

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    if not payload.get("month"):
        return json_error("month is required in YYYY-MM format")

    try:
        month_date = datetime.strptime(payload["month"], "%Y-%m").date().replace(day=1)
    except ValueError:
        return json_error("month is required in YYYY-MM format")

    if AttendanceLock.objects.filter(month=month_date).exists():
        return json_error("month already locked", 409)

    lock = AttendanceLock.objects.create(month=month_date, locked_by=_user_employee(request))
    create_audit_log(request, "attendance_month_locked", "attendance_lock", lock.id, {"month": payload["month"]})
    return _json_success({"id": lock.id, "month": lock.month.isoformat()}, status=201)


@require_http_methods(["GET", "POST"])
@login_required
def invoices(request):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    if request.method == "GET":
        today = date.today()
        queryset = Invoice.objects.select_related("client", "project").all()
        for invoice in queryset:
            if invoice.balance_due > 0 and invoice.due_date < today and invoice.status not in {Invoice.STATUS_PAID, Invoice.STATUS_OVERDUE}:
                invoice.status = Invoice.STATUS_OVERDUE
                invoice.save(update_fields=["status", "updated_at"])
        data = [
            {
                "id": invoice.id,
                "number": invoice.number,
                "client": invoice.client.name,
                "project": invoice.project.name,
                "issued_date": invoice.issued_date.isoformat(),
                "due_date": invoice.due_date.isoformat(),
                "status": invoice.status,
                "is_estimate": invoice.is_estimate,
                "subtotal": float(invoice.subtotal),
                "tax": float(invoice.tax_amount),
                "total": float(invoice.total_amount),
                "paid": float(invoice.paid_amount),
                "balance": float(invoice.balance_due),
            }
            for invoice in queryset
        ]
        return _json_success(data)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")

    required = ["client_id", "project_id", "due_date"]
    if any(field not in payload for field in required):
        return json_error("client_id, project_id, due_date are required")

    try:
        due_date = _parse_date(payload["due_date"], "due_date")
    except ValueError:
        return json_error("Invalid due_date format, use YYYY-MM-DD")

    is_estimate = bool(payload.get("is_estimate", False))
    invoice = Invoice.objects.create(
        number=next_invoice_number(is_estimate),
        client_id=payload["client_id"],
        project_id=payload["project_id"],
        due_date=due_date,
        is_estimate=is_estimate,
        tax_rate=decimal_from_payload(payload.get("tax_rate", "0")),
        notes=payload.get("notes", ""),
    )
    create_audit_log(request, "create_invoice", "invoice", invoice.id)
    return _json_success({"id": invoice.id, "number": invoice.number}, status=201)


@require_POST
@login_required
def invoice_generate_from_attendance(request):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")

    required = ["client_id", "project_id", "start_date", "end_date", "due_days"]
    if any(field not in payload for field in required):
        return json_error("client_id, project_id, start_date, end_date, due_days are required")

    try:
        start_date = _parse_date(payload["start_date"], "start_date")
        end_date = _parse_date(payload["end_date"], "end_date")
    except ValueError:
        return json_error("Invalid start_date/end_date format, use YYYY-MM-DD")

    due_date = date.today() + timedelta(days=int(payload["due_days"]))
    is_estimate = bool(payload.get("is_estimate", False))

    invoice = Invoice.objects.create(
        number=next_invoice_number(is_estimate),
        client_id=payload["client_id"],
        project_id=payload["project_id"],
        due_date=due_date,
        is_estimate=is_estimate,
        tax_rate=decimal_from_payload(payload.get("tax_rate", "0")),
        notes=f"Generated from attendance period {start_date} to {end_date}",
    )

    attendance_rows = AttendanceRecord.objects.filter(
        project_id=payload["project_id"],
        status=AttendanceRecord.STATUS_APPROVED,
        check_in__date__gte=start_date,
        check_in__date__lte=end_date,
        check_out__isnull=False,
    ).select_related("employee", "employee__user")

    created_items = 0
    for record in attendance_rows:
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description=f"Labor - {record.employee.user.get_full_name() or record.employee.user.username}",
            quantity=record.duration_hours,
            unit_price=record.employee.hourly_rate,
            line_total=0,
        )
        AttendanceBillingLink.objects.get_or_create(attendance_record=record, defaults={"invoice_item": item})
        created_items += 1

    create_audit_log(
        request,
        "generate_invoice_from_attendance",
        "invoice",
        invoice.id,
        {"line_items": created_items, "period": f"{start_date} to {end_date}"},
    )
    return _json_success({"invoice_id": invoice.id, "number": invoice.number, "line_items": created_items}, status=201)


@require_POST
@login_required
def invoice_add_item(request, invoice_id):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        return json_error("Invoice not found", 404)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")

    if not payload.get("description"):
        return json_error("description is required")

    quantity = decimal_from_payload(payload.get("quantity", "1"), "1")
    unit_price = decimal_from_payload(payload.get("unit_price", "0"), "0")

    item = InvoiceItem.objects.create(
        invoice=invoice,
        description=payload["description"],
        quantity=quantity,
        unit_price=unit_price,
        line_total=0,
    )
    create_audit_log(request, "add_invoice_item", "invoice_item", item.id)
    return _json_success({"id": item.id, "line_total": float(item.line_total)}, status=201)


@require_POST
@login_required
def invoice_mark_sent(request, invoice_id):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        return json_error("Invoice not found", 404)
    invoice.status = Invoice.STATUS_SENT
    invoice.save(update_fields=["status", "updated_at"])
    create_audit_log(request, "mark_invoice_sent", "invoice", invoice.id)
    return _json_success({"status": invoice.status})


@require_POST
@login_required
def invoice_add_payment(request, invoice_id):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    invoice = Invoice.objects.filter(id=invoice_id).first()
    if not invoice:
        return json_error("Invoice not found", 404)

    payload = parse_json(request)
    if payload is None:
        return json_error("Invalid JSON")
    if "amount" not in payload:
        return json_error("amount is required")

    amount = decimal_from_payload(payload["amount"])
    if amount <= 0:
        return json_error("amount must be greater than zero")

    payment = Payment.objects.create(
        invoice=invoice,
        amount=amount,
        paid_on=_parse_date(payload["paid_on"], "paid_on") if payload.get("paid_on") else date.today(),
        method=payload.get("method", ""),
        reference=payload.get("reference", ""),
    )

    invoice.status = Invoice.STATUS_PAID if invoice.balance_due <= 0 else Invoice.STATUS_PARTIAL
    invoice.save(update_fields=["status", "updated_at"])

    create_audit_log(request, "add_payment", "payment", payment.id)
    return _json_success({"payment_id": payment.id, "invoice_status": invoice.status}, status=201)


@require_GET
@login_required
def invoice_pdf(request, invoice_id):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied
    invoice = Invoice.objects.filter(id=invoice_id).prefetch_related("items").select_related("client", "project").first()
    if not invoice:
        return json_error("Invoice not found", 404)
    return invoice_pdf_response(invoice)


@require_GET
@login_required
def invoice_reminders(request):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied
    overdue = Invoice.objects.filter(
        Q(status=Invoice.STATUS_SENT) | Q(status=Invoice.STATUS_PARTIAL) | Q(status=Invoice.STATUS_OVERDUE),
        due_date__lt=date.today(),
    ).select_related("client")

    reminders = []
    for invoice in overdue:
        invoice.status = Invoice.STATUS_OVERDUE
        invoice.save(update_fields=["status", "updated_at"])
        reminders.append(
            {
                "invoice_id": invoice.id,
                "number": invoice.number,
                "client": invoice.client.name,
                "due_date": invoice.due_date.isoformat(),
                "balance_due": float(invoice.balance_due),
                "message": f"Reminder: Invoice {invoice.number} is overdue.",
            }
        )
    return _json_success(reminders)


@require_GET
@login_required
def dashboard(request):
    denied = _require_roles(request, "worker")
    if denied:
        return denied

    start_month = date.today().replace(day=1)
    approved = AttendanceRecord.objects.filter(
        status=AttendanceRecord.STATUS_APPROVED,
        check_in__date__gte=start_month,
        check_out__isnull=False,
    )
    monthly_hours = sum(float(record.duration_hours) for record in approved)

    data = {
        "employees": Employee.objects.filter(is_active=True).count(),
        "active_projects": Project.objects.filter(is_active=True).count(),
        "pending_attendance": AttendanceRecord.objects.filter(status=AttendanceRecord.STATUS_PENDING).count(),
        "monthly_hours": monthly_hours,
        "monthly_expenses": float(
            Expense.objects.filter(incurred_on__gte=start_month).aggregate(total=Sum("amount"))["total"] or 0
        ),
        "open_invoice_balance": float(
            sum(
                [
                    invoice.balance_due
                    for invoice in Invoice.objects.exclude(status=Invoice.STATUS_PAID)
                ],
                start=Decimal("0.00"),
            )
        ),
    }
    return _json_success(data)


@require_GET
@login_required
def reports_summary(request):
    denied = _require_roles(request, "accountant")
    if denied:
        return denied

    try:
        start_date = _parse_date(request.GET.get("start_date"), "start_date") if request.GET.get("start_date") else None
        end_date = _parse_date(request.GET.get("end_date"), "end_date") if request.GET.get("end_date") else None
    except ValueError:
        return json_error("Invalid report date range, use YYYY-MM-DD")

    attendance_qs = AttendanceRecord.objects.filter(status=AttendanceRecord.STATUS_APPROVED, check_out__isnull=False)
    expense_qs = Expense.objects.all()
    invoice_qs = Invoice.objects.all()

    if start_date:
        attendance_qs = attendance_qs.filter(check_in__date__gte=start_date)
        expense_qs = expense_qs.filter(incurred_on__gte=start_date)
        invoice_qs = invoice_qs.filter(issued_date__gte=start_date)
    if end_date:
        attendance_qs = attendance_qs.filter(check_in__date__lte=end_date)
        expense_qs = expense_qs.filter(incurred_on__lte=end_date)
        invoice_qs = invoice_qs.filter(issued_date__lte=end_date)

    total_hours = sum(float(record.duration_hours) for record in attendance_qs)
    total_expenses = expense_qs.aggregate(total=Sum("amount"))["total"] or 0

    total_invoice_amount = sum(invoice.total_amount for invoice in invoice_qs)
    total_collected = sum(invoice.paid_amount for invoice in invoice_qs)

    return _json_success(
        {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None,
            },
            "attendance_hours": total_hours,
            "expenses": float(total_expenses),
            "invoiced": float(total_invoice_amount),
            "collected": float(total_collected),
            "outstanding": float(total_invoice_amount - total_collected),
        }
    )
