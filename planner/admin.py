from django.contrib import admin

from .models import DayScheduleEntry, PlannerSectionConfig


@admin.register(DayScheduleEntry)
class DayScheduleEntryAdmin(admin.ModelAdmin):
    list_display = ("day", "start_minutes", "end_minutes", "title", "section_id")
    list_filter = ("section_id",)
    search_fields = ("title", "note")


@admin.register(PlannerSectionConfig)
class PlannerSectionConfigAdmin(admin.ModelAdmin):
    list_display = ("slot_id", "label", "active", "position")
    list_editable = ("label", "active")
    ordering = ("position",)
