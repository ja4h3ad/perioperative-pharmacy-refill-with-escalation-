# app/schemas/state.py
"""LangGraph state machine"""

from typing import TypedDict, Annotated, Sequence
import operator
from app.agents.orchestrator import CentralIntelligence
from app.schemas.intents import IntentResult
from app.schemas.entities import ExtractedEntities
from app.state_machine import RefillState

orchestrator = CentralIntelligence()

async def classify_intent_node(state: RefillState) -> RefillState:
    """Intent classification."""
    # send workload to orchestrator
    intent_result = await orchestrator.classify_intent(
        user_message=state['conversation_history'][-1],
        channels=state.get('channel'),
    )

    state['intent_result'] = intent_result
    state['current_step'] = 'intent_classified'
    return state