from mcq_bank.extractors.mcq.extractor import McqExtractor

_REGISTRY = {
    "mcq": McqExtractor(),
    # Future: "flashcard": FlashcardExtractor(), "clinical_pearl": ClinicalPearlExtractor(), ...
}


def get_extractor(content_type: str):
    if content_type not in _REGISTRY:
        raise ValueError(f"No extractor registered for content_type='{content_type}'")
    return _REGISTRY[content_type]


def available_content_types():
    return list(_REGISTRY.keys())
