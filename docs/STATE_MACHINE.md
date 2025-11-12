# Refill Workflow State Machine

## Overview
This document defines the state transitions for the medication refill agent workflow. Each state represents a discrete step in the processing pipeline, with explicit happy/failure paths.

## State Definitions

| State | Description | Transitions | Path |
|-------|-------------|-------------|------|
| **1. Collect_Refill_Request** | Initial state: Agent asks for the medication and confirms the patient/PA identity. | `to_Rx_Safety_Check` | Happy/Failure |
| **2. Rx_Safety_Check** | **AI Agent 1 (Pharmacy Agent)** performs preliminary checks (Drug-Drug interaction, allergies from EHR data). | `to_Refill_Available` (Pass) or `to_Escalation_Required` (Fail) | Happy/Failure |
| **3. Backend_Check** | Simulated API call to EHR/Dispensation system (Pixsys/Omnicell) to check inventory and Rx validity. | `to_Refill_Dispensed` (Available) or `to_PA_Approval_Needed` (Requires Prior Auth) | Happy/Failure |
| **4. PA_Approval_Needed** | **AI Agent 2 (Central Intelligence/ReAct)** determines the escalation contact (supervising physician/PA). | `to_Escalate_Handoff` | Failure |
| **5. Escalate_Handoff** | Agent sends the necessary context and drafts a notification for the human **Circuit Breaker**. | `to_Escalation_Complete` | Failure |
| **6. Refill_Dispensed** | Agent confirms dispensing and provides next steps to the user/PA. | `END` | Happy |
| **7. Escalation_Complete** | Agent informs the user/PA of the successful handoff and expected follow-up. | `END` | Failure |

## State Transition Diagram

See the [state machine diagram](./diagrams/state_machine.png) for a visual representation.

## Agent Responsibilities by State

### State: Pharmacy Agent (AI Agent 1)
- Intent classification
- Entity extraction
- Safety validation (allergy, DDI, dosage)
- Controlled substance policy enforcement

### State: EHR Agent
- Patient identity verification
- Clinical data retrieval (medications, allergies, labs)
- Backend inventory check

### State: Central Intelligence (AI Agent 2 - ReAct)
- Escalation routing logic
- Context package assembly
- Physician notification orchestration

### State: Dispensation Connector
- Order submission to Pixsys/Omnicell
- Status polling
- User notification

## Circuit Breaker Triggers

The following conditions trigger a circuit breaker (State escalation):

1. **Low confidence** in intent/entity extraction (<70%)
2. **Identity verification failure** (DOB mismatch)
3. **Major drug interaction** detected
4. **Direct allergy match** found
5. **Controlled substance** (Schedule II-III) requiring co-signature
6. **EHR/Backend unavailable** (timeout/error)
7. **Max retry attempts** exceeded (3 turns)

## Implementation Notes

- **State persistence**: Stored in Redis with 5-minute TTL
- **Transition logging**: All state changes recorded in immutable audit log
- **Idempotency**: State transitions are idempotent (can retry safely)
- **LangGraph mapping**: Each state maps to a LangGraph node in `app/state_machine.py`

## Related Documents

- [Conversation Design](./CONVERSATION_DESIGN.md) - Intents and entities
- [Functional Requirements](./Assumptions_and_Requirements.pdf) - Detailed business rules
- [Architecture](./ARCHITECTURE.md) - System design