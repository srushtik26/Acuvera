from django.urls import path
from fhir_adapter.views import FHIRPatientView, FHIREncounterView, FHIRObservationView, FHIRTaskView

urlpatterns = [
    path("Patient", FHIRPatientView.as_view()),
    path("Encounter", FHIREncounterView.as_view()),
    path("Observation", FHIRObservationView.as_view()),
    path("Task", FHIRTaskView.as_view()),
]
