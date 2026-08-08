from django.urls import path

from . import export_views, views

urlpatterns = [
    path("export/", export_views.export_all_data, name="export-all-data"),
    path("import/", export_views.import_all_data, name="import-all-data"),
    path("weeks/", views.weeks_list, name="weeks-list"),
    path("week-summaries/", views.week_summaries, name="week-summaries"),
    path("weeks/<str:start_date>/", views.week_detail, name="week-detail"),
]
