"""Core API URL patterns."""
from django.urls import path
from core.views import (
    WhoAmIView, RegisterUserView, LoginView, ForceAdminView,
    PatientListCreateView, PatientDetailView,
    EncounterListCreateView, EncounterDetailView, EncounterAssignView, EncounterLocationUpdateView,
    DepartmentListView, DepartmentDetailView, DoctorListView, UserAvailabilityView,
    StaffListView, StaffDetailView,
)
from core.assessment_views import AssessmentView, CompleteAssessmentView
from core.insight_views import InsightView
from core.simulation_views import SimulateView
from core.ambulance_views import AmbulancePreRegisterView, IncomingAmbulanceListView
from core.clear_views import ClearEncountersView
from core.admin_insight_views import AdminInsightChatView

urlpatterns = [
    path("auth/whoami/", WhoAmIView.as_view()),
    path("auth/register/", RegisterUserView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/force-admin/", ForceAdminView.as_view()),
    path("patients/", PatientListCreateView.as_view()),
    path("patients/<uuid:pk>/", PatientDetailView.as_view()),
    path("encounters/", EncounterListCreateView.as_view()),
    path("encounters/<uuid:pk>/", EncounterDetailView.as_view()),
    path("encounters/<uuid:pk>/assign/", EncounterAssignView.as_view()),
    path("encounters/<uuid:pk>/location/", EncounterLocationUpdateView.as_view()),
    path("departments/", DepartmentListView.as_view()),
    path("departments/<uuid:pk>/", DepartmentDetailView.as_view()),
    path("doctors/", DoctorListView.as_view()),
    path("users/<uuid:pk>/availability/", UserAvailabilityView.as_view()),
    
    # Admin Staff Management
    path("admin/staff/", StaffListView.as_view()),
    path("admin/staff/<uuid:pk>/", StaffDetailView.as_view()),

    # Assessment
    path("encounters/<uuid:pk>/assessment/", AssessmentView.as_view()),
    path("encounters/<uuid:pk>/assessment/complete/", CompleteAssessmentView.as_view()),

    # AI Clinical Insight
    path("encounters/<uuid:pk>/insight/", InsightView.as_view()),

    # Ambulance Pre-Triage
    path("encounters/ambulance/", AmbulancePreRegisterView.as_view()),
    path("encounters/incoming/", IncomingAmbulanceListView.as_view()),

    # Live ER Simulation
    path("admin/simulate/", SimulateView.as_view()),

    # Admin: Clear all encounters (soft-delete)
    path("admin/clear-encounters/", ClearEncountersView.as_view()),

    # Operational Intelligence (Q&A for hospital ops)
    path("admin/insight-chat/", AdminInsightChatView.as_view()),
]
