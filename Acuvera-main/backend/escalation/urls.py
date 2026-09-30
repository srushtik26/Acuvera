from django.urls import path
from escalation.views import TriggerEscalationView, AcknowledgeEscalationView, EscalationEventsView

urlpatterns = [
    path("escalation/trigger/", TriggerEscalationView.as_view()),
    path("escalation/acknowledge/", AcknowledgeEscalationView.as_view()),
    path("escalation/events/", EscalationEventsView.as_view()),
]
