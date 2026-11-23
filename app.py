import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CUSTOMERS_FILE = ROOT / "data" / "customers.json"
CUSTOMERS_FILE.parent.mkdir(exist_ok=True)

if not CUSTOMERS_FILE.exists():
    CUSTOMERS_FILE.write_text(json.dumps([
        {"id": "CUS-001", "name": "Arun Sharma", "contact": "+91 98765 43210", "email": "arun.sharma@example.com", "company": "Sharma Constructions", "gst": "29ABCDE1234F1Z5", "address": "Whitefield, Bengaluru, Karnataka", "projects": 2, "paid": "₹5.25L", "balance": "₹1.75L", "status": "Active"},
        {"id": "CUS-002", "name": "Priya Mehta", "contact": "+91 98450 12345", "email": "priya.mehta@example.com", "company": "Mehta & Partners", "gst": "29FGHIJ5678K2Z1", "address": "Mysuru Road, Mysuru, Karnataka", "projects": 1, "paid": "₹8.40L", "balance": "₹3.60L", "status": "Active"},
        {"id": "CUS-003", "name": "Rahul Reddy", "contact": "+91 99012 34567", "email": "rahul.reddy@example.com", "company": "Reddy Ventures", "gst": "29LMNOP9012Q3Z8", "address": "Sarjapur Road, Bengaluru, Karnataka", "projects": 1, "paid": "₹3.10L", "balance": "₹0", "status": "Active"},
        {"id": "CUS-004", "name": "Sneha Rao", "contact": "+91 97420 67890", "email": "sneha.rao@example.com", "company": "Rao Interiors", "gst": "", "address": "Indiranagar, Bengaluru, Karnataka", "projects": 0, "paid": "₹0", "balance": "₹0", "status": "Inactive"},
    ], indent=2), encoding="utf-8")


def read_customers():
    return json.loads(CUSTOMERS_FILE.read_text(encoding="utf-8"))


def write_customers(customers):
    CUSTOMERS_FILE.write_text(json.dumps(customers, indent=2), encoding="utf-8")

DASHBOARD = {
    "metrics": [
        {"label": "Total projects", "value": "24", "change": "+3 this month", "icon": "projects", "tone": "blue"},
        {"label": "Ongoing projects", "value": "08", "change": "Across 5 locations", "icon": "ongoing", "tone": "orange"},
        {"label": "Completed projects", "value": "16", "change": "This financial year", "icon": "completed", "tone": "green"},
        {"label": "Total customers", "value": "18", "change": "+2 this month", "icon": "customers", "tone": "purple"},
        {"label": "Total revenue", "value": "₹42.8L", "change": "+12.8% this month", "icon": "revenue", "tone": "green"},
        {"label": "Pending payments", "value": "₹8.4L", "change": "From 6 customers", "icon": "payments", "tone": "red"},
        {"label": "Total expenses", "value": "₹26.2L", "change": "This financial year", "icon": "expenses", "tone": "yellow"},
        {"label": "Monthly profit", "value": "₹3.16L", "change": "+8.2% vs last month", "icon": "profit", "tone": "teal"},
    ],
    "projects": [
        {"name": "Sharma Residence", "location": "Whitefield, Bengaluru", "progress": 72, "status": "On track", "tone": "green"},
        {"name": "Lakeview Apartments", "location": "Sarjapur Road, Bengaluru", "progress": 48, "status": "In progress", "tone": "blue"},
        {"name": "Mehta Commercial Complex", "location": "Mysuru, Karnataka", "progress": 31, "status": "At risk", "tone": "orange"},
    ],
    "activities": [
        {"title": "Payment received", "description": "₹2,50,000 from Sharma Residence", "time": "10:42 AM", "kind": "payment"},
        {"title": "New project created", "description": "Mehta Commercial Complex", "time": "Yesterday", "kind": "project"},
        {"title": "Invoice sent", "description": "Invoice #INV-2025-024 to Lakeview Apartments", "time": "Yesterday", "kind": "invoice"},
        {"title": "Material stock updated", "description": "Cement stock increased by 120 bags", "time": "20 Nov, 2026", "kind": "material"},
    ],
}


class ConstructionHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self.send_json(DASHBOARD)
            return
        if path == "/api/customers":
            self.send_json(read_customers())
            return
        if self.path == "/":
            self.path = "/index.html"
        if self.path == "/customers":
            self.path = "/customers.html"
        super().do_GET()

    def do_HEAD(self):
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/index.html"
        elif path == "/customers":
            self.path = "/customers.html"
        super().do_HEAD()

    def do_POST(self):
        if urlparse(self.path).path != "/api/customers":
            self.send_json({"error": "Not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            customer = json.loads(self.rfile.read(length).decode("utf-8"))
            required = ("name", "contact", "email")
            if any(not str(customer.get(field, "")).strip() for field in required):
                self.send_json({"error": "Name, contact and email are required"}, 400)
                return
            customers = read_customers()
            numbers = [int(item["id"].split("-")[-1]) for item in customers if item.get("id", "").startswith("CUS-")]
            customer["id"] = f"CUS-{max(numbers, default=0) + 1:03d}"
            customer.setdefault("company", "")
            customer.setdefault("gst", "")
            customer.setdefault("address", "")
            customer.setdefault("projects", 0)
            customer.setdefault("paid", "₹0")
            customer.setdefault("balance", "₹0")
            customer.setdefault("status", "Active")
            customers.append(customer)
            write_customers(customers)
            self.send_json(customer, 201)
        except (json.JSONDecodeError, ValueError):
            self.send_json({"error": "Invalid customer data"}, 400)

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/customers/"):
            self.send_json({"error": "Not found"}, 404)
            return
        customer_id = path.rsplit("/", 1)[-1]
        try:
            length = int(self.headers.get("Content-Length", "0"))
            updates = json.loads(self.rfile.read(length).decode("utf-8"))
            customers = read_customers()
            index = next((i for i, item in enumerate(customers) if item["id"] == customer_id), None)
            if index is None:
                self.send_json({"error": "Customer not found"}, 404)
                return
            if any(not str(updates.get(field, customers[index].get(field, ""))).strip() for field in ("name", "contact", "email")):
                self.send_json({"error": "Name, contact and email are required"}, 400)
                return
            customers[index].update(updates)
            write_customers(customers)
            self.send_json(customers[index])
        except (json.JSONDecodeError, ValueError):
            self.send_json({"error": "Invalid customer data"}, 400)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/customers/"):
            self.send_json({"error": "Not found"}, 404)
            return
        customer_id = path.rsplit("/", 1)[-1]
        customers = read_customers()
        remaining = [item for item in customers if item["id"] != customer_id]
        if len(remaining) == len(customers):
            self.send_json({"error": "Customer not found"}, 404)
            return
        write_customers(remaining)
        self.send_json({"deleted": customer_id})


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print("Super Construction is running at http://127.0.0.1:8000")
    ThreadingHTTPServer(address, ConstructionHandler).serve_forever()

