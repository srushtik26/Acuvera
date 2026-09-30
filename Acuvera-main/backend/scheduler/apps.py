"""
Scheduler app config — starts APScheduler when Django is ready.
Only runs in the main worker process (not the reloader watcher).
"""
import os
from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "scheduler"
    verbose_name = "Acuvera Background Scheduler"

    def ready(self):
        is_testing = os.environ.get("DJANGO_TEST", "false").lower() == "true"
        if is_testing:
            return

        # Django dev server spawns TWO processes:
        #   1. The reloader watcher  → RUN_MAIN is NOT set  → skip
        #   2. The actual app worker → RUN_MAIN = "true"    → start scheduler
        # In production (gunicorn single-worker) RUN_MAIN is absent but there
        # is only one process, so we also check for gunicorn.
        run_main = os.environ.get("RUN_MAIN")
        server_software = os.environ.get("SERVER_SOFTWARE", "")
        is_gunicorn = "gunicorn" in server_software.lower()
        is_dev_worker = run_main == "true"

        if not is_dev_worker and not is_gunicorn:
            return  # reloader watchdog — do NOT start scheduler

        try:
            from scheduler.jobs import start_scheduler
            start_scheduler()
        except Exception as e:
            import logging
            logging.getLogger("acuvera.scheduler").error("Failed to start scheduler: %s", e)
