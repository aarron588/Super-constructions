import json
import math
import re
from datetime import date, timedelta
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CUSTOMERS_FILE = ROOT / "data" / "customers.json"
PROJECTS_FILE = ROOT / "data" / "projects.json"
ESTIMATES_FILE = ROOT / "data" / "estimates.json"
INVOICES_FILE = ROOT / "data" / "invoices.json"
MATERIALS_FILE = ROOT / "data" / "materials.json"
EXPENSES_FILE = ROOT / "data" / "expenses.json"
SUPPLIERS_FILE = ROOT / "data" / "suppliers.json"
EMPLOYEES_FILE = ROOT / "data" / "employees.json"
PROGRESS_FILE = ROOT / "data" / "progress.json"
PAYMENTS_FILE = ROOT / "data" / "payments.json"
PROJECTS_FILE.parent.mkdir(exist_ok=True)


def read_projects():
    if not PROJECTS_FILE.exists():
        return []
    content = PROJECTS_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_projects(projects):
    standalone_projects = [
        {key: value for key, value in project.items() if key not in {"customer_id", "customer_name"}}
        for project in projects
    ]
    PROJECTS_FILE.write_text(json.dumps(standalone_projects, indent=2), encoding="utf-8")


def migrate_projects_to_standalone():
    projects = read_projects()
    if not PROJECTS_FILE.exists() and CUSTOMERS_FILE.exists():
        content = CUSTOMERS_FILE.read_text(encoding="utf-8")
        customers = json.loads(content) if content.strip() else []
        for customer in customers:
            for project in customer.get("projects", []):
                projects.append(project)
    write_projects(projects)


migrate_projects_to_standalone()


def parse_json_request(handler):
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length <= 0 or content_length > 1024 * 1024:
        raise ValueError("Request must be between 1 byte and 1 MB")
    return json.loads(handler.rfile.read(content_length).decode("utf-8"))


def validate_project(project):
    if not isinstance(project, dict):
        raise ValueError("Project details must be an object")

    required = ("name", "location", "start_date", "expected_completion_date")
    if any(not str(project.get(field, "")).strip() for field in required):
        raise ValueError("Project name, location and dates are required")
    project.pop("customer_id", None)
    project.pop("customer_name", None)

    try:
        start = date.fromisoformat(project["start_date"])
        completion = date.fromisoformat(project["expected_completion_date"])
    except (TypeError, ValueError):
        raise ValueError("Enter valid project dates")
    if completion < start:
        raise ValueError("Expected completion date must be on or after the start date")

    if project.get("status", "Planning") not in {"Planning", "In progress", "On hold", "Completed"}:
        raise ValueError("Select a valid project status")
    try:
        progress = int(project.get("progress", 0))
        budget = float(project.get("budget", 0))
        contract_amount = float(project.get("contract_amount", 0))
    except (TypeError, ValueError):
        raise ValueError("Progress and amounts must be valid numbers")
    if progress < 0 or progress > 100:
        raise ValueError("Progress must be between 0 and 100")
    if not math.isfinite(budget) or not math.isfinite(contract_amount) or budget < 0 or contract_amount < 0:
        raise ValueError("Budget and contract amount must be zero or greater")

    project["progress"] = progress
    project["budget"] = budget
    project["contract_amount"] = contract_amount
    project["status"] = project.get("status", "Planning")
    project["supervisor"] = str(project.get("supervisor", "")).strip()


def next_project_id():
    numbers = [
        int(item["id"].split("-")[-1])
        for item in read_projects()
        if re.fullmatch(r"PRJ-\d+", item.get("id", ""))
    ]
    return f"PRJ-{max(numbers, default=0) + 1:03d}"


def read_estimates():
    if not ESTIMATES_FILE.exists():
        return []
    content = ESTIMATES_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_estimates(estimates):
    ESTIMATES_FILE.write_text(json.dumps(estimates, indent=2), encoding="utf-8")


def read_invoices():
    if not INVOICES_FILE.exists():
        return []
    content = INVOICES_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_invoices(invoices):
    INVOICES_FILE.write_text(json.dumps(invoices, indent=2), encoding="utf-8")


def read_materials():
    if not MATERIALS_FILE.exists():
        return []
    content = MATERIALS_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_materials(materials):
    MATERIALS_FILE.write_text(json.dumps(materials, indent=2), encoding="utf-8")


def read_expenses():
    if not EXPENSES_FILE.exists():
        return []
    content = EXPENSES_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_expenses(expenses):
    EXPENSES_FILE.write_text(json.dumps(expenses, indent=2), encoding="utf-8")


def read_suppliers():
    if not SUPPLIERS_FILE.exists():
        return []
    content = SUPPLIERS_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_suppliers(suppliers):
    SUPPLIERS_FILE.write_text(json.dumps(suppliers, indent=2), encoding="utf-8")


def read_employees():
    if not EMPLOYEES_FILE.exists():
        return []
    content = EMPLOYEES_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_employees(employees):
    EMPLOYEES_FILE.write_text(json.dumps(employees, indent=2), encoding="utf-8")


def read_progress():
    if not PROGRESS_FILE.exists():
        return []
    content = PROGRESS_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_progress(entries):
    PROGRESS_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def read_payments():
    if not PAYMENTS_FILE.exists():
        return []
    content = PAYMENTS_FILE.read_text(encoding="utf-8")
    return json.loads(content) if content.strip() else []


def write_payments(payments):
    PAYMENTS_FILE.write_text(json.dumps(payments, indent=2), encoding="utf-8")


def validate_estimate(estimate):
    if not isinstance(estimate, dict):
        raise ValueError("Estimate details must be an object")

    required = ("project_id", "valid_until")
    if any(not str(estimate.get(field, "")).strip() for field in required):
        raise ValueError("Select a project and validity date")
    project = next((item for item in read_projects() if item.get("id") == estimate["project_id"]), None)
    if not project:
        raise ValueError("Select an existing project")

    try:
        date.fromisoformat(estimate["valid_until"])
    except (TypeError, ValueError):
        raise ValueError("Enter a valid estimate validity date")

    items = estimate.get("items")
    allowed_categories = {"Material", "Labour", "Equipment", "Transport", "Other"}
    if not isinstance(items, list) or not items or len(items) > 100:
        raise ValueError("Add between 1 and 100 estimate items")

    subtotal = 0
    validated_items = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each estimate item must be an object")
        description = str(item.get("description", "")).strip()
        category = item.get("category")
        if not description or category not in allowed_categories:
            raise ValueError("Each item needs a description and valid category")
        try:
            quantity = float(item.get("quantity", 0))
            unit_price = float(item.get("unit_price", 0))
        except (TypeError, ValueError):
            raise ValueError("Item quantities and rates must be valid numbers")
        if not math.isfinite(quantity) or not math.isfinite(unit_price) or quantity <= 0 or unit_price < 0:
            raise ValueError("Item quantities must be greater than zero and rates cannot be negative")
        amount = quantity * unit_price
        if not math.isfinite(amount):
            raise ValueError("Estimate item amount is too large")
        amount = round(amount, 2)
        subtotal += amount
        if not math.isfinite(subtotal):
            raise ValueError("Estimate subtotal is too large")
        validated_items.append({
            "description": description,
            "category": category,
            "quantity": quantity,
            "unit": str(item.get("unit", "unit")).strip() or "unit",
            "unit_price": unit_price,
            "amount": amount,
        })

    try:
        discount_percent = float(estimate.get("discount_percent", 0))
        gst_percent = float(estimate.get("gst_percent", 0))
    except (TypeError, ValueError):
        raise ValueError("Discount and GST must be valid percentages")
    if (not math.isfinite(discount_percent) or not math.isfinite(gst_percent)
            or discount_percent < 0 or discount_percent > 100
            or gst_percent < 0 or gst_percent > 100):
        raise ValueError("Discount and GST must be between 0 and 100 percent")

    discount_amount = round(subtotal * (discount_percent / 100), 2)
    taxable_amount = subtotal - discount_amount
    gst_amount = round(taxable_amount * (gst_percent / 100), 2)
    if not math.isfinite(gst_amount) or not math.isfinite(taxable_amount + gst_amount):
        raise ValueError("Estimate total is too large")
    estimate.update({
        "project_name": project["name"],
        "items": validated_items,
        "discount_percent": discount_percent,
        "gst_percent": gst_percent,
        "subtotal": round(subtotal, 2),
        "discount_amount": discount_amount,
        "gst_amount": gst_amount,
        "total": round(taxable_amount + gst_amount, 2),
        "notes": str(estimate.get("notes", "")).strip(),
        "status": estimate.get("status", "Draft"),
    })
    if estimate["status"] not in {"Draft", "Sent", "Accepted", "Rejected"}:
        raise ValueError("Select a valid estimate status")


def next_estimate_id():
    numbers = [
        int(item["id"].split("-")[-1])
        for item in read_estimates()
        if re.fullmatch(r"EST-\d+", item.get("id", ""))
    ]
    return f"EST-{max(numbers, default=0) + 1:03d}"


def next_invoice_id():
    numbers = [
        int(item["id"].split("-")[-1])
        for item in read_invoices()
        if re.fullmatch(r"INV-\d+", item.get("id", ""))
    ]
    return f"INV-{max(numbers, default=0) + 1:03d}"


def validate_invoice_payment(invoice, payment):
    if not isinstance(payment, dict):
        raise ValueError("Payment details must be an object")
    try:
        amount = float(payment.get("amount", 0))
    except (TypeError, ValueError):
        raise ValueError("Payment amount must be a valid number")
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Payment amount must be greater than zero")
    amount = round(amount, 2)
    balance = round(float(invoice.get("balance", 0)), 2)
    if amount > balance:
        raise ValueError("Payment amount cannot exceed the remaining balance")

    method = payment.get("method")
    if method not in {"Cash", "UPI", "Bank transfer", "Other"}:
        raise ValueError("Select a valid payment method")
    payment_date = str(payment.get("date", "")).strip()
    try:
        date.fromisoformat(payment_date)
    except ValueError:
        raise ValueError("Enter a valid payment date")

    entry = {
        "amount": amount,
        "method": method,
        "date": payment_date,
    }
    payments = invoice.setdefault("payments", [])
    payments.append(entry)
    invoice["paid_amount"] = round(float(invoice.get("paid_amount", 0)) + amount, 2)
    invoice["balance"] = round(float(invoice["total"]) - invoice["paid_amount"], 2)
    invoice["status"] = "Paid" if invoice["balance"] == 0 else "Partially paid"


def validate_material(material):
    if not isinstance(material, dict):
        raise ValueError("Material details must be an object")

    name = str(material.get("name", "")).strip()
    category = material.get("category")
    unit = str(material.get("unit", "unit")).strip()
    if not name or len(name) > 120 or not isinstance(category, str) or category not in {
        "Cement", "Steel", "Sand", "Bricks", "Gravel", "Paint", "Tiles", "Other"
    } or not unit or len(unit) > 24:
        raise ValueError("Enter a material name, valid category, and unit")

    try:
        purchase_price = float(material.get("purchase_price", 0))
        minimum_stock = float(material.get("minimum_stock", 0))
    except (TypeError, ValueError):
        raise ValueError("Purchase price and minimum stock must be valid numbers")
    if (not math.isfinite(purchase_price) or not math.isfinite(minimum_stock)
            or purchase_price < 0 or purchase_price > 1_000_000_000_000
            or minimum_stock < 0 or minimum_stock > 1_000_000_000):
        raise ValueError("Purchase price and minimum stock must be within supported limits")

    supplier_name = str(material.get("supplier_name", "")).strip()
    if len(supplier_name) > 120:
        raise ValueError("Supplier name must be 120 characters or fewer")

    material.update({
        "name": name,
        "category": category,
        "unit": unit,
        "purchase_price": round(purchase_price, 2),
        "minimum_stock": round(minimum_stock, 3),
        "supplier_name": supplier_name,
    })


def next_material_id():
    numbers = [
        int(item["id"].split("-")[-1])
        for item in read_materials()
        if re.fullmatch(r"MAT-\d+", item.get("id", ""))
    ]
    return f"MAT-{max(numbers, default=0) + 1:03d}"


def validate_stock_movement(material, movement):
    if not isinstance(movement, dict):
        raise ValueError("Stock movement details must be an object")
    movement_type = movement.get("type")
    if not isinstance(movement_type, str) or movement_type not in {"Stock in", "Stock out"}:
        raise ValueError("Select Stock in or Stock out")

    try:
        quantity = float(movement.get("quantity", 0))
    except (TypeError, ValueError):
        raise ValueError("Movement quantity must be a valid number")
    if not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("Movement quantity must be greater than zero")
    quantity = round(quantity, 3)
    if quantity <= 0:
        raise ValueError("Movement quantity must be at least 0.001")
    if movement_type == "Stock out" and quantity > float(material.get("quantity", 0)):
        raise ValueError("Stock out quantity cannot exceed the available quantity")

    movement_date = str(movement.get("date", "")).strip()
    try:
        date.fromisoformat(movement_date)
    except (TypeError, ValueError):
        raise ValueError("Enter a valid movement date")

    project_id = str(movement.get("project_id", "")).strip()
    project = None
    if project_id:
        if movement_type != "Stock out":
            raise ValueError("Projects can only be assigned to stock out movements")
        project = next((item for item in read_projects() if item.get("id") == project_id), None)
        if not project:
            raise ValueError("Select an existing project")

    supplier_name = str(movement.get("supplier_name", "")).strip()
    if movement_type == "Stock in":
        supplier_name = supplier_name or material.get("supplier_name", "")
        try:
            unit_price = float(movement.get("unit_price", material.get("purchase_price", 0)))
        except (TypeError, ValueError):
            raise ValueError("Unit purchase price must be a valid number")
        if not math.isfinite(unit_price) or unit_price < 0 or unit_price > 1_000_000_000_000:
            raise ValueError("Unit purchase price must be within supported limits")
        unit_price = round(unit_price, 2)
    else:
        unit_price = round(float(material.get("purchase_price", 0)), 2)

    note = str(movement.get("note", "")).strip()
    if len(note) > 500:
        raise ValueError("Movement notes must be 500 characters or fewer")

    entry = {
        "id": f"{material['id']}-MOV-{len(material.get('movements', [])) + 1:03d}",
        "type": movement_type,
        "quantity": quantity,
        "date": movement_date,
        "supplier_name": supplier_name if movement_type == "Stock in" else "",
        "project_id": project["id"] if project else "",
        "project_name": project["name"] if project else "",
        "unit_price": unit_price,
        "note": note,
    }

    current_quantity = round(float(material.get("quantity", 0)), 3)
    if movement_type == "Stock in":
        new_quantity = round(current_quantity + quantity, 3)
        if new_quantity > 1_000_000_000:
            raise ValueError("Available stock cannot exceed 1,000,000,000 units")
        if new_quantity > 0:
            total_cost = current_quantity * float(material.get("purchase_price", 0)) + quantity * unit_price
            if not math.isfinite(total_cost):
                raise ValueError("Stock value is too large")
            material["purchase_price"] = round(total_cost / new_quantity, 2)
        material["quantity"] = new_quantity
        if supplier_name:
            material["supplier_name"] = supplier_name
    else:
        material["quantity"] = round(current_quantity - quantity, 3)
    material.setdefault("movements", []).append(entry)


def validate_expense(expense):
    if not isinstance(expense, dict):
        raise ValueError("Expense details must be an object")

    description = str(expense.get("description", "")).strip()
    category = expense.get("category")
    allowed_categories = {
        "Material", "Labour", "Transportation", "Equipment",
        "Electricity", "Maintenance", "Other",
    }
    if not description or len(description) > 160 or not isinstance(category, str) or category not in allowed_categories:
        raise ValueError("Enter a description and valid expense category")

    expense_date = str(expense.get("date", "")).strip()
    try:
        date.fromisoformat(expense_date)
    except (TypeError, ValueError):
        raise ValueError("Enter a valid expense date")

    try:
        amount = float(expense.get("amount", 0))
    except (TypeError, ValueError):
        raise ValueError("Expense amount must be a valid number")
    if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000_000_000:
        raise ValueError("Expense amount must be greater than zero and within supported limits")
    amount = round(amount, 2)
    if amount <= 0:
        raise ValueError("Expense amount must be at least 0.01")

    project_id = str(expense.get("project_id", "")).strip()
    project = None
    if project_id:
        project = next((item for item in read_projects() if item.get("id") == project_id), None)
        if not project:
            raise ValueError("Select an existing project")

    payment_method = expense.get("payment_method")
    if not isinstance(payment_method, str) or payment_method not in {"Cash", "UPI", "Bank transfer", "Other"}:
        raise ValueError("Select a valid payment method")

    vendor = str(expense.get("vendor", "")).strip()
    notes = str(expense.get("notes", "")).strip()
    if len(vendor) > 120 or len(notes) > 500:
        raise ValueError("Vendor name or notes exceed the allowed length")

    expense.update({
        "description": description,
        "category": category,
        "date": expense_date,
        "amount": amount,
        "project_id": project["id"] if project else "",
        "project_name": project["name"] if project else "",
        "payment_method": payment_method,
        "vendor": vendor,
        "notes": notes,
    })


def next_expense_id():
    numbers = [
        int(item["id"].split("-")[-1])
        for item in read_expenses()
        if re.fullmatch(r"EXP-\d+", item.get("id", ""))
    ]
    return f"EXP-{max(numbers, default=0) + 1:03d}"


def next_id(records, prefix):
    numbers = [
        int(item["id"].split("-")[-1])
        for item in records
        if re.fullmatch(r"{}-\d+".format(re.escape(prefix)), item.get("id", ""))
    ]
    return "{}-{:03d}".format(prefix, max(numbers, default=0) + 1)


def validate_supplier(supplier):
    if not isinstance(supplier, dict):
        raise ValueError("Supplier details must be an object")
    name = str(supplier.get("name", "")).strip()
    contact_number = str(supplier.get("contact_number", "")).strip()
    email = str(supplier.get("email", "")).strip()
    address = str(supplier.get("address", "")).strip()
    gst_number = str(supplier.get("gst_number", "")).strip().upper()
    materials = supplier.get("materials_supplied", [])
    if isinstance(materials, str):
        materials = materials.splitlines()
    if not isinstance(materials, list):
        raise ValueError("Materials supplied must be a list")
    materials = list(dict.fromkeys(str(item).strip() for item in materials if str(item).strip()))
    if (not name or len(name) > 120 or len(contact_number) > 30 or len(email) > 120
            or len(address) > 300 or len(gst_number) > 20 or len(materials) > 30
            or any(len(item) > 80 for item in materials)):
        raise ValueError("Supplier details exceed the allowed limits")
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("Enter a valid supplier email address")
    try:
        payment_terms_days = int(supplier.get("payment_terms_days", 0))
    except (TypeError, ValueError):
        raise ValueError("Payment terms must be a whole number of days")
    if payment_terms_days < 0 or payment_terms_days > 365:
        raise ValueError("Payment terms must be between 0 and 365 days")
    supplier.update({
        "name": name,
        "contact_number": contact_number,
        "email": email,
        "address": address,
        "gst_number": gst_number,
        "materials_supplied": materials,
        "payment_terms_days": payment_terms_days,
    })


def validate_supplier_bill(bill):
    if not isinstance(bill, dict):
        raise ValueError("Supplier bill details must be an object")
    description = str(bill.get("description", "")).strip()
    invoice_number = str(bill.get("invoice_number", "")).strip()
    bill_date = str(bill.get("date", "")).strip()
    due_date = str(bill.get("due_date", "")).strip()
    try:
        date.fromisoformat(bill_date)
        date.fromisoformat(due_date)
    except ValueError:
        raise ValueError("Enter valid bill and due dates")
    if date.fromisoformat(due_date) < date.fromisoformat(bill_date):
        raise ValueError("Bill due date cannot be before its issue date")
    if not description or len(description) > 160 or len(invoice_number) > 80:
        raise ValueError("Enter a bill description and a valid invoice number")
    try:
        amount = float(bill.get("amount", 0))
    except (TypeError, ValueError):
        raise ValueError("Bill amount must be a valid number")
    if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000_000_000:
        raise ValueError("Bill amount must be greater than zero and within supported limits")
    amount = round(amount, 2)
    if amount <= 0:
        raise ValueError("Bill amount must be at least 0.01")
    project_id = str(bill.get("project_id", "")).strip()
    project = next((item for item in read_projects() if item.get("id") == project_id), None) if project_id else None
    if project_id and not project:
        raise ValueError("Select an existing project")
    bill.update({
        "description": description,
        "invoice_number": invoice_number,
        "date": bill_date,
        "due_date": due_date,
        "amount": amount,
        "project_id": project["id"] if project else "",
        "project_name": project["name"] if project else "",
        "paid_amount": 0,
        "payments": [],
    })


def validate_employee(employee):
    if not isinstance(employee, dict):
        raise ValueError("Employee details must be an object")
    name = str(employee.get("name", "")).strip()
    phone = str(employee.get("phone", "")).strip()
    role = str(employee.get("role", "")).strip()
    joined_on = str(employee.get("joined_on", "")).strip()
    status = employee.get("status", "Active")
    try:
        date.fromisoformat(joined_on)
        daily_wage = float(employee.get("daily_wage", 0))
    except (TypeError, ValueError):
        raise ValueError("Enter a valid joining date and daily wage")
    if (not name or len(name) > 120 or not role or len(role) > 80 or len(phone) > 30
            or not math.isfinite(daily_wage) or daily_wage <= 0 or daily_wage > 1_000_000_000):
        raise ValueError("Enter valid employee details and a positive daily wage")
    if not isinstance(status, str) or status not in {"Active", "Inactive"}:
        raise ValueError("Select Active or Inactive status")
    daily_wage = round(daily_wage, 2)
    if daily_wage <= 0:
        raise ValueError("Daily wage must be at least 0.01")
    employee.update({
        "name": name,
        "phone": phone,
        "role": role,
        "joined_on": joined_on,
        "daily_wage": daily_wage,
        "status": status,
    })


def validate_attendance(entry):
    if not isinstance(entry, dict):
        raise ValueError("Attendance details must be an object")
    attendance_date = str(entry.get("date", "")).strip()
    try:
        date.fromisoformat(attendance_date)
    except ValueError:
        raise ValueError("Enter a valid attendance date")
    status = entry.get("status")
    if not isinstance(status, str) or status not in {"Present", "Half day", "Absent"}:
        raise ValueError("Select Present, Half day, or Absent")
    project_id = str(entry.get("project_id", "")).strip()
    project = next((item for item in read_projects() if item.get("id") == project_id), None) if project_id else None
    if project_id and not project:
        raise ValueError("Select an existing project")
    notes = str(entry.get("notes", "")).strip()
    if len(notes) > 300:
        raise ValueError("Attendance notes must be 300 characters or fewer")
    entry.update({
        "date": attendance_date,
        "status": status,
        "project_id": project["id"] if project else "",
        "project_name": project["name"] if project else "",
        "notes": notes,
    })


def payroll_summary(employee, month):
    attendance = [entry for entry in employee.get("attendance", []) if entry.get("date", "").startswith(month)]
    units = sum(1 if entry.get("status") == "Present" else 0.5 if entry.get("status") == "Half day" else 0 for entry in attendance)
    earned = round(sum(
        (1 if entry.get("status") == "Present" else 0.5 if entry.get("status") == "Half day" else 0)
        * float(entry.get("daily_wage", employee.get("daily_wage", 0)))
        for entry in attendance
    ), 2)
    payments = [payment for payment in employee.get("salary_payments", []) if payment.get("month") == month]
    paid = round(sum(float(payment.get("amount", 0)) for payment in payments), 2)
    return {
        "attendance_days": units,
        "earned": earned,
        "paid": paid,
        "balance": max(0, round(earned - paid, 2)),
    }


def apply_bill_payment(bill, payment):
    try:
        amount = round(float(payment.get("amount", 0)), 2)
    except (TypeError, ValueError):
        raise ValueError("Payment amount must be a valid number")
    balance = round(float(bill.get("amount", 0)) - float(bill.get("paid_amount", 0)), 2)
    if not math.isfinite(amount) or amount <= 0 or amount > balance:
        raise ValueError("Payment amount must be positive and cannot exceed the bill balance")
    method = payment.get("method")
    if not isinstance(method, str) or method not in {"Cash", "UPI", "Bank transfer", "Other"}:
        raise ValueError("Select a valid payment method")
    payment_date = str(payment.get("date", "")).strip()
    try:
        date.fromisoformat(payment_date)
    except ValueError:
        raise ValueError("Enter a valid payment date")
    record = {
        "id": next_id(bill.get("payments", []), "BILLPAY"),
        "date": payment_date,
        "amount": amount,
        "method": method,
    }
    bill.setdefault("payments", []).append(record)
    bill["paid_amount"] = round(float(bill.get("paid_amount", 0)) + amount, 2)
    return record, round(float(bill["amount"]) - float(bill["paid_amount"]), 2)


def apply_salary_payment(employee, payment):
    month = str(payment.get("month", "")).strip()
    try:
        date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError("Select a valid payroll month")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Select a valid payroll month")
    summary = payroll_summary(employee, month)
    try:
        amount = round(float(payment.get("amount", 0)), 2)
    except (TypeError, ValueError):
        raise ValueError("Salary payment amount must be a valid number")
    if not math.isfinite(amount) or amount <= 0 or amount > summary["balance"]:
        raise ValueError("Salary payment cannot exceed the remaining earned salary")
    method = payment.get("method")
    if not isinstance(method, str) or method not in {"Cash", "UPI", "Bank transfer", "Other"}:
        raise ValueError("Select a valid payment method")
    payment_date = str(payment.get("date", "")).strip()
    try:
        date.fromisoformat(payment_date)
    except ValueError:
        raise ValueError("Enter a valid payment date")
    record = {
        "id": next_id(employee.get("salary_payments", []), "SALPAY"),
        "month": month,
        "date": payment_date,
        "amount": amount,
        "method": method,
    }
    employee.setdefault("salary_payments", []).append(record)
    return record, round(summary["balance"] - amount, 2)


def validate_progress_entry(entry):
    if not isinstance(entry, dict):
        raise ValueError("Progress update details must be an object")
    project_id = str(entry.get("project_id", "")).strip()
    project = next((item for item in read_projects() if item.get("id") == project_id), None)
    if not project:
        raise ValueError("Select an existing project")
    entry_date = str(entry.get("date", "")).strip()
    try:
        date.fromisoformat(entry_date)
        progress = int(entry.get("progress", -1))
    except (TypeError, ValueError):
        raise ValueError("Enter a valid date and progress percentage")
    if progress < 0 or progress > 100:
        raise ValueError("Progress must be between 0 and 100")
    summary = str(entry.get("summary", "")).strip()
    if not summary or len(summary) > 300:
        raise ValueError("Enter a work update of 1 to 300 characters")
    completed = entry.get("completed_tasks", [])
    pending = entry.get("pending_tasks", [])
    if not isinstance(completed, list) or not isinstance(pending, list):
        raise ValueError("Completed and pending tasks must be lists")
    completed = [str(task).strip() for task in completed if str(task).strip()]
    pending = [str(task).strip() for task in pending if str(task).strip()]
    if len(completed) > 30 or len(pending) > 30 or any(len(task) > 160 for task in completed + pending):
        raise ValueError("Task lists may contain up to 30 items of 160 characters each")
    notes = str(entry.get("notes", "")).strip()
    if len(notes) > 500:
        raise ValueError("Progress notes must be 500 characters or fewer")
    entry.update({
        "project_id": project["id"],
        "project_name": project["name"],
        "date": entry_date,
        "progress": progress,
        "summary": summary,
        "completed_tasks": completed,
        "pending_tasks": pending,
        "notes": notes,
    })


def build_payment_ledger():
    ledger = []
    for invoice in read_invoices():
        for index, payment in enumerate(invoice.get("payments", []), 1):
            ledger.append({
                "id": "{}-PAY-{:03d}".format(invoice["id"], index),
                "date": payment.get("date", ""),
                "direction": "Incoming",
                "kind": "Invoice",
                "party_name": invoice.get("project_name", ""),
                "project_id": invoice.get("project_id", ""),
                "project_name": invoice.get("project_name", ""),
                "reference": invoice["id"],
                "amount": float(payment.get("amount", 0)),
                "method": payment.get("method", ""),
            })
    for supplier in read_suppliers():
        for bill in supplier.get("bills", []):
            for index, payment in enumerate(bill.get("payments", []), 1):
                ledger.append({
                    "id": "{}-PAY-{:03d}".format(bill["id"], index),
                    "date": payment.get("date", ""),
                    "direction": "Outgoing",
                    "kind": "Supplier",
                    "party_name": supplier.get("name", ""),
                    "project_id": bill.get("project_id", ""),
                    "project_name": bill.get("project_name", ""),
                    "reference": bill.get("invoice_number") or bill["id"],
                    "amount": float(payment.get("amount", 0)),
                    "method": payment.get("method", ""),
                })
    for employee in read_employees():
        for payment in employee.get("salary_payments", []):
            ledger.append({
                "id": payment["id"],
                "date": payment.get("date", ""),
                "direction": "Outgoing",
                "kind": "Salary",
                "party_name": employee.get("name", ""),
                "project_id": payment.get("project_id", ""),
                "project_name": payment.get("project_name", ""),
                "reference": payment.get("month", ""),
                "amount": float(payment.get("amount", 0)),
                "method": payment.get("method", ""),
            })
    for payment in read_payments():
        ledger.append(payment)
    return sorted(ledger, key=lambda payment: (payment.get("date", ""), payment.get("id", "")), reverse=True)


def validate_other_payment(payment):
    if not isinstance(payment, dict):
        raise ValueError("Payment details must be an object")
    direction = payment.get("direction")
    if not isinstance(direction, str) or direction not in {"Incoming", "Outgoing"}:
        raise ValueError("Select Incoming or Outgoing")
    party_name = str(payment.get("party_name", "")).strip()
    category = str(payment.get("category", "")).strip()
    if not party_name or len(party_name) > 120 or not category or len(category) > 80:
        raise ValueError("Enter a payee/payer and payment category")
    try:
        amount = round(float(payment.get("amount", 0)), 2)
    except (TypeError, ValueError):
        raise ValueError("Payment amount must be a valid number")
    if not math.isfinite(amount) or amount <= 0 or amount > 1_000_000_000_000:
        raise ValueError("Payment amount must be greater than zero and within supported limits")
    payment_date = str(payment.get("date", "")).strip()
    try:
        date.fromisoformat(payment_date)
    except ValueError:
        raise ValueError("Enter a valid payment date")
    method = payment.get("method")
    if not isinstance(method, str) or method not in {"Cash", "UPI", "Bank transfer", "Other"}:
        raise ValueError("Select a valid payment method")
    project_id = str(payment.get("project_id", "")).strip()
    project = next((item for item in read_projects() if item.get("id") == project_id), None) if project_id else None
    if project_id and not project:
        raise ValueError("Select an existing project")
    notes = str(payment.get("notes", "")).strip()
    if len(notes) > 500:
        raise ValueError("Payment notes must be 500 characters or fewer")
    payment.update({
        "direction": direction,
        "kind": "Other",
        "party_name": party_name,
        "category": category,
        "amount": amount,
        "date": payment_date,
        "method": method,
        "project_id": project["id"] if project else "",
        "project_name": project["name"] if project else "",
        "reference": str(payment.get("reference", "")).strip()[:80],
        "notes": notes,
    })


def project_payroll_cost(employee, month=None):
    entries = employee.get("attendance", [])
    if month:
        entries = [entry for entry in entries if entry.get("date", "").startswith(month)]
    return round(
        sum(
            (1 if entry.get("status") == "Present" else 0.5 if entry.get("status") == "Half day" else 0)
            * float(entry.get("daily_wage", employee.get("daily_wage", 0)))
            for entry in entries
        ),
        2,
    )


def build_reports(month):
    try:
        date.fromisoformat(month + "-01")
    except ValueError:
        raise ValueError("Select a valid report month")
    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError("Select a valid report month")

    projects = read_projects()
    invoices = read_invoices()
    expenses = read_expenses()
    suppliers = read_suppliers()
    employees = read_employees()
    materials = read_materials()
    payments = build_payment_ledger()
    month_invoices = [invoice for invoice in invoices if invoice.get("issue_date", "").startswith(month)]
    month_expenses = [expense for expense in expenses if expense.get("date", "").startswith(month)]
    month_bills = [
        (supplier, bill)
        for supplier in suppliers
        for bill in supplier.get("bills", [])
        if bill.get("date", "").startswith(month)
    ]
    month_material_purchases = [
        (material, movement)
        for material in materials
        for movement in material.get("movements", [])
        if movement.get("type") == "Stock in" and movement.get("date", "").startswith(month)
    ]
    month_material_usage = [
        (material, movement)
        for material in materials
        for movement in material.get("movements", [])
        if movement.get("type") == "Stock out" and movement.get("date", "").startswith(month)
    ]
    month_payments = [payment for payment in payments if payment.get("date", "").startswith(month)]
    payroll_rows = []
    for employee in employees:
        payroll = payroll_summary(employee, month)
        if payroll["attendance_days"] or payroll["paid"]:
            payroll_rows.append({
                "employee_id": employee["id"],
                "employee_name": employee["name"],
                "role": employee["role"],
                **payroll,
            })

    expenses_by_category = {}
    for expense in month_expenses:
        expenses_by_category[expense["category"]] = round(
            expenses_by_category.get(expense["category"], 0) + float(expense["amount"]), 2
        )
    material_purchases = {}
    for material, movement in month_material_purchases:
        material_name = material.get("name", "Material")
        purchase_value = round(float(movement.get("quantity", 0)) * float(movement.get("unit_price", 0)), 2)
        material_purchases[material_name] = round(material_purchases.get(material_name, 0) + purchase_value, 2)

    project_rows = []
    for project in projects:
        revenue = round(sum(float(invoice.get("total", 0)) for invoice in invoices if invoice.get("project_id") == project["id"]), 2)
        project_expenses = round(sum(float(expense.get("amount", 0)) for expense in expenses if expense.get("project_id") == project["id"]), 2)
        supplier_costs = round(sum(
            float(bill.get("amount", 0))
            for supplier in suppliers for bill in supplier.get("bills", [])
            if bill.get("project_id") == project["id"]
        ), 2)
        material_usage = round(sum(
            float(movement.get("quantity", 0)) * float(movement.get("unit_price", 0))
            for material in materials for movement in material.get("movements", [])
            if movement.get("type") == "Stock out" and movement.get("project_id") == project["id"]
        ), 2)
        payroll_cost = round(sum(
            (1 if entry.get("status") == "Present" else 0.5 if entry.get("status") == "Half day" else 0)
            * float(entry.get("daily_wage", employee.get("daily_wage", 0)))
            for employee in employees
            for entry in employee.get("attendance", [])
            if entry.get("project_id") == project["id"]
        ), 2)
        costs = round(project_expenses + supplier_costs + material_usage + payroll_cost, 2)
        project_rows.append({
            "project_id": project["id"],
            "project_name": project["name"],
            "revenue": revenue,
            "expenses": project_expenses,
            "supplier_purchases": supplier_costs,
            "material_usage": material_usage,
            "payroll": payroll_cost,
            "total_cost": costs,
            "profit": round(revenue - costs, 2),
        })

    invoice_outstanding = round(sum(float(invoice.get("balance", 0)) for invoice in invoices), 2)
    supplier_outstanding = round(sum(
        max(0, float(bill.get("amount", 0)) - float(bill.get("paid_amount", 0)))
        for supplier in suppliers for bill in supplier.get("bills", [])
    ), 2)
    return {
        "month": month,
        "summary": {
            "revenue": round(sum(float(invoice.get("total", 0)) for invoice in month_invoices), 2),
            "collected": round(sum(float(payment.get("amount", 0)) for payment in month_payments if payment.get("direction") == "Incoming"), 2),
            "expenses": round(sum(float(expense.get("amount", 0)) for expense in month_expenses), 2),
            "supplier_purchases": round(sum(float(bill.get("amount", 0)) for _, bill in month_bills), 2),
            "material_purchases": round(sum(
                float(movement.get("quantity", 0)) * float(movement.get("unit_price", 0))
                for _, movement in month_material_purchases
            ), 2),
            "material_usage": round(sum(
                float(movement.get("quantity", 0)) * float(movement.get("unit_price", 0))
                for _, movement in month_material_usage
            ), 2),
            "salary_paid": round(sum(float(payment.get("amount", 0)) for payment in month_payments if payment.get("kind") == "Salary"), 2),
            "payroll_accrued": round(sum(row["earned"] for row in payroll_rows), 2),
            "gst_collected": round(sum(float(invoice.get("gst_amount", 0)) for invoice in month_invoices), 2),
            "invoice_outstanding": invoice_outstanding,
            "supplier_outstanding": supplier_outstanding,
            "payroll_outstanding": round(sum(row["balance"] for row in payroll_rows), 2),
        },
        "expenses_by_category": [
            {"category": category, "amount": amount}
            for category, amount in sorted(expenses_by_category.items())
        ],
        "material_purchases": [
            {"material": name, "amount": amount}
            for name, amount in sorted(material_purchases.items(), key=lambda item: item[1], reverse=True)
        ],
        "payroll": payroll_rows,
        "project_profit_loss": project_rows,
        "payments": month_payments,
    }


def compact_currency(value):
    value = float(value)
    if abs(value) >= 10_000_000:
        return "₹{:.1f}Cr".format(value / 10_000_000)
    if abs(value) >= 100_000:
        return "₹{:.1f}L".format(value / 100_000)
    return "₹{:,.0f}".format(value)


def build_dashboard_data():
    projects = read_projects()
    invoices = read_invoices()
    expenses = read_expenses()
    suppliers = read_suppliers()
    employees = read_employees()
    month = date.today().strftime("%Y-%m")
    report = build_reports(month)
    revenue = round(sum(float(invoice.get("total", 0)) for invoice in invoices), 2)
    outstanding = round(
        report["summary"]["invoice_outstanding"]
        + report["summary"]["supplier_outstanding"]
        + report["summary"]["payroll_outstanding"],
        2,
    )
    total_expenses = round(
        sum(float(expense.get("amount", 0)) for expense in expenses)
        + sum(float(bill.get("amount", 0)) for supplier in suppliers for bill in supplier.get("bills", []))
        + sum(
            float(movement.get("quantity", 0)) * float(movement.get("unit_price", 0))
            for material in read_materials()
            for movement in material.get("movements", [])
            if movement.get("type") == "Stock out"
        )
        + sum(project_payroll_cost(employee) for employee in employees),
        2,
    )
    monthly_profit = round(
        report["summary"]["revenue"] - report["summary"]["expenses"]
        - report["summary"]["supplier_purchases"] - report["summary"]["material_usage"]
        - report["summary"]["payroll_accrued"],
        2,
    )
    active_projects = sum(project.get("status") == "In progress" for project in projects)
    completed_projects = sum(project.get("status") == "Completed" for project in projects)
    metrics = [
        {"label": "Total projects", "value": str(len(projects)), "change": "In the project register", "icon": "projects", "tone": "blue"},
        {"label": "Ongoing projects", "value": str(active_projects), "change": "Currently in progress", "icon": "ongoing", "tone": "orange"},
        {"label": "Completed projects", "value": str(completed_projects), "change": "Marked complete", "icon": "completed", "tone": "green"},
        {"label": "Total revenue", "value": compact_currency(revenue), "change": "From recorded invoices", "icon": "revenue", "tone": "green"},
        {"label": "Pending payments", "value": compact_currency(outstanding), "change": "Invoices, supplier bills, payroll", "icon": "payments", "tone": "red"},
        {"label": "Total expenses", "value": compact_currency(total_expenses), "change": "Recorded costs and accrued payroll", "icon": "expenses", "tone": "yellow"},
        {"label": "Monthly profit", "value": compact_currency(monthly_profit), "change": "Invoiced revenue less recorded costs", "icon": "profit", "tone": "teal"},
    ]
    dashboard_projects = []
    for project in sorted(projects, key=lambda item: (item.get("status") == "Completed", item.get("expected_completion_date", "")))[:4]:
        dashboard_projects.append({
            "name": project["name"],
            "location": project.get("location", ""),
            "progress": project.get("progress", 0),
            "status": project.get("status", "Planning"),
            "tone": {"Completed": "green", "In progress": "blue", "On hold": "orange"}.get(project.get("status"), "neutral"),
        })
    activities = []
    for payment in build_payment_ledger():
        activities.append({
            "title": "{} payment".format("Payment received" if payment.get("direction") == "Incoming" else "Payment sent"),
            "description": "{} · {}".format(compact_currency(payment.get("amount", 0)), payment.get("party_name", "")),
            "time": payment.get("date", ""),
            "kind": "payment",
            "date": payment.get("date", ""),
        })
    for entry in read_progress():
        activities.append({
            "title": "Project progress updated",
            "description": "{} · {}% complete".format(entry.get("project_name", ""), entry.get("progress", 0)),
            "time": entry.get("date", ""),
            "kind": "project",
            "date": entry.get("date", ""),
        })
    for expense in expenses:
        activities.append({
            "title": "Expense recorded",
            "description": "{} · {}".format(compact_currency(expense.get("amount", 0)), expense.get("description", "")),
            "time": expense.get("date", ""),
            "kind": "expense",
            "date": expense.get("date", ""),
        })
    activities = sorted(activities, key=lambda item: item["date"], reverse=True)[:5]
    return {"metrics": metrics, "projects": dashboard_projects, "activities": activities}


class ConstructionHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/dashboard":
            self.send_json(build_dashboard_data())
            return
        if path == "/api/projects":
            self.send_json(read_projects())
            return
        if path == "/api/estimates":
            self.send_json(read_estimates())
            return
        if path == "/api/invoices":
            self.send_json(read_invoices())
            return
        if path == "/api/materials":
            self.send_json(read_materials())
            return
        if path == "/api/expenses":
            self.send_json(read_expenses())
            return
        if path == "/api/suppliers":
            self.send_json(read_suppliers())
            return
        if path == "/api/employees":
            self.send_json(read_employees())
            return
        if path == "/api/progress":
            self.send_json(read_progress())
            return
        if path == "/api/payments":
            self.send_json(build_payment_ledger())
            return
        if path == "/api/reports":
            month = parse_qs(parsed.query).get("month", [date.today().strftime("%Y-%m")])[0]
            try:
                self.send_json(build_reports(month))
            except ValueError as error:
                self.send_json({"error": str(error)}, 400)
            return
        if path == "/":
            self.path = "/index.html"
        elif path == "/customers":
            self.send_response(302)
            self.send_header("Location", "/projects")
            self.end_headers()
            return
        elif path == "/projects":
            self.path = "/projects.html"
        elif path == "/billing":
            self.path = "/estimates.html"
        elif path == "/materials":
            self.path = "/materials.html"
        elif path == "/expenses":
            self.path = "/expenses.html"
        elif path == "/suppliers":
            self.path = "/suppliers.html"
        elif path == "/employees":
            self.path = "/employees.html"
        elif path == "/progress":
            self.path = "/progress.html"
        elif path == "/payments":
            self.path = "/payments.html"
        elif path == "/reports":
            self.path = "/reports.html"
        elif path in {"/estimates", "/invoices"}:
            self.send_response(302)
            self.send_header("Location", "/billing#invoices" if path == "/invoices" else "/billing#estimates")
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/index.html"
        elif path == "/customers":
            self.send_response(302)
            self.send_header("Location", "/projects")
            self.end_headers()
            return
        elif path == "/projects":
            self.path = "/projects.html"
        elif path == "/billing":
            self.path = "/estimates.html"
        elif path == "/materials":
            self.path = "/materials.html"
        elif path == "/expenses":
            self.path = "/expenses.html"
        elif path == "/suppliers":
            self.path = "/suppliers.html"
        elif path == "/employees":
            self.path = "/employees.html"
        elif path == "/progress":
            self.path = "/progress.html"
        elif path == "/payments":
            self.path = "/payments.html"
        elif path == "/reports":
            self.path = "/reports.html"
        elif path in {"/estimates", "/invoices"}:
            self.send_response(302)
            self.send_header("Location", "/billing#invoices" if path == "/invoices" else "/billing#estimates")
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        path = urlparse(self.path).path
        conversion_match = re.fullmatch(r"/api/estimates/(EST-\d+)/convert", path)
        if conversion_match:
            estimate_id = conversion_match.group(1)
            estimates = read_estimates()
            estimate = next((item for item in estimates if item.get("id") == estimate_id), None)
            if not estimate:
                self.send_json({"error": "Estimate not found"}, 404)
                return
            if estimate.get("status") != "Accepted":
                self.send_json({"error": "Only accepted estimates can be converted to invoices."}, 409)
                return
            if estimate.get("converted_invoice_id"):
                self.send_json({"error": f"This estimate was already converted to {estimate['converted_invoice_id']}."}, 409)
                return
            issue_date = date.today()
            invoice = {
                "id": next_invoice_id(),
                "estimate_id": estimate["id"],
                "project_id": estimate["project_id"],
                "project_name": estimate["project_name"],
                "items": estimate["items"],
                "subtotal": estimate["subtotal"],
                "discount_percent": estimate["discount_percent"],
                "discount_amount": estimate["discount_amount"],
                "gst_percent": estimate["gst_percent"],
                "gst_amount": estimate["gst_amount"],
                "notes": estimate.get("notes", ""),
                "total": estimate["total"],
                "paid_amount": 0,
                "balance": estimate["total"],
                "status": "Paid" if estimate["total"] == 0 else "Unpaid",
                "payments": [],
                "issue_date": issue_date.isoformat(),
                "due_date": (issue_date + timedelta(days=30)).isoformat(),
            }
            write_invoices(read_invoices() + [invoice])
            estimate["converted_invoice_id"] = invoice["id"]
            write_estimates(estimates)
            self.send_json(invoice, 201)
            return
        if path == "/api/estimates":
            try:
                estimate = parse_json_request(self)
                validate_estimate(estimate)
                estimate["id"] = next_estimate_id()
                estimate["created_at"] = date.today().isoformat()
                write_estimates(read_estimates() + [estimate])
                self.send_json(estimate, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid estimate data"}, 400)
            return
        if path == "/api/suppliers":
            try:
                supplier = parse_json_request(self)
                allowed_fields = {
                    "name", "contact_number", "email", "address", "gst_number",
                    "materials_supplied", "payment_terms_days",
                }
                if not isinstance(supplier, dict) or set(supplier) - allowed_fields:
                    raise ValueError("Supplier details include unsupported fields")
                validate_supplier(supplier)
                supplier.update({
                    "id": next_id(read_suppliers(), "SUP"),
                    "created_at": date.today().isoformat(),
                    "bills": [],
                })
                write_suppliers(read_suppliers() + [supplier])
                self.send_json(supplier, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid supplier details"}, 400)
            return
        supplier_bill_match = re.fullmatch(r"/api/suppliers/(SUP-\d+)/bills", path)
        if supplier_bill_match:
            supplier_id = supplier_bill_match.group(1)
            try:
                bill = parse_json_request(self)
                allowed_fields = {"description", "invoice_number", "date", "due_date", "amount", "project_id"}
                if not isinstance(bill, dict) or set(bill) - allowed_fields:
                    raise ValueError("Supplier bill details include unsupported fields")
                suppliers = read_suppliers()
                supplier = next((item for item in suppliers if item.get("id") == supplier_id), None)
                if not supplier:
                    self.send_json({"error": "Supplier not found"}, 404)
                    return
                validate_supplier_bill(bill)
                bill["id"] = "{}-BILL-{:03d}".format(supplier_id, len(supplier.get("bills", [])) + 1)
                bill["created_at"] = date.today().isoformat()
                supplier.setdefault("bills", []).append(bill)
                write_suppliers(suppliers)
                self.send_json(bill, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid supplier bill"}, 400)
            return
        if path == "/api/employees":
            try:
                employee = parse_json_request(self)
                allowed_fields = {"name", "phone", "role", "joined_on", "daily_wage", "status"}
                if not isinstance(employee, dict) or set(employee) - allowed_fields:
                    raise ValueError("Employee details include unsupported fields")
                validate_employee(employee)
                employee.update({
                    "id": next_id(read_employees(), "EMP"),
                    "created_at": date.today().isoformat(),
                    "attendance": [],
                    "salary_payments": [],
                })
                write_employees(read_employees() + [employee])
                self.send_json(employee, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid employee details"}, 400)
            return
        attendance_match = re.fullmatch(r"/api/employees/(EMP-\d+)/attendance", path)
        if attendance_match:
            employee_id = attendance_match.group(1)
            try:
                entry = parse_json_request(self)
                allowed_fields = {"date", "status", "project_id", "notes"}
                if not isinstance(entry, dict) or set(entry) - allowed_fields:
                    raise ValueError("Attendance details include unsupported fields")
                validate_attendance(entry)
                employees = read_employees()
                employee = next((item for item in employees if item.get("id") == employee_id), None)
                if not employee:
                    self.send_json({"error": "Employee not found"}, 404)
                    return
                if employee.get("status") != "Active":
                    raise ValueError("Attendance cannot be recorded for an inactive employee")
                if any(record.get("date") == entry["date"] for record in employee.get("attendance", [])):
                    self.send_json({"error": "Attendance has already been recorded for this employee and date"}, 409)
                    return
                entry["id"] = next_id(employee.get("attendance", []), "ATT")
                entry["daily_wage"] = employee["daily_wage"]
                employee.setdefault("attendance", []).append(entry)
                write_employees(employees)
                self.send_json(entry, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid attendance details"}, 400)
            return
        if path == "/api/progress":
            try:
                entry = parse_json_request(self)
                allowed_fields = {"project_id", "date", "progress", "summary", "completed_tasks", "pending_tasks", "notes"}
                if not isinstance(entry, dict) or set(entry) - allowed_fields:
                    raise ValueError("Progress update includes unsupported fields")
                validate_progress_entry(entry)
                entry["id"] = next_id(read_progress(), "UPD")
                entry["created_at"] = date.today().isoformat()
                projects = read_projects()
                project_index = next((i for i, project in enumerate(projects) if project.get("id") == entry["project_id"]), None)
                if project_index is None:
                    self.send_json({"error": "Project not found"}, 404)
                    return
                projects[project_index]["progress"] = entry["progress"]
                write_projects(projects)
                write_progress(read_progress() + [entry])
                self.send_json(entry, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid progress update"}, 400)
            return
        if path == "/api/payments":
            try:
                payment = parse_json_request(self)
                if not isinstance(payment, dict):
                    raise ValueError("Payment details must be an object")
                kind = payment.get("kind")
                if kind == "Invoice":
                    allowed_fields = {"kind", "invoice_id", "amount", "method", "date"}
                    if set(payment) != allowed_fields:
                        raise ValueError("Provide valid invoice payment details")
                    invoices = read_invoices()
                    invoice = next((item for item in invoices if item.get("id") == payment["invoice_id"]), None)
                    if not invoice:
                        self.send_json({"error": "Invoice not found"}, 404)
                        return
                    validate_invoice_payment(invoice, payment)
                    write_invoices(invoices)
                    self.send_json({"kind": kind, "reference": invoice["id"], "balance": invoice["balance"]}, 201)
                    return
                if kind == "Supplier":
                    allowed_fields = {"kind", "supplier_id", "bill_id", "amount", "method", "date"}
                    if set(payment) != allowed_fields:
                        raise ValueError("Provide valid supplier payment details")
                    suppliers = read_suppliers()
                    supplier = next((item for item in suppliers if item.get("id") == payment["supplier_id"]), None)
                    if not supplier:
                        self.send_json({"error": "Supplier not found"}, 404)
                        return
                    bill = next((item for item in supplier.get("bills", []) if item.get("id") == payment["bill_id"]), None)
                    if not bill:
                        self.send_json({"error": "Supplier bill not found"}, 404)
                        return
                    record, balance = apply_bill_payment(bill, payment)
                    write_suppliers(suppliers)
                    self.send_json({"kind": kind, "reference": bill.get("invoice_number") or bill["id"], "payment": record, "balance": balance}, 201)
                    return
                if kind == "Salary":
                    allowed_fields = {"kind", "employee_id", "month", "amount", "method", "date"}
                    if set(payment) != allowed_fields:
                        raise ValueError("Provide valid salary payment details")
                    employees = read_employees()
                    employee = next((item for item in employees if item.get("id") == payment["employee_id"]), None)
                    if not employee:
                        self.send_json({"error": "Employee not found"}, 404)
                        return
                    record, balance = apply_salary_payment(employee, payment)
                    write_employees(employees)
                    self.send_json({"kind": kind, "reference": payment["month"], "payment": record, "balance": balance}, 201)
                    return
                if kind != "Other":
                    raise ValueError("Select a valid payment type")
                allowed_fields = {
                    "kind", "direction", "party_name", "category", "amount",
                    "date", "method", "project_id", "reference", "notes",
                }
                if set(payment) != allowed_fields:
                    raise ValueError("Provide complete payment details")
                validate_other_payment(payment)
                payment["id"] = next_id(read_payments(), "PAY")
                payment["created_at"] = date.today().isoformat()
                write_payments(read_payments() + [payment])
                self.send_json(payment, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid payment details"}, 400)
            return
        material_movement_match = re.fullmatch(r"/api/materials/(MAT-\d+)/movements", path)
        if material_movement_match:
            material_id = material_movement_match.group(1)
            try:
                payload = parse_json_request(self)
                if not isinstance(payload, dict) or set(payload) != {"movement"}:
                    raise ValueError("Provide one stock movement")
                materials = read_materials()
                index = next((i for i, item in enumerate(materials) if item.get("id") == material_id), None)
                if index is None:
                    self.send_json({"error": "Material not found"}, 404)
                    return
                validate_stock_movement(materials[index], payload["movement"])
                write_materials(materials)
                self.send_json(materials[index])
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid stock movement"}, 400)
            return
        if path == "/api/materials":
            try:
                payload = parse_json_request(self)
                validate_material(payload)
                allowed_fields = {"name", "category", "unit", "purchase_price", "minimum_stock", "supplier_name"}
                if set(payload) - allowed_fields:
                    raise ValueError("Material details include unsupported fields")
                material = {
                    **payload,
                    "id": next_material_id(),
                    "quantity": 0,
                    "movements": [],
                }
                materials = read_materials()
                materials.append(material)
                write_materials(materials)
                self.send_json(material, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid material details"}, 400)
            return
        if path == "/api/expenses":
            try:
                expense = parse_json_request(self)
                allowed_fields = {
                    "project_id", "date", "category", "description", "amount",
                    "vendor", "payment_method", "notes",
                }
                if not isinstance(expense, dict) or set(expense) - allowed_fields:
                    raise ValueError("Expense details include unsupported fields")
                validate_expense(expense)
                expense["id"] = next_expense_id()
                expense["created_at"] = date.today().isoformat()
                write_expenses(read_expenses() + [expense])
                self.send_json(expense, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid expense details"}, 400)
            return
        if path == "/api/projects":
            try:
                project = parse_json_request(self)
                validate_project(project)
                project["id"] = next_project_id()
                projects = read_projects()
                projects.append(project)
                write_projects(projects)
                self.send_json(project, 201)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid project data"}, 400)
            return
        self.send_json({"error": "Not found"}, 404)

    def do_PUT(self):
        path = urlparse(self.path).path
        invoice_match = re.fullmatch(r"/api/invoices/(INV-\d+)", path)
        if invoice_match:
            invoice_id = invoice_match.group(1)
            try:
                updates = parse_json_request(self)
                if not isinstance(updates, dict) or set(updates) != {"payment"}:
                    raise ValueError("Provide one payment record")
                invoices = read_invoices()
                index = next((i for i, item in enumerate(invoices) if item["id"] == invoice_id), None)
                if index is None:
                    self.send_json({"error": "Invoice not found"}, 404)
                    return
                validate_invoice_payment(invoices[index], updates["payment"])
                write_invoices(invoices)
                self.send_json(invoices[index])
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid payment details"}, 400)
            return
        estimate_match = re.fullmatch(r"/api/estimates/(EST-\d+)", path)
        if estimate_match:
            estimate_id = estimate_match.group(1)
            try:
                updates = parse_json_request(self)
                if not isinstance(updates, dict):
                    raise ValueError("Estimate details must be an object")
                estimates = read_estimates()
                index = next((i for i, item in enumerate(estimates) if item["id"] == estimate_id), None)
                if index is None:
                    self.send_json({"error": "Estimate not found"}, 404)
                    return
                if estimates[index].get("converted_invoice_id"):
                    self.send_json({"error": "This estimate has been converted to an invoice and cannot be changed."}, 409)
                    return
                updated = {**estimates[index], **updates, "id": estimate_id}
                validate_estimate(updated)
                estimates[index] = updated
                write_estimates(estimates)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid estimate data"}, 400)
            return
        material_match = re.fullmatch(r"/api/materials/(MAT-\d+)", path)
        if material_match:
            material_id = material_match.group(1)
            try:
                updates = parse_json_request(self)
                allowed_fields = {"name", "category", "unit", "purchase_price", "minimum_stock", "supplier_name"}
                if not isinstance(updates, dict) or not updates or set(updates) - allowed_fields:
                    raise ValueError("Provide valid material details")
                materials = read_materials()
                index = next((i for i, item in enumerate(materials) if item.get("id") == material_id), None)
                if index is None:
                    self.send_json({"error": "Material not found"}, 404)
                    return
                updated = {**materials[index], **updates, "id": material_id}
                validate_material(updated)
                materials[index] = updated
                write_materials(materials)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid material details"}, 400)
            return
        supplier_match = re.fullmatch(r"/api/suppliers/(SUP-\d+)", path)
        if supplier_match:
            supplier_id = supplier_match.group(1)
            try:
                updates = parse_json_request(self)
                allowed_fields = {
                    "name", "contact_number", "email", "address", "gst_number",
                    "materials_supplied", "payment_terms_days",
                }
                if not isinstance(updates, dict) or not updates or set(updates) - allowed_fields:
                    raise ValueError("Provide valid supplier details")
                suppliers = read_suppliers()
                index = next((i for i, item in enumerate(suppliers) if item.get("id") == supplier_id), None)
                if index is None:
                    self.send_json({"error": "Supplier not found"}, 404)
                    return
                updated = {**suppliers[index], **updates, "id": supplier_id}
                validate_supplier(updated)
                suppliers[index] = updated
                write_suppliers(suppliers)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid supplier details"}, 400)
            return
        attendance_match = re.fullmatch(r"/api/employees/(EMP-\d+)/attendance/(ATT-\d+)", path)
        if attendance_match:
            employee_id, attendance_id = attendance_match.groups()
            try:
                updates = parse_json_request(self)
                allowed_fields = {"date", "status", "project_id", "notes"}
                if not isinstance(updates, dict) or not updates or set(updates) - allowed_fields:
                    raise ValueError("Provide valid attendance details")
                employees = read_employees()
                employee_index = next((i for i, item in enumerate(employees) if item.get("id") == employee_id), None)
                if employee_index is None:
                    self.send_json({"error": "Employee not found"}, 404)
                    return
                employee = employees[employee_index]
                attendance = employee.get("attendance", [])
                attendance_index = next((i for i, item in enumerate(attendance) if item.get("id") == attendance_id), None)
                if attendance_index is None:
                    self.send_json({"error": "Attendance record not found"}, 404)
                    return
                updated = {**attendance[attendance_index], **updates, "id": attendance_id}
                validate_attendance(updated)
                updated.setdefault("daily_wage", employee["daily_wage"])
                if any(
                    item.get("id") != attendance_id and item.get("date") == updated["date"]
                    for item in attendance
                ):
                    raise ValueError("Attendance already exists for this employee and date")
                if any(payment.get("month") == updated["date"][:7] for payment in employee.get("salary_payments", [])):
                    raise ValueError("Attendance cannot be changed after salary has been paid for that month")
                attendance[attendance_index] = updated
                write_employees(employees)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid attendance details"}, 400)
            return
        employee_match = re.fullmatch(r"/api/employees/(EMP-\d+)", path)
        if employee_match:
            employee_id = employee_match.group(1)
            try:
                updates = parse_json_request(self)
                allowed_fields = {"name", "phone", "role", "joined_on", "daily_wage", "status"}
                if not isinstance(updates, dict) or not updates or set(updates) - allowed_fields:
                    raise ValueError("Provide valid employee details")
                employees = read_employees()
                index = next((i for i, item in enumerate(employees) if item.get("id") == employee_id), None)
                if index is None:
                    self.send_json({"error": "Employee not found"}, 404)
                    return
                updated = {**employees[index], **updates, "id": employee_id}
                validate_employee(updated)
                employees[index] = updated
                write_employees(employees)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid employee details"}, 400)
            return
        expense_match = re.fullmatch(r"/api/expenses/(EXP-\d+)", path)
        if expense_match:
            expense_id = expense_match.group(1)
            try:
                updates = parse_json_request(self)
                allowed_fields = {
                    "project_id", "date", "category", "description", "amount",
                    "vendor", "payment_method", "notes",
                }
                if not isinstance(updates, dict) or not updates or set(updates) - allowed_fields:
                    raise ValueError("Provide valid expense details")
                expenses = read_expenses()
                index = next((i for i, item in enumerate(expenses) if item.get("id") == expense_id), None)
                if index is None:
                    self.send_json({"error": "Expense not found"}, 404)
                    return
                updated = {**expenses[index], **updates, "id": expense_id}
                validate_expense(updated)
                updated["updated_at"] = date.today().isoformat()
                expenses[index] = updated
                write_expenses(expenses)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid expense details"}, 400)
            return
        if re.fullmatch(r"/api/projects/PRJ-\d+", path):
            project_id = path.rsplit("/", 1)[-1]
            try:
                updates = parse_json_request(self)
                if not isinstance(updates, dict):
                    raise ValueError("Project details must be an object")
                projects = read_projects()
                index = next((i for i, item in enumerate(projects) if item["id"] == project_id), None)
                if index is None:
                    self.send_json({"error": "Project not found"}, 404)
                    return
                updated = {**projects[index], **updates, "id": project_id}
                validate_project(updated)
                projects[index] = updated
                write_projects(projects)
                self.send_json(updated)
            except (json.JSONDecodeError, ValueError) as error:
                self.send_json({"error": str(error) or "Invalid project data"}, 400)
            return
        self.send_json({"error": "Not found"}, 404)

    def do_DELETE(self):
        path = urlparse(self.path).path
        estimate_match = re.fullmatch(r"/api/estimates/(EST-\d+)", path)
        if estimate_match:
            estimate_id = estimate_match.group(1)
            estimates = read_estimates()
            if any(item.get("id") == estimate_id and item.get("converted_invoice_id") for item in estimates):
                self.send_json({"error": "This estimate has been converted to an invoice and cannot be deleted."}, 409)
                return
            remaining = [estimate for estimate in estimates if estimate["id"] != estimate_id]
            if len(remaining) == len(estimates):
                self.send_json({"error": "Estimate not found"}, 404)
                return
            write_estimates(remaining)
            self.send_json({"deleted": estimate_id})
            return
        material_match = re.fullmatch(r"/api/materials/(MAT-\d+)", path)
        if material_match:
            material_id = material_match.group(1)
            materials = read_materials()
            material = next((item for item in materials if item.get("id") == material_id), None)
            if not material:
                self.send_json({"error": "Material not found"}, 404)
                return
            if float(material.get("quantity", 0)) != 0 or material.get("movements"):
                self.send_json({"error": "Materials with stock or movement history cannot be deleted."}, 409)
                return
            write_materials([item for item in materials if item.get("id") != material_id])
            self.send_json({"deleted": material_id})
            return
        attendance_match = re.fullmatch(r"/api/employees/(EMP-\d+)/attendance/(ATT-\d+)", path)
        if attendance_match:
            employee_id, attendance_id = attendance_match.groups()
            employees = read_employees()
            employee = next((item for item in employees if item.get("id") == employee_id), None)
            if not employee:
                self.send_json({"error": "Employee not found"}, 404)
                return
            attendance = employee.get("attendance", [])
            record = next((item for item in attendance if item.get("id") == attendance_id), None)
            if not record:
                self.send_json({"error": "Attendance record not found"}, 404)
                return
            if any(payment.get("month") == record.get("date", "")[:7] for payment in employee.get("salary_payments", [])):
                self.send_json({"error": "Attendance cannot be removed after salary has been paid for that month"}, 409)
                return
            employee["attendance"] = [item for item in attendance if item.get("id") != attendance_id]
            write_employees(employees)
            self.send_json({"deleted": attendance_id})
            return
        supplier_match = re.fullmatch(r"/api/suppliers/(SUP-\d+)", path)
        if supplier_match:
            supplier_id = supplier_match.group(1)
            suppliers = read_suppliers()
            supplier = next((item for item in suppliers if item.get("id") == supplier_id), None)
            if not supplier:
                self.send_json({"error": "Supplier not found"}, 404)
                return
            supplier_name = supplier.get("name", "").casefold()
            has_stock_history = any(
                material.get("supplier_name", "").casefold() == supplier_name
                or any(movement.get("supplier_name", "").casefold() == supplier_name for movement in material.get("movements", []))
                for material in read_materials()
            )
            if supplier.get("bills") or has_stock_history:
                self.send_json({"error": "Suppliers with bills or purchase history cannot be deleted."}, 409)
                return
            write_suppliers([item for item in suppliers if item.get("id") != supplier_id])
            self.send_json({"deleted": supplier_id})
            return
        employee_match = re.fullmatch(r"/api/employees/(EMP-\d+)", path)
        if employee_match:
            employee_id = employee_match.group(1)
            employees = read_employees()
            employee = next((item for item in employees if item.get("id") == employee_id), None)
            if not employee:
                self.send_json({"error": "Employee not found"}, 404)
                return
            if employee.get("attendance") or employee.get("salary_payments"):
                self.send_json({"error": "Employees with attendance or salary history cannot be deleted. Mark the employee inactive instead."}, 409)
                return
            write_employees([item for item in employees if item.get("id") != employee_id])
            self.send_json({"deleted": employee_id})
            return
        expense_match = re.fullmatch(r"/api/expenses/(EXP-\d+)", path)
        if expense_match:
            expense_id = expense_match.group(1)
            expenses = read_expenses()
            remaining = [expense for expense in expenses if expense.get("id") != expense_id]
            if len(remaining) == len(expenses):
                self.send_json({"error": "Expense not found"}, 404)
                return
            write_expenses(remaining)
            self.send_json({"deleted": expense_id})
            return
        project_match = re.fullmatch(r"/api/projects/(PRJ-\d+)", path)
        if project_match:
            project_id = project_match.group(1)
            if (any(estimate.get("project_id") == project_id for estimate in read_estimates())
                    or any(invoice.get("project_id") == project_id for invoice in read_invoices())
                    or any(expense.get("project_id") == project_id for expense in read_expenses())
                    or any(entry.get("project_id") == project_id for entry in read_progress())
                    or any(
                        bill.get("project_id") == project_id
                        for supplier in read_suppliers()
                        for bill in supplier.get("bills", [])
                    )
                    or any(
                        entry.get("project_id") == project_id
                        for employee in read_employees()
                        for entry in employee.get("attendance", [])
                    )
                    or any(payment.get("project_id") == project_id for payment in read_payments())
                    or any(
                        movement.get("project_id") == project_id
                        for material in read_materials()
                        for movement in material.get("movements", [])
                    )):
                self.send_json({"error": "This project has expenses, invoices, or other linked financial or work history and cannot be deleted."}, 409)
                return
            projects = read_projects()
            remaining = [project for project in projects if project["id"] != project_id]
            if len(remaining) == len(projects):
                self.send_json({"error": "Project not found"}, 404)
                return
            write_projects(remaining)
            self.send_json({"deleted": project_id})
            return
        self.send_json({"error": "Not found"}, 404)


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print("Super Construction is running at http://127.0.0.1:8000")
    ThreadingHTTPServer(address, ConstructionHandler).serve_forever()

