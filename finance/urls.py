from django.urls import path

from . import views

urlpatterns = [
    path("finance/unlock/", views.finance_unlock, name="finance-unlock"),
    path("finance/", views.finance_overview, name="finance-overview"),
    path("finance/incomes/<int:entry_id>/", views.finance_income_detail, name="finance-income-detail"),
]
