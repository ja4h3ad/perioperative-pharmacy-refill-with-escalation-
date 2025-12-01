# app/agents/central_intelligence.py
"""the orchestration layer for the agentic solution; a top-level ReAct agent"""

import os
import json
from anthropic import Anthropic
from app.schemas.intents import IntentResult
from app.schemas.entities import ExtractedEntities

class CentralIntelligence:
    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def classify_intent(
        self,
        user_message: str,
        channel: str,
        asr_confidence: float | None = None
    ) -> IntentResult:
        """
        Channel-aware intent classification.
        """
        # Channel 1:  WebForm.  Intent is explicit and driven by UI event listeners
        if channel == "web":
            # Parse intent from structured input
            # (Assumes user_message is JSON for web channel)
            form_data = json.loads(user_message)
            return IntentResult(
                intent=form_data["intent"],
                confidence=1.0,  # ← Deterministic
                confidence_source="web_form",
                reasoning="User explicitly selected intent via form"
            )

        elif channel == "voice":
            # classify from transcription
            llm_result = await self._llm_classify(user_message) # llm classifies the ASR result

            # use ASR for primary signal
            return IntentResult(
                intent=llm_result['intent'],
                confidence=asr_confidence or 0.5, # returned from transcription engine
                confidence_source="asr_transcript",
                asr_metadata={
                    "transcript":  user_message,
                    "asr_confidence": asr_confidence
                },
                reasoning=f'ASR confidence:  {asr_confidence:.2f}'

            )

        # in-app chat / unstructured messages
        else:
            llm_result = await self._llm_classify(user_message)
            return IntentResult(
                intent=llm_result['intent'],
                confidence=llm_result['confidence'],
                confidence_source="llm_classification",
                reasoning=llm_result.get('reasoning')
            )
    async def _llm_classify(self, user_message: str) -> dict:
        """Standard LLM intent classification"""
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": INTENT_CLASSIFICATION_PROMPT.format(
                    user_message=user_message
                )
            }]
        )

        return json.loads(response.content[0].text)

