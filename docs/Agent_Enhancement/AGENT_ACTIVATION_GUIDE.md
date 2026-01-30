# Agent Activation Guide

This guide explains when each specialized agent activates and how to trigger specific agents for your Azure architecture needs.

## Agent Routing Priority

The system uses a priority-based routing system. When you send a request, agents are checked in this order:

```
1. IaC Generator (Highest Priority)
   ↓
2. Architecture Planner
   ↓
3. SaaS Advisor
   ↓
4. Cost Estimator (Lowest Priority)
   ↓
5. Main Agent (Default)
```

**Important**: Higher-priority agents can intercept requests intended for lower-priority agents if their keywords match.

---

## IaC Generator Sub-Agent

**When it activates**: Generates Infrastructure as Code (Terraform or Bicep) for finalized architectures.

### Activation Requirements
- ✅ **Must have**: Finalized architecture (`candidateArchitectures` exists in project state)
- ✅ **Must include**: IaC-related keywords in your request

### Keywords that trigger activation
- `terraform`
- `bicep`
- `iac` or `infrastructure as code`
- `generate terraform/bicep`
- `create iac`
- `deploy` or `provision`

### Example requests that activate IaC Generator

✅ **Will activate**:
- "Generate Terraform code for this architecture"
- "Create Bicep templates for the proposed solution"
- "I need IaC for deployment"
- "Provision these resources with Terraform"

❌ **Will NOT activate** (no finalized architecture):
- "Generate Terraform for a web app" (no architecture in state yet)
- "Can you show me how to write Bicep?" (general question, no specific architecture)

### What you'll get
- Production-ready Terraform or Bicep code
- Resource parameterization and modularization
- Dependency management between resources
- Best practices for IaC structure
- Schema validation using MCP tools

---

## Architecture Planner Sub-Agent

**When it activates**: Designs complex Azure architectures with NFR analysis and C4 diagrams.

### Activation Requirements
- ✅ **Must include**: Architecture/design keywords in your request
- ✅ **OR**: Complexity indicators detected (multi-region, HA, DR, compliance, microservices)

### Keywords that trigger activation
- `architecture`
- `design the architecture` or `design solution`
- `propose architecture` or `architecture proposal`
- `candidate architecture`
- `system design`
- `how should i architect`
- `architecture diagram`

### Complexity indicators that trigger activation
When 3+ of these appear in your requirements:
- `multi-region`, `global`, `worldwide`, `distributed`
- `high availability` or `HA`
- `disaster recovery` or `DR`
- Compliance requirements: `SOC 2`, `HIPAA`, `GDPR`, `PCI DSS`
- `microservices`
- `event-driven`
- `real-time`
- SLA targets: `99.9%`, `99.95%`, `99.99%`

### Example requests that activate Architecture Planner

✅ **Will activate**:
- "Design a high-availability architecture for a web application with 99.9% SLA"
- "Propose an architecture for a multi-region e-commerce platform"
- "I need a solution with disaster recovery and HIPAA compliance"
- "Create a microservices architecture for our application"

❌ **Will NOT activate** (too general or missing keywords):
- "What are best practices for Azure?" (general question)
- "I need help with my app" (no architecture keywords)

### What you'll get
- Complete target architecture design
- C4 diagrams (System Context, Container)
- Functional flow diagrams
- Comprehensive NFR analysis (Scalability, Performance, Security, Reliability, Maintainability)
- Phased delivery planning (optional MVP path)
- Trade-off analysis

---

## SaaS Advisor Sub-Agent

**When it activates**: Provides specialized guidance for multi-tenant SaaS architectures.

### Activation Requirements
- ✅ **Must include**: Explicit SaaS keywords in your request (strict matching)
- ⚠️ **Note**: Context-based routing disabled to avoid false positives

### Keywords that trigger activation
- `saas` or `SaaS`
- `multi-tenant` or `multitenant` or `multi tenant`
- `b2b saas` or `b2c saas`
- `tenant isolation`
- `subscription-based`
- `saas architecture`
- `deployment stamps`
- `noisy neighbor`

### Suitability questions that trigger activation
- "Should this be SaaS?"
- "Is SaaS appropriate for this?"
- "Is this suitable for SaaS?"
- "SaaS or not?"
- "Multi-tenant or single-tenant?"
- "Should I use SaaS?"
- "Do you recommend SaaS?"

### Example requests that activate SaaS Advisor

✅ **Will activate**:
- "Design a multi-tenant SaaS architecture for a project management tool"
- "I'm building an invoicing app. Should this be SaaS or single-tenant?"
- "How do I implement tenant isolation for B2B customers?"
- "I need a SaaS solution with 500 enterprise clients"
- "What's the best multi-tenant model for my application?"

❌ **Will NOT activate** (no explicit SaaS keywords):
- "Design a web application for employee performance reviews" (internal app, not SaaS)
- "I need user authentication for my app" (feature request, not SaaS-specific)
- "Create an internal expense tracking system" (enterprise single-tenant)

### What you'll get
- **Tenant Architecture Models**: Silo (dedicated), Pool (shared), Bridge (hybrid)
- **Isolation Strategies**: data layer, compute layer, network layer, storage layer
- **B2B vs B2C Patterns**: SSO integration, onboarding, billing models, customization
- **Noisy Neighbor Mitigation**: rate limiting, quotas, circuit breakers
- **Deployment Stamps**: geographic stamps, tier-based stamps
- **Cost Analysis**: per-tenant economics, pricing models (per-user, per-feature, tiered)
- **Suitability Analysis**: trade-offs, when SaaS is/isn't appropriate

---

## Cost Estimator Sub-Agent

**When it activates**: Estimates Azure costs and provides optimization recommendations.

### Activation Requirements
- ✅ **Must have**: Finalized architecture (`candidateArchitectures` exists in project state)
- ✅ **Must include**: Cost-related keywords in your request

### Keywords that trigger activation
- `cost`
- `price` or `pricing`
- `how much`
- `TCO` or `total cost of ownership`
- `budget estimate`
- `cost estimate` or `estimate cost`
- `monthly cost` or `annual cost`
- `pricing breakdown`
- `cost analysis` or `cost breakdown` or `cost calculation`
- `cost comparison` or `cost optimization`

### Example requests that activate Cost Estimator

✅ **Will activate** (has finalized architecture):
- "How much will this architecture cost per month?"
- "Estimate the monthly cost for this solution"
- "What's the TCO for this architecture over 3 years?"
- "Calculate cost estimate with optimization recommendations"
- "Compare pricing for different regions"

❌ **Will NOT activate** (no finalized architecture):
- "How much does Azure cost?" (no specific architecture)
- "What's the price of App Service?" (general pricing question, no architecture)
- "Design an architecture with a $500/month budget" (budget as constraint, not requesting estimate - will route to Architecture Planner)

### What you'll get
- **Cost Summary Table**: monthly, annual, 3-year TCO
- **Breakdown by Service**: per-resource cost details
- **Regional Pricing**: differences between Azure regions (e.g., +15% West Europe, +30% Brazil South)
- **Optimization Strategies** with quantified savings:
  - Reserved Instances: 40-60% savings (1-year, 3-year)
  - Right-Sizing: match SKU to actual usage
  - Azure Hybrid Benefit (AHB): 30-55% savings for SQL/Windows
  - Spot Instances: 70-90% savings for fault-tolerant workloads
  - Auto-Scaling: 75% savings for dev/test
  - Storage Tiering: Hot → Cool → Archive
- **Service-Specific Pricing**: App Service, SQL Database, Storage, Functions, Cosmos DB
- **Azure Retail Prices API Integration**: real-time pricing data

---

## Main Agent (Default)

**When it activates**: Default fallback for all other requests.

### Handles
- General Azure questions
- Requirement clarification
- Best practices guidance
- General conversational interaction
- Requests that don't match other agent criteria

### Example requests
- "What are Azure security best practices?"
- "Explain the Well-Architected Framework"
- "How do I choose between SQL Database and Cosmos DB?"
- "What's the difference between App Service and Functions?"

---

## Best Practices

### 1. Be Explicit with Keywords
Use specific keywords to trigger the agent you want:
- Want IaC? Say "Generate **Terraform**" not "Create infrastructure"
- Want cost estimate? Say "**How much will this cost**" not "Is this expensive?"
- Want SaaS guidance? Say "**multi-tenant SaaS**" not just "scalable web app"

### 2. Ensure Prerequisites
- **IaC Generator**: Finalize architecture first before requesting IaC
- **Cost Estimator**: Finalize architecture first before requesting cost estimate
- **Architecture Planner**: Provide requirements and complexity indicators
- **SaaS Advisor**: Explicitly mention multi-tenancy or SaaS

### 3. Avoid Keyword Conflicts
Higher-priority agents can intercept requests:
- ❌ "Design a multi-tenant **architecture**" → Routes to Architecture Planner (not SaaS Advisor)
- ✅ "Propose a multi-tenant SaaS solution" → Routes to SaaS Advisor

### 4. Ask Suitability Questions
If unsure which approach to use:
- "Should this be SaaS or single-tenant?"
- "Do I need multi-region deployment?"
- "What's the best architecture for my requirements?"

---

## Troubleshooting

### "Why didn't the SaaS Advisor activate?"
- ✅ Check: Did you use explicit SaaS keywords? ("saas", "multi-tenant", "B2B/B2C")
- ❌ Common mistake: Using "web application" or "authentication" (too general)

### "Why did Architecture Planner activate instead of Cost Estimator?"
- ✅ Check: Did you use "architecture" keyword in your cost request?
- ❌ Common mistake: "Calculate cost for this **architecture**" (triggers Architecture Planner)
- ✅ Solution: Use "How much will this cost?" or "Calculate cost estimate"

### "Why didn't IaC Generator activate?"
- ✅ Check: Do you have a finalized architecture in project state?
- ❌ Common mistake: Requesting IaC before designing architecture
- ✅ Solution: Design architecture first, then request IaC generation

### "I want SaaS guidance but Architecture Planner responded"
- ✅ Check: Did you use "design" or "architecture" in your request?
- ❌ Common mistake: "Design a multi-tenant architecture" (triggers Architecture Planner first)
- ✅ Solution: Use "Propose a multi-tenant SaaS solution" (avoids "design"/"architecture")

---

## Summary

| Agent | Priority | Requires Architecture | Strict Keywords | Example Trigger |
|-------|----------|----------------------|-----------------|-----------------|
| **IaC Generator** | 1 (Highest) | ✅ Yes | terraform, bicep, iac | "Generate Terraform code" |
| **Architecture Planner** | 2 | ❌ No | architecture, design, proposal | "Design a high-availability architecture" |
| **SaaS Advisor** | 3 | ❌ No | saas, multi-tenant, B2B/B2C | "Propose a multi-tenant SaaS solution" |
| **Cost Estimator** | 4 (Lowest) | ✅ Yes | cost, price, how much, TCO | "How much will this cost per month?" |
| **Main Agent** | 5 (Default) | ❌ No | (any) | "What are Azure best practices?" |

---

## Testing

To validate routing behavior, run the comprehensive test suites:

```powershell
# Test SaaS Advisor routing (4 scenarios)
uv run python scripts/test_phase3_saas_advisor.py

# Test Cost Estimator routing (4 scenarios)
uv run python scripts/test_phase3_cost_estimator.py

# Test full system routing (8 scenarios)
uv run python scripts/test_phase3_full_system.py
```

All tests should pass with 100% success rate.

---

For technical implementation details, see [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md).
