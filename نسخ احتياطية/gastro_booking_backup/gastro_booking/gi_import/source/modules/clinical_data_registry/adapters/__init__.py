"""CDR read adapters — each adapter reads from one owning module only."""

from app.modules.clinical_data_registry.adapters import history, labs, medications, patient

__all__ = ["history", "labs", "medications", "patient"]
