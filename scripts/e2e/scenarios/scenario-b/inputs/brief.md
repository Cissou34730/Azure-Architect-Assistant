# Project brief (tech-agnostic)

We are building a fleet telemetry platform for connected devices.

## Business goals
- Securely ingest telemetry from devices deployed worldwide.
- Provide near-real-time dashboards for operations.
- Provide historical analytics for product and reliability teams.

## Workload
- 50k devices in year 1, growing to 250k.
- Average 1 message/minute/device, with bursts.
- Messages are small (0.5-2 KB) JSON payloads.

## Data & queries
- Time-series queries by device, region, and time window.
- Alerts based on thresholds and anomaly detection.
