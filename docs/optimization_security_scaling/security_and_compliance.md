## Security Architecture

### Authentication & Authorization
- **OAuth 2.0 + SMART on FHIR**: access control scoping
- **Role-Based Access**: PA vs Physician approval chains
- **Audit Logging**: Immutable append-only logs for audit purpose

### Data Protection
- **PHI Minimization**: Only necessary fields in agent context, 
- **Encryption**: TLS 1.3 in motion, AES-256 at rest
- **Anonymization**: One-way hashing as needed for non-production and storage

### Compliance Controls
- **HIPAA Audit Trail**: Kipling method tracking for every action
- **BAA Requirements**: Subprocessor agreements for LLM APIs (e.g., Bedrock or self-hosted)
- **Retention Policies**: 7-year log retention, purge after statute

### Perioperative Risk Mitigation
- **Controlled Substance Guardrails**: DEA schedule checks
- **Allergy Cross-Reference**: Mandatory before dispensing
- **Dosage Validation**: Range checks against formulary
- **Time-Critical Flags**: Priority routing for preop medications