"""Intent classifier for the RAG pipeline.

Implements keyword and rule-based intent classification.
Designed to be replaced with a model-based classifier (e.g., KoELECTRA)
without changing the interface.
"""

import logging

from app.services.rag.intent.intents import IntentType
from app.services.rag.intent.keywords import FALLBACK_INTENT, INTENT_KEYWORDS

logger = logging.getLogger(__name__)

# Evaluation order: more specific intents before general ones.
_CLASSIFICATION_ORDER: list[IntentType] = [
    IntentType.DRUG_INTERACTION,
    IntentType.MY_SCHEDULE,
    IntentType.SUPPLEMENT_INFO,
    IntentType.NEARBY_HOSPITAL,
    IntentType.WEATHER,
    IntentType.MEDICATION_INFO,
    IntentType.GENERAL_CHAT,
]


class IntentClassifier:
    """Keyword and rule-based intent classifier.

    Classifies user queries into predefined intent categories.
    Phase 1 implementation uses keyword matching.
    Phase 2 will replace this with KoELECTRA fine-tuned model.
    """

    def classify(self, query: str) -> IntentType:
        """Classify user query into an intent category.

        Args:
            query: User input text to classify.

        Returns:
            IntentType: Classified intent category.
        """
        if not query or not query.strip():
            return IntentType.GENERAL_CHAT

        query_lower = query.lower()

        for intent in _CLASSIFICATION_ORDER:
            keywords = INTENT_KEYWORDS.get(intent, frozenset())
            if any(keyword in query_lower for keyword in keywords):
                logger.debug("Classified '%s' as %s", query[:50], intent)
                return intent

        logger.debug("No keyword match for '%s', falling back to %s", query[:50], FALLBACK_INTENT)
        return FALLBACK_INTENT
