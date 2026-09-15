from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Employee(TimeStampedModel):
    ROLE_ADMIN = "admin"
    ROLE_ACCOUNTANT = "accountant"
    ROLE_SITE_MANAGER = "site_manager"
    ROLE_WORKER = "worker"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_ACCOUNTANT, "Accountant"),
        (ROLE_SITE_MANAGER, "Site Manager"),
        (ROLE_WORKER, "Worker"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="employee")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_WORKER)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.role})"


class Client(TimeStampedModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Project(TimeStampedModel):
    name = models.CharField(max_length=255)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="projects")
    description = models.TextField(blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class WorkShift(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="shifts")
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="shifts")
    shift_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()


class AttendanceLock(TimeStampedModel):
    month = models.DateField(unique=True, help_text="Use first day of month for lock period")
    locked_by = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="attendance_locks")

    def __str__(self):
        return self.month.strftime("%Y-%m")


class AttendanceRecord(TimeStampedModel):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="attendance_records")
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="attendance_records")
    check_in = models.DateTimeField()
    check_out = models.DateTimeField(null=True, blank=True)
    corrected_check_in = models.DateTimeField(null=True, blank=True)
    corrected_check_out = models.DateTimeField(null=True, blank=True)
    correction_reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    approved_by = models.ForeignKey(
        Employee, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_attendance_records"
    )

    class Meta:
        ordering = ["-check_in"]

    @property
    def effective_check_in(self):
        return self.corrected_check_in or self.check_in

    @property
    def effective_check_out(self):
        return self.corrected_check_out or self.check_out

    @property
    def duration_hours(self):
        end_time = self.effective_check_out
        if not end_time:
            return Decimal("0.00")
        duration = end_time - self.effective_check_in
        hours = Decimal(duration.total_seconds()) / Decimal("3600")
        return hours.quantize(Decimal("0.01"))


class Expense(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="expenses")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=100)
    incurred_on = models.DateField()
    notes = models.TextField(blank=True)


class Invoice(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_SENT = "sent"
    STATUS_PARTIAL = "partial"
    STATUS_PAID = "paid"
    STATUS_OVERDUE = "overdue"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SENT, "Sent"),
        (STATUS_PARTIAL, "Partially Paid"),
        (STATUS_PAID, "Paid"),
        (STATUS_OVERDUE, "Overdue"),
    ]

    number = models.CharField(max_length=30, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="invoices")
    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="invoices")
    issued_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_estimate = models.BooleanField(default=False)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notes = models.TextField(blank=True)

    @property
    def subtotal(self):
        value = self.items.aggregate(total=Sum("line_total"))["total"]
        return value or Decimal("0.00")

    @property
    def tax_amount(self):
        return (self.subtotal * self.tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    @property
    def total_amount(self):
        return self.subtotal + self.tax_amount

    @property
    def paid_amount(self):
        value = self.payments.aggregate(total=Sum("amount"))["total"]
        return value or Decimal("0.00")

    @property
    def balance_due(self):
        return self.total_amount - self.paid_amount


class InvoiceItem(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.line_total = (self.quantity * self.unit_price).quantize(Decimal("0.01"))
        super().save(*args, **kwargs)


class Payment(TimeStampedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_on = models.DateField(default=timezone.now)
    method = models.CharField(max_length=50, blank=True)
    reference = models.CharField(max_length=100, blank=True)


class AuditLog(TimeStampedModel):
    actor = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    target_type = models.CharField(max_length=100)
    target_id = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)


class AttendanceBillingLink(TimeStampedModel):
    attendance_record = models.OneToOneField(AttendanceRecord, on_delete=models.CASCADE, related_name="billing_link")
    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE, related_name="attendance_links")
