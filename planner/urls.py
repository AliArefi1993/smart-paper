from django.urls import path

from . import views

urlpatterns = [
    path("weeks/", views.weeks_list, name="weeks-list"),
    path("week-summaries/", views.week_summaries, name="week-summaries"),
    path("weeks/<str:start_date>/", views.week_detail, name="week-detail"),
]
