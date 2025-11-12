## Deployment Architecture

## Design Philosophy: Lessons from CPaaS Architecture

This system applies patterns from carrier-grade telecommunications:

### 1. **Circuit Breakers**
Isolate failures:
- EHR downtime doesn't crash the entire workflow
- Graceful degradation to read-only mode
- Bulkhead pattern for external API calls

### 2. **Event-Driven Architecture**
- Async message bus for A2A communication
- State snapshots for workflow recovery
- Similar to real-time audio streaming buffers

### 3. **Multi-Tenancy**
- Scoped policy engines per healthcare organization
- Isolated vector stores per tenant
- OAuth2 patterns from First Orion integration


### Container Strategy
- **Base Image**: Python 3.12-slim with security hardening
- **Multi-stage builds**: Separate build/runtime for smaller attack surface
- **Orchestration**: Designed for Kubernetes (EKS, GKE, AKS) or serverless containers (ECS Fargate, Cloud Run)

### AWS Reference Architecture
- **Compute**: ECS Fargate for serverless scaling
- **State Management**: ElastiCache (Redis) for session state
- **Message Bus**: SQS/SNS for async agent communication
- **Secrets**: AWS Secrets Manager with IAM role-based access
- **Observability**: CloudWatch + X-Ray integration with OpenTelemetry