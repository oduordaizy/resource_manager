from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Booking, Resource
from .permissions import IsBookingOwnerOrManager, IsManagerOrAdmin
from .serializers import (
    BookingSerializer,
    RegistrationSerializer,
    ResourceSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [AllowAny]


class CurrentUserView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ResourceViewSet(viewsets.ModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if not self.request.user.is_manager_or_admin:
            queryset = queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            return [IsManagerOrAdmin()]
        return [IsAuthenticated()]

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        with transaction.atomic():
            resource = get_object_or_404(
                Resource.objects.select_for_update(), pk=kwargs.get("pk")
            )
            self.check_object_permissions(request, resource)
            serializer = self.get_serializer(
                resource,
                data=request.data,
                partial=partial,
                context={
                    **self.get_serializer_context(),
                    "reserved_peak": self._reserved_peak(resource),
                },
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        resource = self.get_object()
        with transaction.atomic():
            resource = Resource.objects.select_for_update().get(pk=resource.pk)
            if resource.bookings.exists():
                raise ValidationError(
                    "Resources with booking history cannot be deleted; deactivate them instead."
                )
            self.perform_destroy(resource)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _reserved_peak(resource):
        events = []
        for booking in resource.bookings.filter(
            status=Booking.Status.CONFIRMED
        ).only("start_at", "end_at", "quantity"):
            events.append((booking.start_at, booking.quantity))
            events.append((booking.end_at, -booking.quantity))
        events.sort(key=lambda event: (event[0], event[1]))
        in_use = peak = 0
        for _, change in events:
            in_use += change
            peak = max(peak, in_use)
        return peak


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated, IsBookingOwnerOrManager]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        queryset = Booking.objects.select_related("resource", "user")
        if self.request.user.is_manager_or_admin:
            return queryset
        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        resource_id = request.data.get("resource")
        with transaction.atomic():
            resource = get_object_or_404(
                Resource.objects.select_for_update().filter(is_active=True),
                pk=resource_id,
            )
            serializer = self.get_serializer(
                data=request.data,
                context={**self.get_serializer_context(), "locked_resource": resource},
            )
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        booking_id = kwargs.get("pk")
        booking = get_object_or_404(
            self.get_queryset().select_related(None), pk=booking_id
        )
        self.check_object_permissions(request, booking)
        with transaction.atomic():
            resource = Resource.objects.select_for_update().get(pk=booking.resource_id)
            booking = Booking.objects.select_for_update().get(pk=booking_id)
            serializer = self.get_serializer(
                booking,
                data=request.data,
                partial=partial,
                context={**self.get_serializer_context(), "locked_resource": resource},
            )
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)

    def perform_destroy(self, instance):
        if instance.status == Booking.Status.CANCELLED:
            return
        instance.status = Booking.Status.CANCELLED
        instance.save(update_fields=["status", "updated_at"])

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            booking = get_object_or_404(
                self.get_queryset().select_related(None), pk=kwargs["pk"]
            )
            self.check_object_permissions(request, booking)
            Resource.objects.select_for_update().get(pk=booking.resource_id)
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            self.perform_destroy(booking)
        return Response(status=status.HTTP_204_NO_CONTENT)
