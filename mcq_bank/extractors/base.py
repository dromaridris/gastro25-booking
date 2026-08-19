"""
Common interface every extractor plugin must implement. Adding a new
content type (flashcards, clinical pearls, summaries, tables...) means
creating a new package under app/extractors/<type>/ that implements this
interface and registering it in registry.py - nothing else in the codebase
needs to change.
"""
from abc import ABC, abstractmethod


class ExtractedItem:
    """
    Normalized output of any extractor, regardless of content type.
    `payload` is type-specific (see each extractor's schema.py) but every
    extractor must produce one of these so the generic content_service can
    store it uniformly in content_items.payload_json.
    """
    def __init__(self, item_number, payload, source_location=None,
                 raw_extracted_text=None, confidence_flag="high",
                 review_flags=None, review_evidence=None):
        self.item_number = item_number
        self.payload = payload
        self.source_location = source_location or {}
        self.raw_extracted_text = raw_extracted_text or ""
        self.confidence_flag = confidence_flag
        self.review_flags = review_flags or []
        self.review_evidence = review_evidence


class BaseExtractor(ABC):
    content_type = None  # override in subclass, e.g. "mcq"

    @abstractmethod
    def detect_pattern(self, chapter_text: str) -> str:
        """Return a short pattern identifier (e.g. 'type_a', 'type_b',
        'unknown') describing how this chapter's source material is laid
        out. Used for confidence reporting in the admin review UI."""
        raise NotImplementedError

    @abstractmethod
    def extract(self, chapter_text: str) -> list:
        """Return a list of ExtractedItem instances."""
        raise NotImplementedError
