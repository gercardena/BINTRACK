from django.contrib import admin
from .models import BinType, Cliente, BinMovement

admin.site.register(BinType)
admin.site.register(Cliente)
admin.site.register(BinMovement)