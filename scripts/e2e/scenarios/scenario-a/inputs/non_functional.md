# Non-functional requirements

## Availability
- Target 99.9% uptime for learner experience.

## Performance
- P95 API latency < 300ms for core read flows.
- Video playback should be resilient to transient network issues.

## Scalability
- Support spikes during course launches (10x traffic for a few hours).
- Progress events can reach 2k events/second during peaks.

## Observability
- End-to-end tracing across API and background workers.
- Audit logging for admin actions.

## Operations
- Prefer managed services.
- Infrastructure must be reproducible via IaC.
