# app/schemas/intents.py

from pydantic import BaseModel, Field
from typing import Literal


class IntentResult(BaseModel):
    """
    Output of Intent Classification node.

    Confidence interpretation varies by input channel:
    - web_form: Always 1.0 (user explicitly selected intent)
    - voice: ASR confidence (Deepgram provides per-word confidence)
    - chat: LLM self-reported confidence (less reliable)
    """
    intent: Literal["RequestRefill", "CancelRequest", "StatusInquiry", "Clarification"]

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (source-dependent)"
    )

    confidence_source: Literal["web_form", "asr_transcript", "llm_classification"] = Field(
        ...,
        description="Where confidence score originated"
    )

    asr_metadata: dict | None = Field(
        None,
        description="ASR-specific data (word-level confidence, alternatives)"
    )

    reasoning: str | None = None