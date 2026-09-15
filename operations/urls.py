from django.urls import path

from . import views

urlpatterns = [
    path("auth/register", views.register, name="register"),
    path("auth/login", views.login_view, name="login"),
    path("auth/logout", views.logout_view, name="logout"),
    path("employees", views.employees, name="employees"),
    path("clients", views.clients, name="clients"),
    path("projects", views.projects, name="projects"),
    path("expenses", views.expenses, name="expenses"),
    path("attendance", views.attendance, name="attendance"),
    path("attendance/<int:record_id>/check-out", views.attendance_checkout, name="attendance_checkout"),
    path("attendance/<int:record_id>/correct", views.attendance_correct, name="attendance_correct"),
    path("attendance/<int:record_id>/approve", views.attendance_approve, name="attendance_approve"),
    path("attendance/lock", views.attendance_lock, name="attendance_lock"),
    path("invoices", views.invoices, name="invoices"),
    path("invoices/generate-from-attendance", views.invoice_generate_from_attendance, name="invoice_generate_from_attendance"),
    path("invoices/<int:invoice_id>/items", views.invoice_add_item, name="invoice_add_item"),
    path("invoices/<int:invoice_id>/send", views.invoice_mark_sent, name="invoice_mark_sent"),
    path("invoices/<int:invoice_id>/payments", views.invoice_add_payment, name="invoice_add_payment"),
    path("invoices/<int:invoice_id>/pdf", views.invoice_pdf, name="invoice_pdf"),
    path("invoices/reminders", views.invoice_reminders, name="invoice_reminders"),
    path("dashboard", views.dashboard, name="dashboard"),
    path("reports/summary", views.reports_summary, name="reports_summary"),
]
