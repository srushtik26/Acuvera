from django.urls import path
from analytics.views import (
    AdminOverviewView, DoctorUtilizationView, AdminConfigView,
    ForecastView, FinancialImpactView, StarvationAlertsView, AnalyticsSnapshotHistoryView,
)

urlpatterns = [
    path("admin/overview/", AdminOverviewView.as_view()),
    path("admin/doctor/<uuid:doctor_id>/utilization/", DoctorUtilizationView.as_view()),
    path("admin/config/", AdminConfigView.as_view()),
    path("admin/forecast/", ForecastView.as_view()),
    path("admin/financial-impact/", FinancialImpactView.as_view()),
    path("admin/starvation-alerts/", StarvationAlertsView.as_view()),
    path("admin/snapshots/", AnalyticsSnapshotHistoryView.as_view()),
]
