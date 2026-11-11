from django.contrib import admin
from django.urls import include, path
from drf_spectacular.utils import extend_schema
from rest_framework.routers import DefaultRouter
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from equipment.views import BookingViewSet, CurrentUserView, RegisterView, ResourceViewSet


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class TokenObtainView(ObtainAuthToken):
    @extend_schema(
        request=AuthTokenSerializer,
        responses=TokenResponseSerializer,
        description="Exchange a username and password for a DRF token.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


router = DefaultRouter()
router.register("resources", ResourceViewSet, basename="resource")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/token/", TokenObtainView.as_view(), name="api-token"),
    path("api/auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("api/", include(router.urls)),
]
