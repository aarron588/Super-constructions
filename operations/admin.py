from django.contrib import admin

from .models import (
    AttendanceBillingLink,
    AttendanceLock,
    AttendanceRecord,
    AuditLog,
    Client,
    Employee,
    Expense,
    Invoice,
    InvoiceItem,
    Payment,
    Project,
    WorkShift,
)

admin.site.register(Employee)
admin.site.register(Client)
admin.site.register(Project)
admin.site.register(WorkShift)
admin.site.register(AttendanceLock)
admin.site.register(AttendanceRecord)
admin.site.register(Expense)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Payment)
admin.site.register(AuditLog)
admin.site.register(AttendanceBillingLink)
