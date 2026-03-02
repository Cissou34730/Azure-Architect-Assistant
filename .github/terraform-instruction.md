---
description: 'Create or modify solutions built using Terraform on Azure.'
applyTo: '**/*.terraform, **/*.tf, **/*.tfvars, **/*.tflint.hcl, **/*.tfstate, **/*.tf.json, **/*.tfvars.json'
---

# Terraform / Azure Rules (Scoped)

## Scope

- Applies only to Terraform files (`*.tf`, `*.tfvars`, `*.tf.json`, etc.).

## General Instructions

- Keep IaC changes minimal and targeted.
- Keep changes parameterized and environment-agnostic.

## Safety Requirements

- Never store secrets in code, state, or outputs.
- Never edit `*.tfstate` or `.terraform/*` as source code.
- Parameterize values; avoid hardcoded environment-specific constants.
- Favor least privilege and secure defaults.

## IaC Quality Requirements

- Keep module layout clear (`main.tf`, `variables.tf`, `outputs.tf`, `locals.tf`, provider config).
- Prefer implicit dependencies; avoid unnecessary `depends_on`.
- Use typed variables and clear descriptions.
- Mark sensitive outputs with `sensitive = true`.

## Best Practices

- Keep reusable modules focused and composable.
- Keep naming and tagging consistent across resources.
- Prefer managed identity and private connectivity where applicable.

## Azure-Specific Requirements

- Prefer Azure Verified Modules when suitable and approved.
- Prefer Managed Identity over explicit credentials.
- Reuse existing RG/network primitives when specified.

## Validation and Delivery Policy

- `terraform validate`, `plan`, and `apply` require explicit user request.
- Do not execute deployment steps implicitly.

## Terraform Definition of Done

1. Requested IaC behavior implemented with minimal scope.
2. Security-sensitive values handled safely.
3. Changes remain parameterized and maintainable.
