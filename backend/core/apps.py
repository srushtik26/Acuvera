"""
Core app configuration. APScheduler is NOT started from here;
that is done from the scheduler app to avoid import cycles.
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Acuvera Core"
