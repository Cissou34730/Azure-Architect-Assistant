"""
Test SaaS Advisor routing and behavior (Task 3.3.1).

Test Scenarios:
1. Explicit SaaS request → SaaS Advisor activated
2. Regular web app request → SaaS Advisor NOT activated
3. Enterprise single-tenant → SaaS Advisor NOT activated
4. Suitability question → SaaS Advisor provides analysis

Usage:
    uv python scripts/test_phase3_saas_advisor.py
"""

import asyncio
import logging
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.agents_system.langgraph.nodes.stage_routing import (
    should_route_to_saas_advisor,
    prepare_saas_advisor_handoff,
)
from app.agents_system.langgraph.state import GraphState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Test Scenarios
TEST_SCENARIOS = [
    {
        "name": "Explicit SaaS Request - Should Activate",
        "description": "Multi-tenant B2B SaaS with enterprise customers",
        "user_message": "Design a multi-tenant SaaS architecture for a project management tool. We expect 500 B2B enterprise customers with 50-200 users each. Need tenant isolation for data security and compliance with SOC 2.",
        "project_state": {
            "name": "Enterprise Project Management SaaS",
            "requirements": {
                "workloadType": "Web Application",
                "expectedUsers": "25,000-100,000",
                "compliance": ["SOC 2", "GDPR"],
                "sla": "99.9%",
            },
        },
        "expected_activation": True,
        "expected_tenant_model": ["silo", "pool", "bridge"],  # Should recommend one of these
    },
    {
        "name": "Regular Web App - Should NOT Activate",
        "description": "Standard web application with authentication",
        "user_message": "Design a web application for employee performance reviews. It needs user authentication, a dashboard, and reporting capabilities. About 1,000 internal employees will use it.",
        "project_state": {
            "name": "Employee Performance Review System",
            "requirements": {
                "workloadType": "Web Application",
                "expectedUsers": "1,000",
                "sla": "99.5%",
            },
        },
        "expected_activation": False,
    },
    {
        "name": "Enterprise Single-Tenant - Should NOT Activate",
        "description": "Internal corporate application",
        "user_message": "We need an internal expense tracking system for our company. It should integrate with our existing AD, support 5,000 employees, and provide manager approval workflows.",
        "project_state": {
            "name": "Internal Expense Tracker",
            "requirements": {
                "workloadType": "Web Application",
                "expectedUsers": "5,000",
                "compliance": ["Internal Policy"],
            },
        },
        "expected_activation": False,
    },
    {
        "name": "SaaS Suitability Question - Should Activate",
        "description": "User asks if SaaS model is appropriate",
        "user_message": "I'm building an invoicing application for small businesses. Should this be a SaaS model or single-tenant deployments for each customer? I expect 200-300 customers with 1-10 users each.",
        "project_state": {
            "name": "Small Business Invoicing",
            "requirements": {
                "workloadType": "Web Application",
                "expectedUsers": "2,000-3,000",
            },
        },
        "expected_activation": True,
    },
]


async def test_saas_advisor_routing() -> None:
    """Test SaaS Advisor routing for all scenarios."""
    logger.info("=" * 80)
    logger.info("PHASE 3 - Task 3.3.1: Testing SaaS Advisor Routing")
    logger.info("=" * 80)
    
    results = []
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        logger.info("")
        logger.info(f"--- Scenario {i}/{len(TEST_SCENARIOS)}: {scenario['name']} ---")
        logger.info(f"Description: {scenario['description']}")
        logger.info(f"User Message: {scenario['user_message']}")
        logger.info(f"Expected Activation: {scenario['expected_activation']}")
        
        # Prepare state
        state = GraphState(
            project_id="test-project-saas",
            conversation_id="test-conversation-saas",
            user_message=scenario["user_message"],
            current_project_state=scenario["project_state"],
            context_summary=f"Project: {scenario['project_state']['name']}\n{scenario['description']}",
            messages=[],
            chat_history=[],
        )
        
        # Test routing logic directly
        try:
            # Call should_route_to_saas_advisor directly
            actual_activation = should_route_to_saas_advisor(state)
            
            # Determine test result
            passed = (actual_activation == scenario["expected_activation"])
            status = "✅ PASS" if passed else "❌ FAIL"
            
            logger.info(f"Result: {status}")
            logger.info(f"  Expected Activation: {scenario['expected_activation']}")
            logger.info(f"  Actual Activation: {actual_activation}")
            
            # If activated, test handoff preparation
            if actual_activation:
                handoff_result = prepare_saas_advisor_handoff(state)
                handoff_context = handoff_result.get("agent_handoff_context", {})
                current_agent = handoff_result.get("current_agent", "")
                
                logger.info(f"  Handoff Context:")
                logger.info(f"    Current Agent: {current_agent}")
                logger.info(f"    Routing Reason: {handoff_context.get('routing_reason', 'N/A')}")
                
                tenant_reqs = handoff_context.get("tenant_requirements", {})
                logger.info(f"  Tenant Requirements:")
                logger.info(f"    Customer Type: {tenant_reqs.get('customer_type', 'Not detected')}")
                logger.info(f"    Expected Tenants: {tenant_reqs.get('expected_tenants', 'Not detected')}")
                logger.info(f"    Isolation Level: {tenant_reqs.get('isolation_level', 'Not detected')}")
                logger.info(f"    Compliance: {tenant_reqs.get('compliance', [])}")
            
            results.append({
                "scenario": scenario["name"],
                "passed": passed,
                "activation": actual_activation,
            })
            
        except Exception as e:
            logger.error(f"❌ EXCEPTION: {e}", exc_info=True)
            results.append({
                "scenario": scenario["name"],
                "passed": False,
                "activation": "ERROR",
            })
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY: SaaS Advisor Routing Tests")
    logger.info("=" * 80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    logger.info(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    logger.info("")
    
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        logger.info(f"{status} - {result['scenario']}")
        logger.info(f"       Activation: {result['activation']}")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 All SaaS Advisor routing tests passed!")
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Review routing logic.")


if __name__ == "__main__":
    asyncio.run(test_saas_advisor_routing())
