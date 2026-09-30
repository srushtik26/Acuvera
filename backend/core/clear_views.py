"""
Admin-only: Clear all encounters (soft-delete) and optionally patients.
POST /api/admin/clear-encounters/
"""
from rest_framework.views import APIView
from core.exceptions import ok, err
from core.permissions import IsAdmin
from core.audit import log_audit
import logging

logger = logging.getLogger("acuvera.admin.clear")


class ClearEncountersView(APIView):
    """
    POST /api/admin/clear-encounters/
    Body: { "mode": "encounters" | "all" }
      - "encounters" (default): soft-delete all encounters (marks is_deleted=True)
      - "all": soft-delete encounters AND hard-delete simulation patients (name not matching real patients)
    Admin only. Audit-logged.
    """
    permission_classes = [IsAdmin]

    def post(self, request):
        from core.models import Encounter, Patient
        mode = request.data.get("mode", "encounters")

        # Soft-delete all non-deleted encounters
        enc_qs = Encounter.objects.filter(is_deleted=False)
        enc_count = enc_qs.count()
        enc_qs.update(is_deleted=True)

        patient_count = 0
        if mode == "all":
            # Hard-delete patients that only have simulation encounters
            # (i.e. all their encounters are now deleted)
            from django.db.models import Count, Q
            sim_patients = Patient.objects.annotate(
                active_enc=Count('encounter', filter=Q(encounter__is_deleted=False))
            ).filter(active_enc=0)
            patient_count = sim_patients.count()
            sim_patients.delete()

        log_audit(
            "admin.clear_encounters", "system", None,
            request.acuvera_user, None, {"enc_count": enc_count, "patient_count": patient_count},
            request, metadata={"mode": mode}
        )

        logger.info(
            "Clear encounters: user=%s mode=%s enc_deleted=%d patients_deleted=%d",
            request.acuvera_user.username, mode, enc_count, patient_count
        )

        return ok({
            "encounters_cleared": enc_count,
            "patients_cleared": patient_count,
            "mode": mode,
        })
