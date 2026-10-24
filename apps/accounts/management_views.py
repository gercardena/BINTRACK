from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UsuarioAsociado
from .permissions.account_owner import IsAccountOwner
from .management_serializers import SecondaryCreateSerializer, SecondaryUpdateSerializer, SecondarySerializer
from .services.account_management import account_summary, create_secondary, update_secondary


class AccountManagementView(APIView):
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def get(self, request):
        summary = account_summary(request.user)
        relations = UsuarioAsociado.objects.filter(titular=request.user).select_related("usuario_asociado").order_by("id")
        summary["usuarios"] = SecondarySerializer(relations, many=True).data
        return Response(summary)

    def post(self, request):
        serializer = SecondaryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            relation = create_secondary(request.user, dict(serializer.validated_data))
        except IntegrityError:
            return Response({"detail": "No se pudo crear el usuario. Comprueba que el nombre esté disponible."}, status=400)
        return Response(SecondarySerializer(relation).data, status=status.HTTP_201_CREATED)


class SecondaryDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAccountOwner]

    def put(self, request, pk):
        relation = get_object_or_404(
            UsuarioAsociado.objects.select_related("usuario_asociado").filter(titular=request.user), pk=pk,
        )
        serializer = SecondaryUpdateSerializer(data=request.data, context={"secondary": relation.usuario_asociado})
        serializer.is_valid(raise_exception=True)
        relation = update_secondary(request.user, pk, dict(serializer.validated_data))
        return Response(SecondarySerializer(relation).data)
