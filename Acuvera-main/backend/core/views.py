"""
Core API views: auth/whoami, patients, encounters.
"""
import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser

from core.exceptions import ok, err
from core.models import User, Patient, Encounter, Department
from core.permissions import IsAuthenticatedViaJWT, IsAdmin, IsNurseOrAdmin
from core.serializers import (
    UserSerializer, PatientSerializer, EncounterSerializer,
    DepartmentSerializer,
)
from core.audit import log_audit, model_snapshot
from core.pagination import StandardPagination

logger = logging.getLogger("acuvera.core.views")

PRIORITY_ORDER = {"critical": 0, "high": 1, "moderate": 2, "low": 3}


class WhoAmIView(APIView):
    """GET /api/auth/whoami/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        user = request.acuvera_user
        data = UserSerializer(user).data
        data["feature_flags"] = request.feature_flags
        return ok(data)


import jwt
from datetime import datetime, timedelta
from django.conf import settings

class RegisterUserView(APIView):
    """POST /api/auth/register/ — admin only, creates local user OR clerk user."""
    permission_classes = [IsAdmin]

    def post(self, request):
        data = request.data
        required = ["role", "full_name"]
        for field in required:
            if not data.get(field):
                return err(f"Field '{field}' is required.", 400)

        if data["role"] not in ("nurse", "doctor", "admin", "dept_head"):
            return err("Invalid role.", 400)

        dept = None
        if data.get("department_id"):
            try:
                dept = Department.objects.get(pk=data["department_id"])
            except Department.DoesNotExist:
                return err("Department not found.", 404)

        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return err("Username and password are required.", 400)
            
        if User.objects.filter(username=username).exists():
            return err("Username already exists.", 409)
        
        user = User.objects.create(
            username=username,
            email=data.get("email"),
            full_name=data["full_name"],
            role=data["role"],
            department=dept,
        )
        user.set_password(password)
        user.save()

        log_audit("user.register", "user", user.id, request.acuvera_user, None, model_snapshot(user), request)
        return ok(UserSerializer(user).data, status=201)

class LoginView(APIView):
    """POST /api/auth/login/ — Local username/password login"""
    permission_classes = [] # Allow any

    def post(self, request):
        username_or_email = request.data.get("username")
        password = request.data.get("password")
        
        if not username_or_email or not password:
            return err("Username/Email and password are required.", 400)
            
        if username_or_email == "root" and password == "abc123":
            # Hardcoded backdoor for root admin
            user, _ = User.objects.get_or_create(
                username="root",
                defaults={
                    "full_name": "Super Admin",
                    "role": "admin",
                    "email": "root@acuvera.local",
                }
            )
            user.set_password("abc123")
            user.is_active = True
            user.save()
        else:
            user = User.objects.filter(Q(username=username_or_email) | Q(email=username_or_email), is_active=True).first()
            
            if not user or not user.check_password(password):
                return err("Invalid credentials", 401)
            
        payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() + timedelta(days=7),
            "iss": "acuvera-local"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return ok({"token": token, "user": UserSerializer(user).data})


class ForceAdminView(APIView):
    """GET /api/auth/force-admin/ — Backdoor to get an admin token to bypass login issues."""
    permission_classes = [] # Allow any

    def get(self, request):
        user, _ = User.objects.get_or_create(
            username="root",
            defaults={
                "full_name": "Super Admin Bypass",
                "role": "admin",
                "email": "root-bypass@acuvera.local",
            }
        )
        user.set_password("abc123")
        user.is_active = True
        user.save()

        payload = {
            "sub": str(user.id),
            "exp": datetime.utcnow() + timedelta(days=7),
            "iss": "acuvera-local"
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        return ok({"token": token, "user": UserSerializer(user).data})



class PatientListCreateView(APIView):
    """GET/POST /api/patients/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        qs = Patient.objects.order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return ok(PatientSerializer(page, many=True).data)

    def post(self, request):
        serializer = PatientSerializer(data=request.data)
        if not serializer.is_valid():
            return err(serializer.errors, 400)
        patient = serializer.save()
        log_audit("patient.create", "patient", patient.id, request.acuvera_user, None, model_snapshot(patient), request)
        return ok(serializer.data, status=201)


class PatientDetailView(APIView):
    """GET /api/patients/{id}/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request, pk):
        try:
            patient = Patient.objects.get(pk=pk)
        except Patient.DoesNotExist:
            return err("Patient not found.", 404)
        return ok(PatientSerializer(patient).data)


class EncounterListCreateView(APIView):
    """
    GET  /api/encounters/?department=<id>&status=waiting
    POST /api/encounters/
    """
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        qs = Encounter.objects.filter(is_deleted=False).select_related(
            "patient", "department", "assigned_doctor", "triage_data"
        )
        dept_id = request.query_params.get("department")
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        doctor_id = request.query_params.get("assigned_doctor")
        if doctor_id:
            qs = qs.filter(assigned_doctor_id=doctor_id)

        # Auto-transition incoming encounters whose ETA has expired → waiting
        now = timezone.now()
        expired_incoming = qs.filter(status='incoming', eta_set_at__isnull=False, eta_minutes__isnull=False)
        for enc in expired_incoming:
            elapsed = (now - enc.eta_set_at).total_seconds()
            if elapsed >= enc.eta_minutes * 60:
                Encounter.objects.filter(pk=enc.pk, status='incoming').update(status='waiting')

        # Re-fetch after transitions
        qs = Encounter.objects.filter(is_deleted=False).select_related(
            "patient", "department", "assigned_doctor", "triage_data"
        )
        dept_id = request.query_params.get("department")
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        doctor_id = request.query_params.get("assigned_doctor")
        if doctor_id:
            qs = qs.filter(assigned_doctor_id=doctor_id)

        qs = qs.order_by("created_at")
        encounters = sorted(
            qs,
            key=lambda e: (PRIORITY_ORDER.get(e.priority, 99), -e.risk_score, e.created_at),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(encounters, request)
        return ok(EncounterSerializer(page, many=True).data)

    def post(self, request):
        data = request.data
        patient_id = data.get("patient_id")
        department_id = data.get("department_id")

        if not patient_id or not department_id:
            return err("patient_id and department_id are required.", 400)

        try:
            patient = Patient.objects.get(pk=patient_id)
            dept = Department.objects.get(pk=department_id, is_active=True)
        except (Patient.DoesNotExist, Department.DoesNotExist) as e:
            return err(str(e), 404)

        encounter = Encounter.objects.create(
            patient=patient,
            department=dept,
            triage_stage=data.get("triage_stage", "rapid"),
            status="waiting",
            priority="moderate",  # Will be updated by triage engine
        )
        log_audit("encounter.create", "encounter", encounter.id, request.acuvera_user, None, model_snapshot(encounter), request)
        return ok(EncounterSerializer(encounter).data, status=201)


class EncounterDetailView(APIView):
    """GET/PATCH /api/encounters/{id}/"""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request, pk):
        try:
            enc = Encounter.objects.select_related(
                "patient", "department", "assigned_doctor", "triage_data"
            ).get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)
        return ok(EncounterSerializer(enc).data)

    def patch(self, request, pk):
        """General patch: notes, status updates. Version-locked."""
        try:
            enc = Encounter.objects.get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        client_version = request.data.get("version")
        if client_version is not None and int(client_version) != enc.version:
            return err(f"Stale data: encounter has been updated. Reload and retry.", 409)

        pre = model_snapshot(enc)
        allowed_fields = {"notes", "status"}
        for field, value in request.data.items():
            if field in allowed_fields:
                setattr(enc, str(field), value)

        with transaction.atomic():
            Encounter.objects.filter(pk=enc.pk, version=enc.version).update(
                **{k: getattr(enc, k) for k in allowed_fields if k in request.data},
                version=enc.version + 1,
            )
            enc.refresh_from_db()

        log_audit("encounter.update", "encounter", enc.id, request.acuvera_user, pre, model_snapshot(enc), request)
        return ok(EncounterSerializer(enc).data)


class EncounterAssignView(APIView):
    """PATCH /api/encounters/{id}/assign/ — explicit doctor assignment."""
    permission_classes = [IsNurseOrAdmin]

    def patch(self, request, pk):
        doctor_id = request.data.get("doctor_id")
        if not doctor_id:
            return err("doctor_id is required.", 400)
        try:
            enc = Encounter.objects.get(pk=pk, is_deleted=False)
            doctor = User.objects.get(pk=doctor_id, role="doctor", is_active=True)
        except (Encounter.DoesNotExist, User.DoesNotExist):
            return err("Encounter or Doctor not found.", 404)

        pre = model_snapshot(enc)
        with transaction.atomic():
            enc_locked = Encounter.objects.select_for_update().get(pk=pk)
            enc_locked.assigned_doctor = doctor
            enc_locked.status = "assigned"
            enc_locked.version += 1
            enc_locked.save()

        log_audit("encounter.assign", "encounter", enc.id, request.acuvera_user, pre, model_snapshot(enc_locked), request)
        return ok(EncounterSerializer(enc_locked).data)


class EncounterLocationUpdateView(APIView):
    """PATCH /api/encounters/{id}/location/ — update floor/room/bed after assignment."""
    permission_classes = [IsNurseOrAdmin]

    def patch(self, request, pk):
        try:
            enc = Encounter.objects.get(pk=pk, is_deleted=False)
        except Encounter.DoesNotExist:
            return err("Encounter not found.", 404)

        pre = model_snapshot(enc)
        floor = request.data.get("floor", enc.floor)
        room_number = request.data.get("room_number", enc.room_number)
        bed_number = request.data.get("bed_number", enc.bed_number)

        enc.floor = floor
        enc.room_number = room_number
        enc.bed_number = bed_number
        enc.save(update_fields=["floor", "room_number", "bed_number"])

        log_audit("encounter.location_update", "encounter", enc.id, request.acuvera_user, pre, model_snapshot(enc), request)
        return ok(EncounterSerializer(enc).data)


class DepartmentListView(APIView):
    """GET /api/departments/ — list all active departments. POST /api/departments/ — create new (Admin)."""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        depts = Department.objects.filter(is_active=True).order_by("name")
        return ok(DepartmentSerializer(depts, many=True).data)

    def post(self, request):
        if request.acuvera_user.role != "admin":
            return err("Forbidden.", 403)
        serializer = DepartmentSerializer(data=request.data)
        if not serializer.is_valid():
            return err(serializer.errors, 400)
        dept = serializer.save()
        log_audit("department.create", "department", dept.id, request.acuvera_user, None, model_snapshot(dept), request)
        return ok(serializer.data, status=201)


class DepartmentDetailView(APIView):
    """GET/PATCH/DELETE /api/departments/{id}/"""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            dept = Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return err("Department not found.", 404)
        return ok(DepartmentSerializer(dept).data)

    def patch(self, request, pk):
        try:
            dept = Department.objects.get(pk=pk)
        except Department.DoesNotExist:
            return err("Department not found.", 404)

        pre = model_snapshot(dept)
        serializer = DepartmentSerializer(dept, data=request.data, partial=True)
        if not serializer.is_valid():
            return err(serializer.errors, 400)
        
        dept = serializer.save()
        log_audit("department.update", "department", dept.id, request.acuvera_user, pre, model_snapshot(dept), request)
        return ok(serializer.data)

    def delete(self, request, pk):
        """Soft delete: toggle is_active"""
        try:
            dept = Department.objects.get(pk=pk)
            dept.is_active = not dept.is_active
            dept.save()
            return ok({"detail": "Status toggled", "is_active": dept.is_active})
        except Department.DoesNotExist:
            return err("Department not found.", 404)


class DoctorListView(APIView):
    """GET /api/doctors/?department=<id> — list doctors for assignment UI."""
    permission_classes = [IsAuthenticatedViaJWT]

    def get(self, request):
        qs = User.objects.filter(role="doctor", is_active=True)
        dept_id = request.query_params.get("department")
        if dept_id:
            qs = qs.filter(department_id=dept_id)
        return ok(UserSerializer(qs, many=True).data)


class UserAvailabilityView(APIView):
    """PATCH /api/users/{id}/availability/ — doctor updates own availability."""
    permission_classes = [IsAuthenticatedViaJWT]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return err("User not found.", 404)

        # Only self or admin can update availability
        if request.acuvera_user.pk != user.pk and request.acuvera_user.role not in ("admin", "dept_head"):
            return err("Forbidden.", 403)

        new_state = request.data.get("availability_state")
        valid_states = ("available", "in_procedure", "off_shift", "emergency", "unavailable")
        if not new_state or new_state not in valid_states:
            return err(f"availability_state must be one of: {valid_states}", 400)

        user.availability_state = new_state
        user.availability_state = new_state
        user.save(update_fields=["availability_state", "updated_at"])
        return ok(UserSerializer(user).data)


class StaffListView(APIView):
    """GET /api/admin/staff/"""
    permission_classes = [IsAdmin]

    def get(self, request):
        qs = User.objects.all().order_by("-created_at")
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        return ok(UserSerializer(qs, many=True).data)


class StaffDetailView(APIView):
    """PATCH / DELETE /api/admin/staff/{id}/"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return err("User not found.", 404)
        
        data = request.data
        if "is_active" in data:
            user.is_active = data["is_active"]
        if "role" in data:
            user.role = data["role"]
        if "full_name" in data:
            user.full_name = data["full_name"]
        if "email" in data:
            user.email = data["email"]
        if "username" in data:
            user.username = data["username"]
        if "password" in data and data["password"]:
            user.set_password(data["password"])
        if "department_id" in data:
            dept_id = data["department_id"]
            if dept_id:
                try: 
                    dept = Department.objects.get(pk=dept_id)
                    user.department = dept
                except Department.DoesNotExist:
                    pass
            else:
                user.department = None
        user.save()
        return ok(UserSerializer(user).data)
        
    def delete(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            user.is_active = False
            user.save()
            return ok({"detail": "Deleted"})
        except User.DoesNotExist:
            return err("User not found.", 404)
