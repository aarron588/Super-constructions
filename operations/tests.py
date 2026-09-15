import json
from datetime import timedelta

from django.test import Client as HttpClient, TestCase
from django.utils import timezone

from .models import AttendanceRecord, Client, Employee, Invoice, Project


class ApiWorkflowTests(TestCase):
    def setUp(self):
        self.client = HttpClient()

    def _post(self, url, payload):
        return self.client.post(url, data=json.dumps(payload), content_type="application/json")

    def test_bootstrap_admin_registration_and_login(self):
        response = self._post(
            "/api/auth/register",
            {"username": "admin", "password": "pass12345", "role": "admin", "hourly_rate": "50"},
        )
        self.assertEqual(response.status_code, 201)

        login_response = self._post("/api/auth/login", {"username": "admin", "password": "pass12345"})
        self.assertEqual(login_response.status_code, 200)

        dashboard_response = self.client.get("/api/dashboard")
        self.assertEqual(dashboard_response.status_code, 200)

    def test_attendance_approval_and_invoice_generation(self):
        self._post("/api/auth/register", {"username": "admin", "password": "pass12345", "role": "admin"})
        self._post("/api/auth/login", {"username": "admin", "password": "pass12345"})

        worker_resp = self._post(
            "/api/auth/register",
            {"username": "worker", "password": "pass12345", "role": "worker", "hourly_rate": "15"},
        )
        worker_id = worker_resp.json()["data"]["employee_id"]

        client_resp = self._post("/api/clients", {"name": "Acme"})
        client_id = client_resp.json()["data"]["id"]

        project_resp = self._post(
            "/api/projects",
            {"name": "Tower", "client_id": client_id, "start_date": timezone.now().date().isoformat()},
        )
        project_id = project_resp.json()["data"]["id"]

        attendance_resp = self._post("/api/attendance", {"employee_id": worker_id, "project_id": project_id})
        record_id = attendance_resp.json()["data"]["id"]

        record = AttendanceRecord.objects.get(id=record_id)
        record.check_out = record.check_in + timedelta(hours=8)
        record.save(update_fields=["check_out", "updated_at"])

        approve_resp = self._post(f"/api/attendance/{record_id}/approve", {"action": "approve"})
        self.assertEqual(approve_resp.status_code, 200)

        invoice_resp = self._post(
            "/api/invoices/generate-from-attendance",
            {
                "client_id": client_id,
                "project_id": project_id,
                "start_date": timezone.now().date().isoformat(),
                "end_date": timezone.now().date().isoformat(),
                "due_days": 15,
                "tax_rate": "10",
            },
        )
        self.assertEqual(invoice_resp.status_code, 201)

        invoice = Invoice.objects.get(id=invoice_resp.json()["data"]["invoice_id"])
        self.assertGreater(invoice.items.count(), 0)
        self.assertGreater(invoice.total_amount, 0)

        pdf_response = self.client.get(f"/api/invoices/{invoice.id}/pdf")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")

    def test_monthly_attendance_lock_blocks_updates(self):
        self._post("/api/auth/register", {"username": "admin", "password": "pass12345", "role": "admin"})
        self._post("/api/auth/login", {"username": "admin", "password": "pass12345"})

        self._post(
            "/api/attendance/lock",
            {"month": timezone.now().strftime("%Y-%m")},
        )

        db_client = Client.objects.create(name="Client")
        project = Project.objects.create(name="Project", client=db_client, start_date=timezone.now().date())
        worker_user_response = self._post(
            "/api/auth/register",
            {"username": "worker2", "password": "pass12345", "role": "worker"},
        )

        worker_employee = Employee.objects.get(id=worker_user_response.json()["data"]["employee_id"])
        locked_record = AttendanceRecord.objects.create(
            employee=worker_employee,
            project=project,
            check_in=timezone.now(),
        )

        checkout_resp = self._post(f"/api/attendance/{locked_record.id}/check-out", {})
        self.assertEqual(checkout_resp.status_code, 409)
