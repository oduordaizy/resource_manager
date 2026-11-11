from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token

from equipment.views import BookingViewSet, CurrentUserView, RegisterView, ResourceViewSet

router = DefaultRouter()
router.register("resources", ResourceViewSet, basename="resource")
router.register("bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view(), name="register"),
    path("api/auth/token/", obtain_auth_token, name="api-token"),
    path("api/auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("api/", include(router.urls)),
]
