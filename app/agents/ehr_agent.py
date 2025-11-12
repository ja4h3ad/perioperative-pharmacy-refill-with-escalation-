# app/agents/ehr_agent.py
''' interfaces with ehr using FHIR connectors, with circuit breaker'''

import asyncio
import aiohttp
from typing import Optional
from app.safety.circuit_breaker import AsyncCircuitBreaker


class EHRAgent:
    def __init__(self, fhir_base_url: str = "https://fhir.example.com"):
        self.fhir_base_url = fhir_base_url
        self.circuit_breaker = AsyncCircuitBreaker(
            failure_threshold=5,
            timeout=3.0,
            recovery_timeout=30.0
        )
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """Async context manager for session pooling"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    @AsyncCircuitBreaker.protected
    async def fetch_patient_data(self, mrn: str) -> dict:
        """Fetch patient data with circuit breaker protection"""
        if not self.session:
            self.session = aiohttp.ClientSession()

        try:
            # Parallel FHIR queries
            patient_task = self._get_patient(mrn)
            meds_task = self._get_medications(mrn)
            allergies_task = self._get_allergies(mrn)
            labs_task = self._get_labs(mrn)

            patient, meds, allergies, labs = await asyncio.gather(
                patient_task,
                meds_task,
                allergies_task,
                labs_task,
                return_exceptions=True
            )

            # Handle partial failures gracefully
            return {
                "patient": patient if not isinstance(patient, Exception) else None,
                "active_medications": meds if not isinstance(meds, Exception) else [],
                "allergies": allergies if not isinstance(allergies, Exception) else [],
                "labs": labs if not isinstance(labs, Exception) else {},
                "data_complete": all(
                    not isinstance(d, Exception) for d in [patient, meds, allergies, labs]
                )
            }

        except asyncio.TimeoutError:
            raise EHRTimeoutError(f"EHR query timeout for patient {mrn}")
        except Exception as e:
            raise EHRError(f"EHR query failed: {e}")

    async def _get_patient(self, mrn: str) -> dict:
        """Get patient demographics"""
        async with self.session.get(
                f"{self.fhir_base_url}/Patient/{mrn}",
                timeout=aiohttp.ClientTimeout(total=2.0)
        ) as response:
            response.raise_for_status()
            data = await response.json()

            return {
                "mrn": mrn,
                "name": data.get("name", [{}])[0].get("text"),
                "birthDate": data.get("birthDate"),
                "gender": data.get("gender")
            }

    async def _get_medications(self, mrn: str) -> list[str]:
        """Get active medications"""
        async with self.session.get(
                f"{self.fhir_base_url}/MedicationStatement",
                params={"patient": mrn, "status": "active"},
                timeout=aiohttp.ClientTimeout(total=2.0)
        ) as response:
            response.raise_for_status()
            data = await response.json()

            meds = []
            for entry in data.get("entry", []):
                med_name = entry.get("resource", {}).get("medicationCodeableConcept", {}).get("text")
                if med_name:
                    meds.append(med_name)

            return meds

    async def _get_allergies(self, mrn: str) -> list[dict]:
        """Get patient allergies"""
        async with self.session.get(
                f"{self.fhir_base_url}/AllergyIntolerance",
                params={"patient": mrn},
                timeout=aiohttp.ClientTimeout(total=2.0)
        ) as response:
            response.raise_for_status()
            data = await response.json()

            allergies = []
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                allergies.append({
                    "substance": resource.get("code", {}).get("text"),
                    "severity": resource.get("criticality", "unknown")
                })

            return allergies

    async def _get_labs(self, mrn: str) -> dict:
        """Get relevant lab values (SCr, LFTs)"""
        async with self.session.get(
                f"{self.fhir_base_url}/Observation",
                params={"patient": mrn, "category": "laboratory"},
                timeout=aiohttp.ClientTimeout(total=2.0)
        ) as response:
            response.raise_for_status()
            data = await response.json()

            labs = {}
            for entry in data.get("entry", []):
                resource = entry.get("resource", {})
                code = resource.get("code", {}).get("coding", [{}])[0].get("code")
                value = resource.get("valueQuantity", {}).get("value")

                if code in ["2160-0", "38483-4"]:  # SCr, ALT LOINC codes
                    labs[code] = value

            return labs


class EHRTimeoutError(Exception):
    pass


class EHRError(Exception):
    pass

