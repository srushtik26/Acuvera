"""
Standardised API response envelope and DRF exception handler.
All responses follow: { meta: {}, data: ..., errors: [] }
"""
import uuid
import logging
from datetime import datetime, timezone

from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("acuvera.exceptions")


def ok(data, status=200, meta_extra: dict = None):
    meta = {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()}
    if meta_extra:
        meta.update(meta_extra)
    return Response({"meta": meta, "data": data, "errors": []}, status=status)


def err(errors, status=400, meta_extra: dict = None):
    meta = {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()}
    if meta_extra:
        meta.update(meta_extra)
    if isinstance(errors, str):
        errors = [errors]
    return Response({"meta": meta, "data": None, "errors": errors}, status=status)


def acuvera_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled exception in view", exc_info=exc)
        return err("An unexpected server error occurred. Please try again.", status=500)

    # Normalise DRF error format to our envelope
    detail = response.data.get("detail", response.data) if hasattr(response.data, "get") else response.data
    if isinstance(detail, list):
        errors = [str(d) for d in detail]
    elif isinstance(detail, dict):
        errors = [f"{k}: {v}" for k, v in detail.items()]
    else:
        errors = [str(detail)]

    response.data = {
        "meta": {"request_id": str(uuid.uuid4()), "timestamp": datetime.now(timezone.utc).isoformat()},
        "data": None,
        "errors": errors,
    }
    return response
