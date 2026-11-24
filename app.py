import json
import math
import re
from datetime import date
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CUSTOMERS_FILE = ROOT / "data" / "customers.json"
PROJECTS_FILE = ROOT / "data" / "projects.json"
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


DASHBOARD = {
    "metrics": [
        {"label": "Total projects", "value": "24", "change": "+3 this month", "icon": "projects", "tone": "blue"},
        {"label": "Ongoing projects", "value": "08", "change": "Across 5 locations", "icon": "ongoing", "tone": "orange"},
        {"label": "Completed projects", "value": "16", "change": "This financial year", "icon": "completed", "tone": "green"},
        {"label": "Total revenue", "value": "₹42.8L", "change": "+12.8% this month", "icon": "revenue", "tone": "green"},
        {"label": "Pending payments", "value": "₹8.4L", "change": "Across open invoices", "icon": "payments", "tone": "red"},
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
        path = urlparse(self.path).path
        if path == "/api/dashboard":
            self.send_json(DASHBOARD)
            return
        if path == "/api/projects":
            self.send_json(read_projects())
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
        super().do_HEAD()

    def do_POST(self):
        path = urlparse(self.path).path
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
        project_match = re.fullmatch(r"/api/projects/(PRJ-\d+)", path)
        if project_match:
            project_id = project_match.group(1)
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

