# VRAV AI Production Readiness Checklist

## Current stage
Prototype core runtime with in-memory persistence and local HTTP/CLI surfaces.

## Readiness estimate

- Current production-readiness score: **~25%** toward an initial production baseline.
- Remaining to initial production baseline: **~6-10 weeks** with a focused team.
- Remaining to hardened enterprise readiness: **~12-16 weeks** with security, reliability and operations hardening.
- This estimate assumes the current prototype scope remains stable and durable storage, auth, observability and deployment work are prioritized next.

## Gaps to production

1. Durable storage (PostgreSQL/Redis/Kafka) replacing in-memory EventLog/SessionStore.
2. Multi-process safe concurrency and distributed rate limiting.
3. AuthN/AuthZ hardening (JWT/OAuth2, RBAC, key rotation, audit trails).
4. Observability (OpenTelemetry traces, Prometheus metrics, structured logging, alerts).
5. SLO-backed reliability (timeouts, retries, circuit breakers, chaos/load tests).
6. Secure tool execution sandbox and policy engine.
7. API versioning strategy and backward-compatible contracts.
8. Data governance (PII controls, retention policies, encryption, backups).
9. Deployment stack (Docker/K8s, Helm/Terraform, progressive rollouts).
10. Incident response runbooks and on-call process.

## Estimated completion
With a focused team, ~6-10 weeks for an initial production baseline and ~12-16 weeks for hardened enterprise readiness.
