from pydantic import BaseModel, Field
from typing import Optional, Literal

class RefillRequest(BaseModel):
    """
    API contract for Collect Request node.
    Validates all input regardless of channel.
    1. pa_id:  clinician userId acquired via login
    2. session_id:  conversationID initiated from UI evenet listener
    3. channel:  metadata helps with observability; for LangFuse tracking of comparison of voice and
    web for confidence scores for prompt tuning or ASR improvements.
    """
    user_message: str = Field(
        ...,
        description="Natural language text request or transcribed speech",
        example="Refill lisinopril 10mg for patient 123"
    )
    user_message: str
    pa_id: str
    session_id: str | None = None
    channel: Literal["web", "voice", "mobile", "chat"]

    # Voice-specific
    asr_confidence: float | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="ASR transcription confidence (voice channel only)"
    )

    # Web-specific
    explicit_intent: Literal["RequestRefill", "CancelRequest", "StatusInquiry"] | None = Field(
        None,
        description="User-selected intent (web form only)"
    )
