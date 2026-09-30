"""
Acuvera DRF permission classes — server-side role enforcement.
Every view must declare which roles are permitted.
"""
from rest_framework.permissions import BasePermission


def _user(request):
    return getattr(request, "acuvera_user", None)


class IsAuthenticatedViaJWT(BasePermission):
    """Default permission: any authenticated Acuvera user."""
    def has_permission(self, request, view):
        return _user(request) is not None


class IsNurse(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role == "nurse"


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role == "doctor"


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role in ("admin",)


class IsDeptHead(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role in ("dept_head", "admin")


class IsNurseOrAdmin(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role in ("nurse", "admin", "dept_head")


class IsNurseOrDoctor(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role in ("nurse", "doctor")


class IsAnyAuthenticatedRole(BasePermission):
    def has_permission(self, request, view):
        u = _user(request)
        return u is not None and u.role in ("nurse", "doctor", "admin", "dept_head")
