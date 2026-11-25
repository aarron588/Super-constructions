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


class ExpenseApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.original_expenses_file = app.EXPENSES_FILE
        cls.original_projects_file = app.PROJECTS_FILE
        app.EXPENSES_FILE = Path(cls.temp_dir.name) / "expenses.json"
        app.PROJECTS_FILE = Path(cls.temp_dir.name) / "projects.json"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), QuietConstructionHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = "http://127.0.0.1:{}".format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        app.EXPENSES_FILE = cls.original_expenses_file
        app.PROJECTS_FILE = cls.original_projects_file
        cls.temp_dir.cleanup()

    def setUp(self):
        app.EXPENSES_FILE.write_text("[]", encoding="utf-8")
        app.PROJECTS_FILE.write_text(json.dumps([{
            "id": "PRJ-987654",
            "name": "Expense test project",
        }]), encoding="utf-8")

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

    def create_expense(self, **overrides):
        payload = {
            "date": "2026-11-25",
            "category": "Material",
            "description": "Cement delivery",
            "amount": 1250.5,
            "project_id": "PRJ-987654",
            "vendor": "Building Supply Co.",
            "payment_method": "UPI",
            "notes": "",
        }
        payload.update(overrides)
        return self.request("/api/expenses", "POST", payload)

    def test_create_update_list_and_delete_expense(self):
        status, created = self.create_expense()
        self.assertEqual(status, 201)
        self.assertEqual(created["id"], "EXP-001")
        self.assertEqual(created["project_name"], "Expense test project")
        self.assertEqual(self.request("/api/expenses")[1], [created])

        status, updated = self.request(
            "/api/expenses/EXP-001", "PUT", {"amount": 2000, "category": "Equipment"}
        )
        self.assertEqual(status, 200)
        self.assertEqual(updated["amount"], 2000)
        self.assertEqual(updated["category"], "Equipment")

        self.assertEqual(self.request("/api/expenses/EXP-001", "DELETE")[0], 200)
        self.assertEqual(self.request("/api/expenses")[1], [])

    def test_rejects_small_amount_and_unknown_project(self):
        status, error = self.create_expense(amount=0.001)
        self.assertEqual(status, 400)
        self.assertIn("at least 0.01", error["error"])

        status, error = self.create_expense(project_id="PRJ-404")
        self.assertEqual(status, 400)
        self.assertIn("existing project", error["error"])

    def test_project_with_expense_cannot_be_deleted(self):
        self.assertEqual(self.create_expense()[0], 201)
        status, error = self.request("/api/projects/PRJ-987654", "DELETE")
        self.assertEqual(status, 409)
        self.assertIn("expenses", error["error"])

        self.assertEqual(self.request("/api/expenses/EXP-001", "DELETE")[0], 200)
        self.assertEqual(self.request("/api/projects/PRJ-987654", "DELETE")[0], 200)


if __name__ == "__main__":
    unittest.main()
