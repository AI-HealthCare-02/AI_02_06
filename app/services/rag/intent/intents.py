"""Intent type definitions for the RAG pipeline.

This module defines the IntentType enum used for classifying
user queries in the healthcare AI assistant.
"""

from enum import StrEnum


class IntentType(StrEnum):
    """User intent categories for the healthcare AI assistant.

    Categories are designed to be extensible as new features are added.
    """

    MEDICATION_INFO = "medication_info"
    DRUG_INTERACTION = "drug_interaction"
    MY_SCHEDULE = "my_schedule"
    SUPPLEMENT_INFO = "supplement_info"
    NEARBY_HOSPITAL = "nearby_hospital"
    WEATHER = "weather"
    GENERAL_CHAT = "general_chat"
    OUT_OF_SCOPE = "out_of_scope"
