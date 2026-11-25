import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import app


class QuietConstructionHandler(app.ConstructionHandler):
    def log_message(self, format_string, *args):
        pass


class RemainingModuleApiTests(unittest.TestCase):
    FILE_NAMES = (
        "PROJECTS_FILE",
        "INVOICES_FILE",
        "MATERIALS_FILE",
        "EXPENSES_FILE",
        "SUPPLIERS_FILE",
        "EMPLOYEES_FILE",
        "PROGRESS_FILE",
        "PAYMENTS_FILE",
    )

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_files = {name: getattr(app, name) for name in cls.FILE_NAMES}
        for name in cls.FILE_NAMES:
            setattr(app, name, Path(cls.temp_dir.name) / (name.lower() + ".json"))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietConstructionHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for name, value in cls.original_files.items():
            setattr(app, name, value)
        cls.temp_dir.cleanup()

    def setUp(self):
        for name in self.FILE_NAMES:
            getattr(app, name).write_text("[]", encoding="utf-8")
        app.write_projects([{
            "id": "PRJ-900",
            "name": "Module test project",
            "location": "Test site",
            "start_date": "2026-01-01",
            "expected_completion_date": "2026-12-31",
            "budget": 100000,
            "contract_amount": 150000,
            "status": "In progress",
            "progress": 0,
            "supervisor": "",
        }])
        app.write_invoices([{
            "id": "INV-900",
            "project_id": "PRJ-900",
            "project_name": "Module test project",
            "total": 2000,
            "gst_amount": 0,
            "paid_amount": 0,
            "balance": 2000,
            "payments": [],
            "issue_date": "2026-04-05",
        }])

    def request(self, path, method="GET", payload=None):
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(self.base_url + path, data=body, method=method)
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    def test_supplier_bill_payment_is_listed_in_payment_ledger(self):
        status, supplier = self.request("/api/suppliers", "POST", {
            "name": "Test supplier",
            "contact_number": "555-0100",
            "email": "supplier@example.com",
            "address": "",
            "gst_number": "",
            "materials_supplied": ["Cement"],
            "payment_terms_days": 14,
        })
        self.assertEqual(status, 201)
        status, bill = self.request("/api/suppliers/{}/bills".format(supplier["id"]), "POST", {
            "description": "Cement delivery",
            "invoice_number": "SUP-INV-1",
            "date": "2026-04-10",
            "due_date": "2026-04-24",
            "amount": 1000,
            "project_id": "PRJ-900",
        })
        self.assertEqual(status, 201)

        status, result = self.request("/api/payments", "POST", {
            "kind": "Supplier",
            "supplier_id": supplier["id"],
            "bill_id": bill["id"],
            "amount": 400,
            "method": "UPI",
            "date": "2026-04-12",
        })
        self.assertEqual(status, 201)
        self.assertEqual(result["balance"], 600)
        ledger = self.request("/api/payments")[1]
        self.assertEqual(len(ledger), 1)
        self.assertEqual(ledger[0]["direction"], "Outgoing")
        self.assertEqual(ledger[0]["reference"], "SUP-INV-1")

    def test_attendance_wage_snapshot_drives_payroll_and_project_report(self):
        status, employee = self.request("/api/employees", "POST", {
            "name": "Test worker",
            "phone": "555-0123",
            "role": "Mason",
            "joined_on": "2026-01-01",
            "daily_wage": 800,
            "status": "Active",
        })
        self.assertEqual(status, 201)
        status, attendance = self.request(
            "/api/employees/{}/attendance".format(employee["id"]),
            "POST",
            {
                "date": "2026-04-10",
                "status": "Present",
                "project_id": "PRJ-900",
                "notes": "",
            },
        )
        self.assertEqual(status, 201)

        self.assertEqual(self.request(
            "/api/employees/{}".format(employee["id"]),
            "PUT",
            {"daily_wage": 1000},
        )[0], 200)
        status, result = self.request("/api/payments", "POST", {
            "kind": "Salary",
            "employee_id": employee["id"],
            "month": "2026-04",
            "amount": 300,
            "method": "Cash",
            "date": "2026-04-30",
        })
        self.assertEqual(status, 201)
        self.assertEqual(result["balance"], 500)

        report = self.request("/api/reports?month=2026-04")[1]
        self.assertEqual(report["payroll"][0]["earned"], 800)
        self.assertEqual(report["payroll"][0]["paid"], 300)
        self.assertEqual(report["project_profit_loss"][0]["payroll"], 800)
        self.assertEqual(attendance["daily_wage"], 800)

    def test_progress_update_updates_project_and_prevents_deletion(self):
        status, update = self.request("/api/progress", "POST", {
            "project_id": "PRJ-900",
            "date": "2026-04-15",
            "progress": 35,
            "summary": "Foundation complete",
            "completed_tasks": ["Foundation"],
            "pending_tasks": ["Walls"],
            "notes": "Inspection passed",
        })
        self.assertEqual(status, 201)
        self.assertEqual(self.request("/api/projects")[1][0]["progress"], 35)
        self.assertEqual(self.request("/api/progress")[1], [update])
        status, error = self.request("/api/projects/PRJ-900", "DELETE")
        self.assertEqual(status, 409)
        self.assertIn("cannot be deleted", error["error"])

    def test_monthly_report_separates_material_purchases_from_usage(self):
        status, material = self.request("/api/materials", "POST", {
            "name": "Cement",
            "category": "Cement",
            "unit": "bag",
            "purchase_price": 50,
            "minimum_stock": 0,
            "supplier_name": "",
        })
        self.assertEqual(status, 201)
        status, _ = self.request("/api/materials/{}/movements".format(material["id"]), "POST", {
            "movement": {
                "type": "Stock in",
                "quantity": 20,
                "date": "2026-04-01",
                "supplier_name": "",
                "unit_price": 50,
                "project_id": "",
                "note": "",
            },
        })
        self.assertEqual(status, 200)
        status, _ = self.request("/api/materials/{}/movements".format(material["id"]), "POST", {
            "movement": {
                "type": "Stock out",
                "quantity": 4,
                "date": "2026-04-15",
                "project_id": "PRJ-900",
                "note": "",
            },
        })
        self.assertEqual(status, 200)

        report = self.request("/api/reports?month=2026-04")[1]
        self.assertEqual(report["summary"]["material_purchases"], 1000)
        self.assertEqual(report["summary"]["material_usage"], 200)
        self.assertEqual(report["project_profit_loss"][0]["material_usage"], 200)

    def test_rejects_invalid_report_month(self):
        status, result = self.request("/api/reports?month=2026-13")
        self.assertEqual(status, 400)
        self.assertIn("valid report month", result["error"])


if __name__ == "__main__":
    unittest.main()
