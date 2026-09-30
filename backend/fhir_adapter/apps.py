from django.apps import AppConfig

class FhirAdapterConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fhir_adapter"
    verbose_name = "Acuvera FHIR Adapter"
