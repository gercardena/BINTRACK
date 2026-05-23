from django.contrib import admin

from .models import BinType, BinMovement


admin.site.register(BinType)
admin.site.register(BinMovement)