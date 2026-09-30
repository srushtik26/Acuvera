"""
Audit logging service — immutable append-only trail.
Call log_audit() before and after every mutation.
"""
import logging
from typing import Any, Optional

logger = logging.getLogger("acuvera.audit")


def log_audit(
    action: str,
    entity_type: str,
    entity_id: Any,
    user=None,
    pre: Optional[dict] = None,
    post: Optional[dict] = None,
    request=None,
    metadata: Optional[dict] = None,
):
    """
    Create an immutable AuditLog entry.

    Parameters
    ----------
    action      : verb e.g. 'triage.analyze', 'allocation.assign', 'escalation.trigger'
    entity_type : 'encounter', 'patient', 'user', etc.
    entity_id   : UUID or str of the primary key
    user        : Acuvera User model instance (or None for system)
    pre         : snapshot of model state before change
    post        : snapshot of model state after change
    request     : Django request object (for IP, user_agent)
    metadata    : any extra JSON-serialisable context
    """
    from core.models import AuditLog
    import uuid

    ip = None
    ua = ""
    if request:
        ip = getattr(request, "acuvera_ip", None)
        ua = getattr(request, "acuvera_user_agent", "")

    try:
        entity_uuid = uuid.UUID(str(entity_id)) if entity_id else None
    except (ValueError, AttributeError):
        entity_uuid = None

    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            entity_type=entity_type,
            entity_id=entity_uuid,
            pre_change_snapshot=pre,
            post_change_snapshot=post,
            ip_address=ip,
            user_agent=ua,
            metadata_json=metadata,
        )
    except Exception as e:
        # Audit log must never block the main flow
        logger.error("Failed to write audit log: %s", e, exc_info=True)


def model_snapshot(instance) -> dict:
    """
    Produce a JSON-serialisable dict snapshot of a model instance.
    Strips non-serialisable types.
    """
    from django.forms.models import model_to_dict
    import uuid
    from datetime import datetime, date
    from decimal import Decimal

    data = {}
    try:
        data = model_to_dict(instance)
    except Exception:
        return {}

    def _clean(v):
        if isinstance(v, (uuid.UUID,)):
            return str(v)
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, Decimal):
            return float(v)
        return v

    return {k: _clean(v) for k, v in data.items()}
