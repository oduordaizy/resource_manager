from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsManagerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_manager_or_admin
        )


class IsBookingOwnerOrManager(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.user.id or request.user.is_manager_or_admin
