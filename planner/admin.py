from django.contrib import admin

from .models import PlannerSectionConfig


@admin.register(PlannerSectionConfig)
class PlannerSectionConfigAdmin(admin.ModelAdmin):
    list_display = ("slot_id", "label", "active", "position")
    list_editable = ("label", "active")
    ordering = ("position",)
