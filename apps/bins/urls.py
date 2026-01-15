# apps/bins/urls.py

from django.urls import path
from .views import BinListView

urlpatterns = [
    path("bins/", BinListView.as_view(), name="bins-list"),
]