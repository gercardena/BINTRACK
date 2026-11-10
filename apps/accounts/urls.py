from django.urls import path
from .views import RegisterView, LoginView, SubscriptionStatusView
from .views import ChangePasswordView, UserProfileView
from .management_views import AccountManagementView, SecondaryDetailView


urlpatterns = [
    path("cuenta/", AccountManagementView.as_view(), name="account_management"),
    path("cuenta/usuarios/<int:pk>/", SecondaryDetailView.as_view(), name="secondary_detail"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("suscripcion/estado/", SubscriptionStatusView.as_view(), name="suscripcion_estado"),
    path("user/profile/", UserProfileView.as_view(), name="user_profile"),
    path("user/change-password/", ChangePasswordView.as_view(), name="change_password"),
]
