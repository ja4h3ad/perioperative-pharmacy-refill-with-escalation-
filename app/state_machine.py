# app/state_machine.py
# app/state_machine.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
import operator
import asyncio


class RefillState(TypedDict):
    """State schema for refill workflow"""
    conversation_id: str
    conversation_history: Annotated[Sequence[str], operator.add]
    intents: list[str]
    entities: dict
    confidence_scores: dict
    safety_checks: dict
    escalation_required: bool
    escalation_context: dict
    current_step: str
    error_state: dict | None


# Async node functions
async def collect_refill_request(state: RefillState) -> RefillState:
    """Entry point: parse initial user message"""
    from app.agents.orchestrator import CentralOrchestrator

    orchestrator = CentralOrchestrator()
    result = await orchestrator.parse_request(state['conversation_history'][-1])

    state['current_step'] = 'collect_request'
    return state


async def classify_intent_node(state: RefillState) -> RefillState:
    """Classify user intent using LLM"""
    from app.agents.orchestrator import CentralOrchestrator

    orchestrator = CentralOrchestrator()
    intent_result = await orchestrator.classify_intent(
        state['conversation_history'][-1]
    )

    state['intents'].append(intent_result['intent'])
    state['confidence_scores']['intent'] = intent_result['confidence']
    state['current_step'] = 'intent_classified'

    return state


async def extract_entities_node(state: RefillState) -> RefillState:
    """Extract entities from user message"""
    from app.agents.orchestrator import CentralOrchestrator

    orchestrator = CentralOrchestrator()
    entities = await orchestrator.extract_entities(
        state['conversation_history'][-1],
        state['intents'][-1]
    )

    state['entities'].update(entities)
    state['current_step'] = 'entities_extracted'

    return state


async def perform_safety_checks(state: RefillState) -> RefillState:
    """Run pharmacy agent safety validation"""
    from app.agents.pharmacy_agent import PharmacyAgent
    from app.agents.ehr_agent import EHRAgent

    # Parallel EHR data fetch and drug lookup
    ehr_agent = EHRAgent()
    pharmacy_agent = PharmacyAgent()

    # Run in parallel using asyncio.gather
    patient_data, drug_info = await asyncio.gather(
        ehr_agent.fetch_patient_data(state['entities']['patient_id']),
        pharmacy_agent.lookup_drug(state['entities']['drug_name'])
    )

    # Sequential safety checks (depend on patient_data)
    safety_result = await pharmacy_agent.validate_safety(
        patient_data=patient_data,
        drug_info=drug_info,
        requested_dose=state['entities']['dose'],
        requested_quantity=state['entities']['quantity']
    )

    state['safety_checks'] = safety_result
    state['escalation_required'] = safety_result.get('escalation_required', False)
    state['current_step'] = 'safety_checked'

    return state


async def escalate_to_human(state: RefillState) -> RefillState:
    """Build context package and notify physician"""
    from app.agents.escalation_agent import EscalationAgent

    escalation_agent = EscalationAgent()

    # Build context package and send notification in parallel
    context_task = escalation_agent.build_context_package(state)
    notification_task = escalation_agent.notify_physician(state)

    context, notification_result = await asyncio.gather(
        context_task,
        notification_task
    )

    state['escalation_context'] = context
    state['current_step'] = 'escalated'

    return state


async def confirm_dispensing(state: RefillState) -> RefillState:
    """Submit order to dispensation system"""
    from app.agents.dispense_connector import DispenseConnector

    connector = DispenseConnector()
    order_result = await connector.submit_order(state['entities'])

    state['current_step'] = 'dispensed'
    return state


# Conditional routing functions
def route_by_intent(state: RefillState) -> str:
    """Route based on intent classification"""
    intent = state['intents'][-1]
    confidence = state['confidence_scores']['intent']

    if confidence < 0.70:
        return "circuit_breaker"
    elif intent == "RequestRefill":
        return "extract_entities"
    elif intent == "CancelRequest":
        return END
    else:
        return "clarify"


def check_slot_completeness(state: RefillState) -> str:
    """Check if all required entities are present"""
    required_slots = ['patient_id', 'drug_name', 'dose', 'quantity']
    missing = [s for s in required_slots if s not in state['entities']]

    if missing:
        return "clarify"
    else:
        return "safety_check"


def check_safety_result(state: RefillState) -> str:
    """Route based on safety check outcome"""
    if state['safety_checks'].get('blocked'):
        return "safe_exit"
    elif state['escalation_required']:
        return "escalate"
    else:
        return "dispense"


# Build the async graph
def create_refill_graph():
    """Create LangGraph state machine with async nodes"""
    workflow = StateGraph(RefillState)

    # Add async nodes
    workflow.add_node("collect_request", collect_refill_request)
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("extract_entities", extract_entities_node)
    workflow.add_node("safety_check", perform_safety_checks)
    workflow.add_node("escalate", escalate_to_human)
    workflow.add_node("dispense", confirm_dispensing)

    # Set entry point
    workflow.set_entry_point("collect_request")

    # Add edges
    workflow.add_edge("collect_request", "classify_intent")

    workflow.add_conditional_edges(
        "classify_intent",
        route_by_intent,
        {
            "extract_entities": "extract_entities",
            "circuit_breaker": END,
            "clarify": "collect_request"
        }
    )

    workflow.add_conditional_edges(
        "extract_entities",
        check_slot_completeness,
        {
            "clarify": "collect_request",
            "safety_check": "safety_check"
        }
    )

    workflow.add_conditional_edges(
        "safety_check",
        check_safety_result,
        {
            "escalate": "escalate",
            "dispense": "dispense",
            "safe_exit": END
        }
    )

    workflow.add_edge("escalate", END)
    workflow.add_edge("dispense", END)

    return workflow.compile()


# Main execution
async def process_refill_request(conversation_id: str, user_message: str) -> dict:
    """Process a refill request through the state machine"""
    graph = create_refill_graph()

    initial_state: RefillState = {
        "conversation_id": conversation_id,
        "conversation_history": [user_message],
        "intents": [],
        "entities": {},
        "confidence_scores": {},
        "safety_checks": {},
        "escalation_required": False,
        "escalation_context": {},
        "current_step": "initial",
        "error_state": None
    }

    # Run async graph
    result = await graph.ainvoke(initial_state)

    return result