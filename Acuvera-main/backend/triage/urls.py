from django.urls import path
from triage.views import AnalyzeTriageView

urlpatterns = [
    path("triage/<uuid:encounter_id>/analyze/", AnalyzeTriageView.as_view()),
]
