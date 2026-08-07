"""Clinical Data Registry — read-only SSOT facade (Sprint 6A-CDR)."""

from app.modules.clinical_data_registry.service import ClinicalDataRegistry, get_clinical_data_registry

__all__ = ["ClinicalDataRegistry", "get_clinical_data_registry"]
