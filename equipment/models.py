from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Manager"
        MEMBER = "member", "Member"

    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)

    @property
    def is_manager_or_admin(self):
        return self.is_superuser or self.role in {self.Role.ADMIN, self.Role.MANAGER}


class Resource(models.Model):
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=160, blank=True)
    total_quantity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_quantity__gt=0),
                name="resource_quantity_positive",
            )
        ]

    def __str__(self):
        return self.name


class Booking(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    resource = models.ForeignKey(
        Resource, on_delete=models.PROTECT, related_name="bookings"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="bookings"
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.CONFIRMED
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_at", "id"]
        indexes = [
            models.Index(
                fields=["resource", "status", "start_at", "end_at"],
                name="booking_res_status_time_idx",
            ),
            models.Index(fields=["user", "start_at"], name="booking_user_start_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0), name="booking_quantity_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(end_at__gt=models.F("start_at")),
                name="booking_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.resource} ({self.start_at} – {self.end_at})"
