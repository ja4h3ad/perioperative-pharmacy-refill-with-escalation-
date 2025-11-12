# app/agents/pharmacy_agents.py

# app/agents/pharmacy_agent.py
import asyncio
from typing import Optional
from dataclasses import dataclass
from app.rag.vector_store import VectorStore
from app.safety.policy_engine import PolicyEngine


@dataclass
class SafetyResult:
    passed: bool
    blocked: bool
    escalation_required: bool
    findings: list[dict]
    recommendations: list[str]


class PharmacyAgent:
    def __init__(self):
        self.vector_store = VectorStore()
        self.policy_engine = PolicyEngine()

    async def lookup_drug(self, drug_name: str) -> dict:
        """Async RAG lookup for drug information"""
        # Simulate async vector search
        result = await self.vector_store.asimilarity_search(
            query=drug_name,
            index="formulary-index",
            top_k=1
        )

        if not result or result[0]['score'] < 0.75:
            raise ValueError(f"Drug '{drug_name}' not found in formulary")

        return result[0]['metadata']

    async def validate_safety(
            self,
            patient_data: dict,
            drug_info: dict,
            requested_dose: str,
            requested_quantity: int
    ) -> SafetyResult:
        """Run all safety checks in parallel"""

        # Run checks concurrently
        allergy_check, ddi_check, dosage_check, controlled_check = await asyncio.gather(
            self._check_allergies(patient_data, drug_info),
            self._check_drug_interactions(patient_data, drug_info),
            self._check_dosage(drug_info, requested_dose, patient_data),
            self._check_controlled_substance(drug_info),
            return_exceptions=True  # Don't fail if one check errors
        )

        # Aggregate results
        findings = []
        escalation_required = False
        blocked = False

        if isinstance(allergy_check, Exception):
            findings.append({"check": "allergy", "error": str(allergy_check)})
            blocked = True
        elif allergy_check['severity'] == 'major':
            blocked = True
            findings.append(allergy_check)
        elif allergy_check['severity'] == 'moderate':
            escalation_required = True
            findings.append(allergy_check)

        if isinstance(ddi_check, Exception):
            findings.append({"check": "ddi", "error": str(ddi_check)})
        elif ddi_check['severity'] == 'major':
            blocked = True
            findings.append(ddi_check)
        elif ddi_check['severity'] == 'moderate':
            escalation_required = True
            findings.append(ddi_check)

        if isinstance(controlled_check, Exception):
            findings.append({"check": "controlled", "error": str(controlled_check)})
        elif controlled_check['schedule'] in ['II', 'III']:
            escalation_required = True
            findings.append(controlled_check)

        return SafetyResult(
            passed=not blocked,
            blocked=blocked,
            escalation_required=escalation_required,
            findings=findings,
            recommendations=self._generate_recommendations(findings)
        )

    async def _check_allergies(self, patient_data: dict, drug_info: dict) -> dict:
        """Async allergy checking with RAG cross-reference"""
        await asyncio.sleep(0.1)  # Simulate I/O

        patient_allergies = patient_data.get('allergies', [])
        drug_ingredients = drug_info.get('active_ingredients', [])

        # Check for direct matches
        for allergy in patient_allergies:
            if allergy['substance'].lower() in [ing.lower() for ing in drug_ingredients]:
                return {
                    "check": "allergy",
                    "severity": "major",
                    "finding": f"Patient allergic to {allergy['substance']}",
                    "recommendation": "BLOCK: Do not dispense"
                }

        # Check for cross-sensitivities via RAG
        cross_sensitivity = await self._check_cross_sensitivity(patient_allergies, drug_info)
        if cross_sensitivity:
            return {
                "check": "allergy",
                "severity": "moderate",
                "finding": cross_sensitivity,
                "recommendation": "Escalate to physician for review"
            }

        return {"check": "allergy", "severity": "none", "finding": "No allergies detected"}

    async def _check_cross_sensitivity(self, allergies: list, drug_info: dict) -> Optional[str]:
        """RAG lookup for drug class cross-sensitivities"""
        if not allergies:
            return None

        # Query vector store for cross-reactivity
        allergy_names = [a['substance'] for a in allergies]
        query = f"{drug_info['drug_class']} cross-reactivity with {', '.join(allergy_names)}"

        results = await self.vector_store.asimilarity_search(
            query=query,
            index="allergy-cross-ref-index",
            top_k=1
        )

        if results and results[0]['score'] > 0.80:
            return results[0]['content']

        return None

    async def _check_drug_interactions(self, patient_data: dict, drug_info: dict) -> dict:
        """Async DDI checking"""
        await asyncio.sleep(0.15)  # Simulate I/O

        active_meds = patient_data.get('active_medications', [])
        if not active_meds:
            return {"check": "ddi", "severity": "none", "finding": "No active medications"}

        # Query interaction database
        interactions = await self._query_interaction_db(active_meds, drug_info['drug_name'])

        major_interactions = [i for i in interactions if i['severity'] == 'major']
        if major_interactions:
            return {
                "check": "ddi",
                "severity": "major",
                "finding": f"Major interaction: {major_interactions[0]['description']}",
                "recommendation": "BLOCK: Do not dispense"
            }

        moderate_interactions = [i for i in interactions if i['severity'] == 'moderate']
        if moderate_interactions:
            return {
                "check": "ddi",
                "severity": "moderate",
                "finding": f"Moderate interaction: {moderate_interactions[0]['description']}",
                "recommendation": "Escalate for physician review"
            }

        return {"check": "ddi", "severity": "none", "finding": "No significant interactions"}

    async def _query_interaction_db(self, active_meds: list[str], new_drug: str) -> list[dict]:
        """RAG query for drug-drug interactions"""
        # Batch query for efficiency
        queries = [f"{med} interaction with {new_drug}" for med in active_meds]

        # Parallel vector searches
        tasks = [
            self.vector_store.asimilarity_search(
                query=q,
                index="drug-interaction-index",
                top_k=1
            )
            for q in queries
        ]

        results = await asyncio.gather(*tasks)

        interactions = []
        for result_set in results:
            if result_set and result_set[0]['score'] > 0.85:
                interactions.append({
                    "severity": result_set[0]['metadata'].get('severity', 'minor'),
                    "description": result_set[0]['content']
                })

        return interactions

    async def _check_dosage(self, drug_info: dict, requested_dose: str, patient_data: dict) -> dict:
        """Async dosage validation"""
        await asyncio.sleep(0.05)  # Simulate I/O

        # Parse dose
        import re
        dose_match = re.match(r'(\d+(?:\.\d+)?)\s*(mg|mcg|g)', requested_dose)
        if not dose_match:
            return {"check": "dosage", "severity": "error", "finding": "Invalid dose format"}

        dose_value = float(dose_match.group(1))
        dose_unit = dose_match.group(2)

        # Get formulary ranges
        min_dose = drug_info.get('min_dose', 0)
        max_dose = drug_info.get('max_dose', float('inf'))

        if dose_value < min_dose or dose_value > max_dose:
            return {
                "check": "dosage",
                "severity": "moderate",
                "finding": f"Dose {requested_dose} outside formulary range ({min_dose}-{max_dose}{dose_unit})",
                "recommendation": "Escalate for physician review"
            }

        return {"check": "dosage", "severity": "none", "finding": "Dose within acceptable range"}

    async def _check_controlled_substance(self, drug_info: dict) -> dict:
        """Check DEA schedule"""
        await asyncio.sleep(0.05)  # Simulate policy lookup

        schedule = drug_info.get('dea_schedule')

        if schedule in ['II', 'III', 'IV']:
            return {
                "check": "controlled_substance",
                "schedule": schedule,
                "severity": "moderate",
                "finding": f"Controlled substance Schedule {schedule}",
                "recommendation": "Requires physician co-signature"
            }

        return {"check": "controlled_substance", "severity": "none", "finding": "Non-controlled"}

    def _generate_recommendations(self, findings: list[dict]) -> list[str]:
        """Generate action recommendations"""
        recs = []
        for finding in findings:
            if 'recommendation' in finding:
                recs.append(finding['recommendation'])
        return recs