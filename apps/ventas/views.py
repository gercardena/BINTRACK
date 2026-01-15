from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import HasActiveSubscription


class VentaListView(APIView):
    permission_classes = [
        IsAuthenticated,
        HasActiveSubscription
    ]

    def get(self, request):
        return Response(
            {
                "message": "Acceso autorizado a ventas",
                "user": request.user.username
            }
        )