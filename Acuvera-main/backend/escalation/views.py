"""
Escalation API views.
"""
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAuthenticatedViaJWT, IsNurse


class TriggerEscalationView(APIView):
    """POST /api/escalation/trigger/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        escalation_type = request.data.get("type")
        if not encounter_id or not escalation_type:
            return err("encounter_id and type are required.", 400)

        from escalation.engine import trigger_escalation
        result = trigger_escalation(
            encounter_id=str(encounter_id),
            escalation_type=escalation_type,
            triggered_by=request.acuvera_user,
            request=request,
        )
        if not result["success"]:
            return err(result["error"], 400)
        return ok(result, status=201)


class AcknowledgeEscalationView(APIView):
    """POST /api/escalation/acknowledge/ — nurses only"""
    permission_classes = [IsNurse]

    def post(self, request):
        event_id = request.data.get("event_id")
        encounter_id = request.data.get("encounter_id")

        if encounter_id and not event_id:
            from core.models import EscalationEvent
            event = EscalationEvent.objects.filter(
                encounter_id=encounter_id, 
                acknowledged_at__isnull=True,
                type="code_blue"
            ).order_by("-timestamp").first()
            if not event:
                return err("Already acknowledged or no active code blue for this encounter.", 400)
            event_id = str(event.id)

        if not event_id:
            return err("event_id or encounter_id is required.", 400)

        from escalation.engine import acknowledge_escalation
        result = acknowledge_escalation(
            event_id=str(event_id),
            acknowledging_nurse=request.acuvera_user,
            request=request,
        )
        if not result["success"]:
            return err(result["error"], 400)
        return ok({
            "status": "acknowledged",
            "acknowledged_by": request.acuvera_user.full_name,
            "acknowledged_at": result.get("acknowledged_at"),
            "response_time_seconds": result.get("response_time_seconds"),
            "sla_breached": result.get("sla_breached"),
        })


class EscalationEventsView(APIView):
    """GET /api/escalation/events/?department=<id>"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        from core.models import EscalationEvent

        qs = EscalationEvent.objects.select_related(
            "encounter", "encounter__patient", "triggered_by", "acknowledged_by"
        ).order_by("-timestamp")
        dept_id = request.query_params.get("department")
        if dept_id:
            qs = qs.filter(encounter__department_id=dept_id)

        data = []
        for ev in qs:
            data.append({
                "id": str(ev.id),
                "encounter_id": str(ev.encounter_id),
                "type": ev.type,
                "patient_name": ev.encounter.patient.name if ev.encounter and ev.encounter.patient else None,
                "triggered_by_id": str(ev.triggered_by_id) if ev.triggered_by_id else None,
                "triggered_by_name": ev.triggered_by.full_name if ev.triggered_by else None,
                "acknowledged_by_id": str(ev.acknowledged_by_id) if ev.acknowledged_by_id else None,
                "acknowledged_by_name": ev.acknowledged_by.full_name if ev.acknowledged_by else None,
                "acknowledged_at": ev.acknowledged_at.isoformat() if ev.acknowledged_at else None,
                "response_time_seconds": ev.response_time,
                "sla_breached": ev.sla_breached,
                "timestamp": ev.timestamp.isoformat(),
            })
        return ok(data)
