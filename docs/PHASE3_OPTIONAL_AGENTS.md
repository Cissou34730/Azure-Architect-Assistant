# Phase 3: Optional Specialized Agents - Implementation Guide

**Date:** January 24, 2026  
**Version:** 1.0  
**Branch:** `feature/optional-agents`  
**Duration:** 2 weeks  
**Prerequisites:** Phase 2 Multi-Agent Architecture Complete

---

## Executive Summary

Phase 3 adds **optional specialized agents** for SaaS scenarios and cost estimation to the Azure Architecture Assistant. These agents activate **only when explicitly needed**, avoiding unnecessary complexity for standard architecture requests.

### Key Principles
1. **Strict Activation Rules**: SaaS Advisor only triggers on explicit SaaS keywords
2. **Cost on Demand**: Cost Estimator runs only when user requests pricing
3. **No False Positives**: Regular web apps don't trigger SaaS patterns
4. **Graceful Degradation**: Main agent handles cases if sub-agents unavailable

---

## Objectives

### Primary Goals
- ✅ Add SaaS-specific architectural guidance (multi-tenancy, isolation, scaling)
- ✅ Integrate Azure Retail Prices API for accurate cost estimation
- ✅ Maintain clean separation: optional agents don't bloat core flows

### Success Criteria
- SaaS Advisor triggers only on explicit SaaS requests (0% false positives)
- Cost estimates within 5% of Azure Pricing Calculator
- No performance degradation for non-SaaS, non-cost requests
- All E2E tests pass with Phase 3 agents

---

## Architecture Overview

### Current Multi-Agent System (Phase 2)
```
Main Agent → orchestrator, requirement clarification
├─ Architecture Planner → C4 diagrams, NFR analysis, target architecture
└─ IaC Generator → Bicep/Terraform code generation
```

### Phase 3 Extensions
```
Main Agent
├─ Architecture Planner
├─ IaC Generator
├─ SaaS Advisor (NEW) → tenant isolation, B2B/B2C patterns, scaling stamps
└─ Cost Estimator (NEW) → Azure Pricing API, TCO calculation, optimization
```

---

## Agent Specifications

### 1. SaaS Advisor Sub-Agent

#### Purpose
Provide specialized guidance for **Software-as-a-Service architectures** with multi-tenancy, tenant isolation, and SaaS-specific scaling patterns.

#### Activation Triggers (Strict)
```python
# EXPLICIT keywords required
saas_keywords = [
    "saas", "multi-tenant", "multitenant", 
    "b2b saas", "b2c saas", "tenant isolation",
    "subscription-based", "saas architecture"
]

# User questions about SaaS suitability
suitability_questions = [
    "should this be saas",
    "is saas appropriate",
    "saas or not"
]
```

#### DO NOT Activate For
- Regular web applications (even with auth)
- Single-tenant enterprise apps
- Internal tools
- Simple CRUD apps

#### Specialized Knowledge
1. **Tenant Isolation Models**
   - Silo: Dedicated resources per tenant (highest isolation)
   - Pool: Shared resources with logical separation
   - Bridge: Hybrid approach (shared compute, isolated data)

2. **B2B vs B2C Patterns**
   - B2B: Enterprise customers, custom branding, SSO, compliance
   - B2C: Individual users, self-service, social auth, scale

3. **Noisy Neighbor Mitigation**
   - Rate limiting per tenant
   - Resource quotas (CPU, memory, API calls)
   - Separate scaling groups
   - Backpressure mechanisms

4. **Deployment Stamps**
   - Deploy entire stack per region/customer tier
   - Isolate blast radius
   - Scale horizontally with new stamps
   - Blue-green deployment per stamp

#### Handoff Context
```yaml
saas_context:
  tenant_model: "silo|pool|bridge"
  customer_type: "b2b|b2c|hybrid"
  expected_tenants: 100
  isolation_requirements: "high|medium|low"
  compliance: ["GDPR", "SOC2"]
  current_architecture: "...parsed from state..."
```

#### Output Format
- Tenant isolation strategy with diagrams
- Data segregation approach
- Scaling strategy (stamps vs shared pool)
- Cost implications per model
- ADR for tenant architecture

---

### 2. Cost Estimator Sub-Agent

#### Purpose
Calculate accurate Azure cost estimates using **Azure Retail Prices API** and provide optimization recommendations.

#### Activation Triggers
```python
cost_keywords = [
    "cost", "price", "pricing", "how much",
    "estimate cost", "tco", "total cost of ownership",
    "monthly cost", "annual cost"
]
```

#### Prerequisites
- Architecture proposal finalized (services identified)
- Region specified (defaults to East US)
- Resource SKUs known or inferrable

#### Azure Retail Prices API Integration

**Endpoint:** `https://prices.azure.com/api/retail/prices`

**Query Parameters:**
- `$filter`: `serviceName eq 'Virtual Machines' and armRegionName eq 'eastus'`
- `currencyCode`: `USD`
- `api-version`: `2023-01-01-preview`

**Example Query:**
```http
GET https://prices.azure.com/api/retail/prices
?$filter=serviceName eq 'Virtual Machines' 
  and armRegionName eq 'eastus' 
  and armSkuName eq 'Standard_D2s_v3'
&currencyCode=USD
```

**Response:**
```json
{
  "Items": [{
    "currencyCode": "USD",
    "retailPrice": 0.096,
    "unitOfMeasure": "1 Hour",
    "armSkuName": "Standard_D2s_v3",
    "serviceName": "Virtual Machines"
  }]
}
```

#### Cost Calculation Logic
```python
# Monthly cost = hourly_rate * 730 hours
# Annual cost = monthly_cost * 12
# TCO (3 years) = annual_cost * 3

def calculate_service_cost(service_name, sku, region, quantity=1):
    hourly_rate = query_azure_pricing_api(service_name, sku, region)
    monthly_cost = hourly_rate * 730 * quantity
    return {
        "service": service_name,
        "sku": sku,
        "quantity": quantity,
        "monthly_cost": monthly_cost,
        "annual_cost": monthly_cost * 12
    }
```

#### Optimization Recommendations
1. **Reserved Instances**: 1-year RI = 40% savings, 3-year RI = 60% savings
2. **Right-Sizing**: Analyze workload, recommend smaller SKUs
3. **Auto-Scaling**: Turn off dev/test environments off-hours
4. **Azure Hybrid Benefit**: Reuse Windows Server licenses
5. **Spot Instances**: 70-90% savings for fault-tolerant workloads

#### Handoff Context
```yaml
cost_context:
  architecture: "...parsed architecture..."
  services:
    - name: "App Service"
      sku: "P1v3"
      quantity: 2
      region: "eastus"
    - name: "SQL Database"
      sku: "S3"
      quantity: 1
      region: "eastus"
  region: "eastus"
  environment: "production"
```

#### Output Format
```markdown
## Cost Estimate

**Total Monthly Cost:** $1,234.56
**Total Annual Cost:** $14,814.72
**3-Year TCO:** $44,444.16

### Breakdown
| Service | SKU | Qty | Monthly | Annual |
|---------|-----|-----|---------|--------|
| App Service | P1v3 | 2 | $292.00 | $3,504.00 |
| SQL Database | S3 | 1 | $150.00 | $1,800.00 |
| Storage | LRS | 1 | $21.00 | $252.00 |

### Optimization Opportunities
1. **Reserved Instances**: Save $4,000/year with 1-year RI on App Service
2. **Right-Sizing**: SQL Database S2 sufficient for 80% of queries (save $600/year)
3. **Dev/Test Pricing**: 40% discount for non-production environments
```

---

## Implementation Tasks

### Task 3.0: Phase 3 Setup ✅
- [x] Create `feature/optional-agents` branch
- [x] Document Phase 3 plan (this document)
- [ ] Confirm Phase 3 scope and priority

### Task 3.1: SaaS Advisor Implementation
1. **Task 3.1.1**: Create `saas_advisor_prompt.yaml` (~150 lines)
2. **Task 3.1.2**: Create `saas_advisor.py` node implementation
3. **Task 3.1.3**: Add SaaS routing to `stage_routing.py`
4. **Task 3.1.4**: Integrate into `graph_factory.py`

**Estimated Effort:** 3-4 days

### Task 3.2: Cost Estimator Implementation
1. **Task 3.2.1**: Research Azure Retail Prices API (0.5 day)
2. **Task 3.2.2**: Create `cost_estimator_prompt.yaml` (~180 lines)
3. **Task 3.2.3**: Create `retail_prices_client.py` (1-2 days)
4. **Task 3.2.4**: Create `cost_estimator.py` node (2 days)
5. **Task 3.2.5**: Add cost routing to graph (0.5 day)

**Estimated Effort:** 5-6 days

### Task 3.3: Testing & Documentation
1. **Task 3.3.1**: Test SaaS Advisor activation rules
2. **Task 3.3.2**: Test Cost Estimator accuracy
3. **Task 3.3.3**: Full system E2E tests
4. **Task 3.3.4**: Update documentation (CHANGELOG, SYSTEM_ARCHITECTURE, user guide)

**Estimated Effort:** 2-3 days

**Total Phase 3 Duration:** ~2 weeks

---

## Routing Priority

**Agent Router Decision Tree:**
```
1. Check IaC request + architecture exists → IaC Generator
2. Check architecture/design request → Architecture Planner
3. Check explicit SaaS keywords → SaaS Advisor (NEW)
4. Check cost/pricing request → Cost Estimator (NEW)
5. Default → Main Agent
```

**Key Principle:** Optional agents have **lower priority** than core agents (Architecture Planner, IaC Generator).

---

## State Schema Extensions

### Phase 3 Additions to GraphState
```python
class GraphState(TypedDict):
    # ... Phase 2 fields ...
    
    # Phase 3: Optional Agents
    saas_context: Optional[Dict[str, Any]]  # Tenant model, customer type, isolation
    cost_estimate: Optional[Dict[str, Any]]  # Pricing lines, total cost, optimizations
    pricing_region: Optional[str]  # Default: "eastus"
```

---

## Testing Strategy

### 1. SaaS Advisor Tests

**Positive Cases (Should Activate):**
```python
# Explicit SaaS request
"Design a multi-tenant SaaS architecture for B2B customers"

# Tenant isolation
"How should I implement tenant isolation in my SaaS app?"

# B2B/B2C question
"What's the difference between B2B and B2C SaaS architectures?"
```

**Negative Cases (Should NOT Activate):**
```python
# Regular web app
"Design a web application with user authentication"

# Enterprise app
"Single-tenant application for internal HR system"

# E-commerce
"Build an e-commerce website with product catalog"
```

### 2. Cost Estimator Tests

**Test Scenarios:**
```python
# Architecture with known services
services = [
    {"name": "App Service", "sku": "P1v3", "qty": 2},
    {"name": "SQL Database", "sku": "S3", "qty": 1},
    {"name": "Storage Account", "sku": "LRS", "qty": 1}
]
# Expected: ~$463/month

# Compare with Azure Pricing Calculator
# Tolerance: ±5%
```

### 3. Regression Tests
- All Phase 1 and Phase 2 E2E tests must pass
- No token usage increase for non-SaaS, non-cost requests
- Routing latency < 100ms

---

## Rollout Plan

### Stage 1: SaaS Advisor (Week 1)
- Day 1-2: Create prompt and node
- Day 3: Add routing logic
- Day 4: Testing and validation

### Stage 2: Cost Estimator (Week 2)
- Day 1: Research API and create client
- Day 2-3: Create prompt and node
- Day 4-5: Integration and testing

### Stage 3: Documentation & Merge
- Day 6-7: Full system testing
- Day 8: Documentation updates
- Day 9: Code review and merge

---

## Risks & Mitigation

### Risk 1: SaaS False Positives
**Risk:** Regular web apps incorrectly trigger SaaS Advisor

**Mitigation:**
- Strict keyword matching (explicit SaaS terms only)
- Test suite with 20+ negative cases
- User feedback loop to tune triggers

### Risk 2: Azure Pricing API Rate Limits
**Risk:** API throttling during high-volume cost requests

**Mitigation:**
- Implement caching (1-hour TTL for pricing data)
- Batch API queries per region
- Fallback to cached/approximate pricing

### Risk 3: Cost Estimate Accuracy
**Risk:** Pricing API returns unexpected SKUs or regions

**Mitigation:**
- Validate API responses
- Use default pricing for unknown SKUs
- Disclaimer: "Estimate only, verify with Azure Pricing Calculator"

---

## Success Metrics

### Accuracy
- SaaS Advisor: 0% false positive rate on test suite
- Cost Estimator: ±5% accuracy vs Azure Pricing Calculator

### Performance
- Agent routing: < 100ms decision time
- Cost API query: < 2 seconds per estimate
- No degradation for non-optional-agent requests

### Adoption
- User feedback: "Cost estimates save time"
- SaaS scenarios: Clear tenant isolation guidance
- Documentation: "When Each Agent Activates" guide used

---

## File Changes Summary

### New Files (8)
1. `backend/config/prompts/saas_advisor_prompt.yaml` - SaaS agent prompt
2. `backend/app/agents_system/langgraph/nodes/saas_advisor.py` - SaaS node
3. `backend/config/prompts/cost_estimator_prompt.yaml` - Cost agent prompt
4. `backend/app/services/pricing/retail_prices_client.py` - Azure Pricing API client
5. `backend/app/agents_system/langgraph/nodes/cost_estimator.py` - Cost node
6. `docs/PHASE3_OPTIONAL_AGENTS.md` - This document
7. `docs/AGENT_ACTIVATION_GUIDE.md` - User guide: when each agent activates
8. `backend/tests/test_optional_agents.py` - Test suite

### Modified Files (4)
1. `backend/app/agents_system/langgraph/nodes/stage_routing.py` - Add SaaS/Cost routing
2. `backend/app/agents_system/langgraph/graph_factory.py` - Integrate new nodes
3. `backend/app/agents_system/langgraph/state.py` - Add saas_context, cost_estimate fields
4. `CHANGELOG.md` - Add [1.3.0] entry

---

## References

- [Azure Retail Prices API Docs](https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices)
- [Multi-Tenant SaaS Guidance](https://learn.microsoft.com/azure/architecture/guide/multitenant/overview)
- [Deployment Stamps Pattern](https://learn.microsoft.com/azure/architecture/patterns/deployment-stamp)
- [Agent Enhancement Plan](./AGENT_ENHANCEMENT_IMPLEMENTATION_PLAN.md) - Original Phase 3 specification
- [Multi-Agent Architecture](./MULTI_AGENT_ARCHITECTURE.md) - Phase 2 foundation

---

**Document Version History:**
- v1.0 (2026-01-24): Initial Phase 3 plan created
