"""
Acuvera middleware stack:
1. RequestAuditMiddleware — captures IP + user_agent for audit log
2. JWTAuthMiddleware — validates Clerk JWT (or BYPASS_AUTH in dev)
3. FeatureFlagMiddleware — injects per-hospital feature flags
"""
import json
import logging
import jwt

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("acuvera.middleware")

# Paths exempt from auth
AUTH_EXEMPT_PATHS = {
    "/healthz",
    "/system-status",
    "/api/auth/login/",
    "/api/auth/force-admin/",
}


class RequestAuditMiddleware(MiddlewareMixin):
    """Capture request metadata for audit log and structured logs."""

    def process_request(self, request):
        request.acuvera_ip = self._get_ip(request)
        request.acuvera_user_agent = request.META.get("HTTP_USER_AGENT", "")
        request.acuvera_user = None  # Populated by JWTAuthMiddleware

    def _get_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")


class JWTAuthMiddleware(MiddlewareMixin):
    """
    Validate Acuvera local JWT on every request and attach the Acuvera User to
    request.acuvera_user.
    """

    def process_request(self, request):
        if request.method == "OPTIONS":
            return None

        if request.path in AUTH_EXEMPT_PATHS:
            return None

        # FHIR endpoints use Basic auth — handled by fhir_adapter
        if request.path.startswith("/fhir/"):
            return None

        # Normal JWT validation
        token = self._extract_token(request)
        
        # Dev bypass — allow bypassing via header if enabled in settings
        if settings.BYPASS_AUTH:
            bypass_id = request.META.get("HTTP_X_BYPASS_USER_ID")
            if bypass_id:
                from core.models import User
                try:
                    request.acuvera_user = User.objects.get(pk=bypass_id, is_active=True)
                    return None
                except User.DoesNotExist:
                    pass

        if not token:
            return JsonResponse(
                {"meta": {}, "data": None, "errors": ["Authentication required"]},
                status=401,
            )

        try:
            # First try our local JWT — this enables our ID/Password local auth
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            if payload.get("iss") == "acuvera-local":
                from core.models import User
                user_id = payload.get("sub")
                try:
                    request.acuvera_user = User.objects.get(pk=user_id, is_active=True)
                    return None
                except User.DoesNotExist:
                    return JsonResponse({"meta": {}, "data": None, "errors": ["Local user not found"]}, status=403)
            else:
                return JsonResponse({"meta": {}, "data": None, "errors": ["Invalid token issuer"]}, status=401)
        except Exception as e:
            logger.warning("JWT validation failed: %s", str(e))
            return JsonResponse(
                {"meta": {}, "data": None, "errors": ["Invalid or expired token"]},
                status=401,
            )

        return None

    def _extract_token(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        logger.warning(f"Extracting token for {request.path}: HTTP_AUTHORIZATION present? {bool(header)}")
        if header.startswith("Bearer "):
            return header[7:]
        return None




class FeatureFlagMiddleware(MiddlewareMixin):
    """
    Inject per-hospital feature flags into request.feature_flags.
    Falls back to FEATURE_FLAGS_DEFAULT from settings.
    """

    def process_request(self, request):
        flags = dict(settings.FEATURE_FLAGS_DEFAULT)
        # TODO: if we have a hospital_id concept, load hospital-specific HospitalConfig here
        # For now, use global defaults merged with any DB config (single-hospital MVP)
        try:
            from core.models import HospitalConfig
            config = HospitalConfig.objects.first()
            if config and config.feature_flags:
                flags.update(config.feature_flags)
        except Exception:
            pass  # DB may not be ready during startup checks
        request.feature_flags = flags
