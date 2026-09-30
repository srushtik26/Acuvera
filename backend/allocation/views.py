"""
Allocation API views.
"""
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAuthenticatedViaJWT, IsNurseOrAdmin, IsDoctor


class SuggestDoctorView(APIView):
    """POST /api/allocation/suggest/{encounter_id}/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def post(self, request, encounter_id):
        from allocation.engine import suggest_doctor
        result = suggest_doctor(str(encounter_id))
        if not result["success"]:
            return err(result["error"], 404)
        return ok(result)


class CandidatesListView(APIView):
    """GET /api/allocation/candidates/{encounter_id}/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request, encounter_id):
        from core.models import Encounter, User
        from core.serializers import UserSerializer
        from allocation.engine import get_candidate_doctors
        
        try:
            enc = Encounter.objects.get(pk=encounter_id, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found", 404)
            
        candidates = get_candidate_doctors(str(enc.department_id))
        
        # Prepare response with workload data
        data = []
        for c in candidates:
            doc_data = UserSerializer(c["doctor"]).data
            doc_data["workload_score"] = c["workload"]
            # Raw count of active (assigned + in_progress + escalated) cases for display
            from core.models import Encounter as Enc
            doc_data["active_case_count"] = Enc.objects.filter(
                assigned_doctor_id=c["doctor"].id,
                status__in=("assigned", "in_progress", "escalated"),
                is_deleted=False,
            ).count()
            data.append(doc_data)
            
        return ok(data)


class ConfirmAllocationView(APIView):
    """POST /api/allocation/confirm/"""
    permission_classes = [IsNurseOrAdmin]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        to_doctor_id = request.data.get("to_doctor_id")
        reason = request.data.get("reason", "manual_confirm")

        if not encounter_id or not to_doctor_id:
            return err("encounter_id and to_doctor_id are required.", 400)

        floor = request.data.get("floor")
        room_number = request.data.get("room_number")
        bed_number = request.data.get("bed_number")

        from allocation.engine import try_assign_doctor
        success = try_assign_doctor(
            str(encounter_id), str(to_doctor_id),
            reason=reason,
            requested_by=request.acuvera_user,
            request=request,
            floor=floor,
            room_number=room_number,
            bed_number=bed_number,
        )
        if not success:
            return err("Assignment failed — encounter may already be assigned or doctor unavailable.", 409)

        from core.models import Encounter
        from core.serializers import EncounterSerializer
        enc = Encounter.objects.get(pk=encounter_id)
        return ok(EncounterSerializer(enc).data)


class RespondAllocationView(APIView):
    """POST /api/allocation/respond/ — doctor accept or reject."""
    permission_classes = [IsDoctor]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        accepted = request.data.get("accepted")  # true=accept, false=reject
        rejection_reason = request.data.get("rejection_reason", "")

        if encounter_id is None or accepted is None:
            return err("encounter_id and accepted (true/false) are required.", 400)

        if accepted:
            # Doctor confirms — move encounter to in_progress
            from core.models import Encounter
            from core.serializers import EncounterSerializer
            try:
                from django.db import transaction
                with transaction.atomic():
                    enc = Encounter.objects.select_for_update().get(pk=encounter_id, is_deleted=False)
                    if str(enc.assigned_doctor_id) != str(request.acuvera_user.id):
                        return err("This encounter is not assigned to you.", 403)
                    enc.status = "in_progress"
                    enc.version += 1
                    enc.save()
                from core.audit import log_audit
                log_audit("allocation.accept", "encounter", enc.id, request.acuvera_user,
                          None, None, request)
                return ok(EncounterSerializer(enc).data)
            except Encounter.DoesNotExist:
                return err("Encounter not found.", 404)
        else:
            # Doctor rejects
            if not rejection_reason:
                return err("rejection_reason is required when rejecting.", 400)
            from allocation.engine import handle_rejection
            result = handle_rejection(
                str(encounter_id),
                str(request.acuvera_user.id),
                rejection_reason,
                requested_by=request.acuvera_user,
                request=request,
            )
            if not result["success"]:
                return err(result["error"], 400)
            return ok(result)


class ReferDoctorView(APIView):
    """POST /api/allocation/refer/ — doctor hands off their case to a suggested or chosen doctor."""
    permission_classes = [IsDoctor]

    def post(self, request):
        encounter_id = request.data.get("encounter_id")
        to_doctor_id = request.data.get("to_doctor_id")

        if not encounter_id or not to_doctor_id:
            return err("encounter_id and to_doctor_id are required.", 400)

        from core.models import Encounter
        from core.serializers import EncounterSerializer
        try:
            enc = Encounter.objects.get(pk=encounter_id, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        # Prevent self-referral
        if str(to_doctor_id) == str(request.acuvera_user.id):
            return err("You cannot refer a patient to yourself.", 400)

        # Only the currently assigned doctor can refer
        if enc.assigned_doctor_id and str(enc.assigned_doctor_id) != str(request.acuvera_user.id):
            return err("You can only refer cases that are assigned to you.", 403)

        from allocation.engine import try_assign_doctor
        success = try_assign_doctor(
            str(encounter_id), str(to_doctor_id),
            reason="doctor_referral",
            requested_by=request.acuvera_user,
            request=request,
        )
        if not success:
            return err("Referral failed — doctor may be unavailable.", 409)

        enc.refresh_from_db()
        return ok(EncounterSerializer(enc).data)
