from django.urls import path
from .views import RegisterView, LoginView, SubscriptionStatusView
from .views import UserProfileView


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("suscripcion/estado/", SubscriptionStatusView.as_view(), name="suscripcion_estado"),
    path("user/profile/", UserProfileView.as_view(), name="user_profile"),
]