from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db.models import Sum
from rest_framework import serializers

from .models import Booking, Resource

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "role")
        read_only_fields = ("id", "role")


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password", "first_name", "last_name")
        read_only_fields = ("id",)

    def validate(self, attrs):
        validate_password(attrs["password"], user=User(**attrs))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class ResourceSerializer(serializers.ModelSerializer):
    available_quantity = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = (
            "id",
            "name",
            "description",
            "location",
            "total_quantity",
            "available_quantity",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "available_quantity")

    def get_available_quantity(self, resource):
        at = self.context.get("availability_at")
        if at is None:
            from django.utils import timezone

            at = timezone.now()
        reserved = (
            resource.bookings.filter(
                status=Booking.Status.CONFIRMED,
                start_at__lte=at,
                end_at__gt=at,
            ).aggregate(total=Sum("quantity"))["total"]
            or 0
        )
        return max(resource.total_quantity - reserved, 0)

    def validate_total_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        if self.instance is not None:
            max_reserved = self.instance.bookings.filter(
                status=Booking.Status.CONFIRMED
            ).aggregate(total=Sum("quantity"))["total"]
            if max_reserved is not None and value < max_reserved:
                # The exact concurrent peak is checked by the resource view.
                peak = self.context.get("reserved_peak", max_reserved)
                if value < peak:
                    raise serializers.ValidationError(
                        "Quantity cannot be lower than existing confirmed reservations."
                    )
        return value


class BookingSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    resource = serializers.PrimaryKeyRelatedField(
        queryset=Resource.objects.filter(is_active=True)
    )

    class Meta:
        model = Booking
        fields = (
            "id",
            "resource",
            "resource_name",
            "user",
            "username",
            "start_at",
            "end_at",
            "quantity",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "user", "status", "created_at", "updated_at")

    def validate_resource(self, resource):
        locked_resource = self.context.get("locked_resource")
        if locked_resource is not None and resource.pk != locked_resource.pk:
            raise serializers.ValidationError(
                "The resource changed while this booking was being processed."
            )
        return locked_resource or resource

    def validate(self, attrs):
        start_at = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end_at = attrs.get("end_at", getattr(self.instance, "end_at", None))
        quantity = attrs.get("quantity", getattr(self.instance, "quantity", 1))
        resource = attrs.get("resource", getattr(self.instance, "resource", None))

        if (
            self.instance is not None
            and "resource" in attrs
            and resource.pk != self.instance.resource_id
        ):
            raise serializers.ValidationError(
                {"resource": "A booking's resource cannot be changed."}
            )
        if start_at is None or end_at is None or end_at <= start_at:
            raise serializers.ValidationError(
                {"end_at": "End time must be later than start time."}
            )
        if quantity < 1:
            raise serializers.ValidationError(
                {"quantity": "Quantity must be greater than zero."}
            )
        if resource is None:
            raise serializers.ValidationError({"resource": "A resource is required."})
        if not resource.is_active:
            raise serializers.ValidationError(
                {"resource": "This resource is not available for booking."}
            )

        bookings = Booking.objects.filter(
            resource=resource,
            status=Booking.Status.CONFIRMED,
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        if self.instance is not None:
            bookings = bookings.exclude(pk=self.instance.pk)

        # Half-open ranges permit a booking to begin exactly when another ends.
        events = [(start_at, quantity), (end_at, -quantity)]
        for booking in bookings.only("start_at", "end_at", "quantity"):
            events.append((max(start_at, booking.start_at), booking.quantity))
            events.append((min(end_at, booking.end_at), -booking.quantity))
        events.sort(key=lambda event: (event[0], event[1]))
        in_use = 0
        peak = 0
        for _, change in events:
            in_use += change
            peak = max(peak, in_use)
        if peak > resource.total_quantity:
            raise serializers.ValidationError(
                {
                    "quantity": (
                        f"Only {resource.total_quantity} units exist; "
                        "this booking overlaps reservations that exceed capacity."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        return Booking.objects.create(user=self.context["request"].user, **validated_data)
