# Conversation Design

## Overview
This document defines the conversational interface for the medication refill agent, including intents, entities, and ambiguity handling strategies.

## Intent Classification

### Primary Intents

| Intent Name | Example Utterance | Handling |
|-------------|-------------------|----------|
| `RequestRefill` | "I need a refill on my prescription." | Primary intent to start the flow. Proceeds to entity extraction. |
| `CancelRequest` | "Hold on, I don't need it anymore." | Global intent to immediately exit the flow (Circuit Breaker). Terminates conversation gracefully. |
| `StatusInquiry` | "What's the status of order ORD-456?" | *(Future enhancement)* Query existing order status. |
| `Clarification` | "30 tablets" (in response to prompt) | User providing missing information during multi-turn dialog. |

### Intent Confidence Thresholds

| Confidence Range | Action |
|------------------|--------|
| **>85%** | Proceed with high confidence |
| **70-85%** | Ask clarifying question ("Did you mean...?") |
| **<70%** | Circuit breaker → Human handoff |

---

## Entity/Slot Extraction

### Required Entities

| Entity Name | Example Value | Validation Rules | Ambiguity Handling |
|-------------|---------------|------------------|-------------------|
| **PatientID / MRN** | `12345678` | Must exist in EHR, 6-8 digits | **Crucial**: Must be confirmed via simulated backend API (e.g., "Can you confirm your date of birth is MM/DD/YYYY?"). |
| **DrugName** | `Morphine Sulfate` | Must exist in formulary | **Ambiguity**: Use RAG/Vector Search over a list of common perioperative drugs to suggest alternatives if spelling is ambiguous (e.g., "Did you mean 'Morphine' or 'Motrin'?"). |
| **Quantity / Dose** | `30 days` / `10mg` | Must fall within formulary guidelines | **Missing Info**: Agent must prompt for this if not provided, ensuring it falls within policy guidelines (RAG check). |

### Optional Entities

| Entity Name | Example Value | Default Behavior |
|-------------|---------------|------------------|
| **Frequency** | `once daily` | Infer from previous Rx if missing |
| **Route** | `PO` (oral) | Default to most common route for drug |

---

## Handling Ambiguity

### 1. Drug Name Disambiguation (RAG/Vector Search)

**Scenario**: User says "lysinopril" (typo)

**Strategy**:
1. Embed user input: `embed("lysinopril")`
2. Vector search formulary index → Top 3 matches:
   - Lisinopril 10mg (similarity: 0.92)
   - Lisinopril 20mg (similarity: 0.91)
   - Enalapril 10mg (similarity: 0.65)
3. **If top match >0.95**: Confirm single option
4. **If top match 0.75-0.95**: Present top 3 for user selection
5. **If top match <0.75**: Escalate to pharmacist

**Example Dialog**:
```
PA: "Refill lysinopril for patient 123"
Agent: "I found a few matches. Did you mean:
        1. Lisinopril 10mg
        2. Lisinopril 20mg
        3. Enalapril 10mg
        Please respond with the number."
PA: "1"
Agent: "Got it. Lisinopril 10mg. How many tablets?"
```

---

### 2. Missing Required Fields

**Scenario**: User omits quantity

**Strategy**: Progressive prompting with context
```
PA: "Refill metformin for patient 456"
Agent: "How many days supply? (e.g., 30 days, 90 days)"
PA: "30 days"
Agent: [Calculates quantity based on dosing schedule]
```

**Max Retries**: 3 attempts before circuit breaker

---

### 3. Patient Identity Verification

**Scenario**: Ambiguous patient reference

**Strategy**: Always confirm with DOB or last 4 of SSN
```
PA: "Refill for patient 123"
Agent: [Queries EHR] "I found John Doe, DOB 03/15/1965. Can you confirm?"
PA: "Confirmed"
Agent: [Proceeds to safety checks]
```

**Failure Mode**: If DOB doesn't match → Circuit breaker (potential HIPAA violation)

---

## Multi-Turn Conversation Flow

### Example 1: Happy Path (Complete Information)
```
Turn 1
PA: "Refill lisinopril 10mg, 30 tabs for patient 123."
Agent: [Intent: RequestRefill (confidence: 0.95)]
       [Entities: MRN=123, Drug=Lisinopril 10mg, Qty=30]
       "Confirming patient John Doe, DOB 03/15/1965?"

Turn 2
PA: "Yes"
Agent: [Safety checks: Allergy ✓, DDI ✓, Dosage ✓, Non-controlled ✓]
       "Patient has no allergies to lisinopril. No drug interactions found. 
        Refill created and sent to Pixsys. Order ID: ORD-456."
```

---

### Example 2: Escalation Path (Controlled Substance)
```
Turn 1
PA: "Refill oxycodone 30mg, 30 tabs for patient 123."
Agent: [Intent: RequestRefill (confidence: 0.97)]
       [Entities: MRN=123, Drug=Oxycodone 30mg, Qty=30]
       "Confirming patient John Doe, DOB 03/15/1965?"

Turn 2
PA: "Confirmed"
Agent: [Safety checks: Controlled substance = Schedule II]
       "Request requires physician co-sign due to controlled substance policy. 
        I've sent a co-sign request to Dr. Smith with context: 
        [patient summary, meds, labs, conversation]. 
        Awaiting sign-off. (Escalation ID: ESC-99)"
```

---

### Example 3: Ambiguity Resolution (Drug Name)
```
Turn 1
PA: "Refill lysnopril for patient 123"
Agent: [Intent: RequestRefill (confidence: 0.89)]
       [Entity: DrugName → Vector search finds multiple matches]
       "I found a few similar medications:
        1. Lisinopril 10mg
        2. Lisinopril 20mg
        3. Enalapril 5mg
        Which did you mean?"

Turn 2
PA: "1"
Agent: [Entity confirmed: Lisinopril 10mg]
       "Great. How many tablets?"

Turn 3
PA: "30"
Agent: [Proceeds to safety checks...]
```

---

### Example 4: Circuit Breaker (Low Confidence)
```
Turn 1
PA: "Need thing for guy"
Agent: [Intent: Unknown (confidence: 0.42)]
       "I'm having trouble understanding. Could you rephrase? 
        For example: 'Refill [medication name] for patient [MRN]'"

Turn 2
PA: "Patient needs stuff"
Agent: [Intent: Still unclear (confidence: 0.38)]
       "I want to make sure I get this right. Let me connect you 
        with a pharmacist who can help. (Handoff ID: HO-789)"
```

---

## Prompt Templates

### Intent Classification Prompt
```
You are a clinical assistant helping Physician Assistants (PAs) process medication refills.

Classify the user's intent from the following options:
- RequestRefill: User wants to refill a prescription
- CancelRequest: User wants to cancel a pending request
- StatusInquiry: User wants to check order status
- Clarification: User is providing additional information

User message: "{user_message}"

Respond in JSON format:
{
  "intent": "RequestRefill",
  "confidence": 0.95
}
```

### Entity Extraction Prompt
```
Extract the following entities from the user's refill request:
- patient_id (MRN): 6-8 digit number
- drug_name: Medication name (generic or brand)
- dose: Amount with unit (e.g., "10mg", "500mg")
- quantity: Number of tablets/capsules or days supply

User message: "{user_message}"

Respond in JSON format:
{
  "entities": {
    "patient_id": "12345678",
    "drug_name": "Lisinopril",
    "dose": "10mg",
    "quantity": 30
  },
  "missing_entities": []
}
```

---

## RAG Integration Points

### 1. Drug Name Matching
- **Index**: `formulary-index` (500 common perioperative drugs)
- **Retrieval**: Hybrid (BM25 + dense embeddings)
- **Threshold**: Similarity >0.75 for inclusion

### 2. Drug Interaction Lookup
- **Index**: `drug-interaction-index` (10K drug pairs)
- **Query**: `[Patient's active meds] + [Requested med]`
- **Output**: Severity (major/moderate/minor), mechanism, recommendation

### 3. Policy Enforcement
- **Index**: `policy-index` (controlled substance rules, formulary guidelines)
- **Query**: Drug name + schedule + patient risk factors
- **Output**: Escalation required (yes/no), rationale, policy version

---

## Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Intent Accuracy** | >95% | Compare predicted vs. human-labeled |
| **Entity Extraction F1** | >90% | Precision/recall on required fields |
| **Clarification Turns** | <2 per conversation | Average turns to slot completion |
| **Drug Match Accuracy** | >98% | Correct drug after disambiguation |
| **Circuit Breaker Rate** | <2% | Percentage of conversations escalated |

---

## Related Documents

- [State Machine](./STATE_MACHINE.md) - Workflow states
- [Functional Requirements](./FUNCTIONAL_REQUIREMENTS.md) - Business rules
- [Architecture](./ARCHITECTURE.md) - System design