from django.conf import settings
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.users.api.views import (
    UserViewSet, 
    SendOTPView, 
    VerifyOTPView, 
    PhoneLoginView,
    CustomTokenObtainPairView,
    BranchListView,
    PositionListView
)
from apps.surveys.api.views import (
    SurveyViewSet,
    SurveySessionViewSet,
    CurrentSessionView,
    DownloadUserCertificatePDFView,
    GetUserCertificateDataView
)
from apps.surveys.api.moderator_views import (
    ModeratorUserViewSet,
    ModeratorSurveyStatsViewSet,
    ModeratorDashboardView
)

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("surveys", SurveyViewSet, basename='survey')
router.register("sessions", SurveySessionViewSet, basename='surveysession')

# Moderator endpoints
router.register("moderator/users", ModeratorUserViewSet, basename='moderator-user')
router.register("moderator/surveys", ModeratorSurveyStatsViewSet, basename='moderator-survey')

app_name = "api"
urlpatterns = [
    # Authentication endpoints
    path("auth/send-otp/", SendOTPView.as_view(), name="send-otp"),
    path("auth/verify-otp/", VerifyOTPView.as_view(), name="verify-otp"),
    path("auth/login/", PhoneLoginView.as_view(), name="phone-login"),
    path("auth/token/", CustomTokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    
    # Survey endpoints
    path("current-session/", CurrentSessionView.as_view(), name="current-session"),
    
    # Moderator endpoints
    path("moderator/dashboard/", ModeratorDashboardView.as_view(), name="moderator-dashboard"),
    
    # User data endpoints
    path("branches/", BranchListView.as_view(), name="branches-list"),
    path("positions/", PositionListView.as_view(), name="positions-list"),
    path("certificate/", include("apps.surveys.urls", namespace="surveys")),
    
    # Include router URLs
    path("", include(router.urls)),
]
