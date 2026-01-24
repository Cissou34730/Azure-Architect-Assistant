# Project brief (tech-agnostic)

We are building an online retail order processing system.

## Business goals
- Support shopping cart, checkout, payment authorization, and order fulfillment.
- Provide real-time inventory visibility.
- Integrate with external shipping providers.

## Workload
- 1k orders/day typical, 20k orders/day during promotions.
- 20x read-to-write ratio.

## Data
- Orders, order events, payments status, inventory, products.

## Constraints
- Payments handled via third-party payment processor.
- Integrations must be resilient to vendor downtime.
