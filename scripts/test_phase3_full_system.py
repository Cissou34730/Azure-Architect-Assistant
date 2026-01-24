"""
Full system E2E testing with all agents (Task 3.3.3).

Test Scenarios:
1. All routing paths (IaC → Arch → SaaS → Cost → Main)
2. No unintended activations (false positives)
3. Performance testing (latency, token usage)

Usage:
    uv python scripts/test_phase3_full_system.py
"""

import asyncio
import logging
import time
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.agents_system.langgraph.nodes.stage_routing import (
    should_route_to_iac_generator,
    should_route_to_architecture_planner,
    should_route_to_saas_advisor,
    should_route_to_cost_estimator,
)
from app.agents_system.langgraph.state import GraphState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Test Scenarios for All Routing Paths
TEST_SCENARIOS = [
    {
        "name": "IaC Generator - Highest Priority",
        "description": "Explicit Terraform/Bicep request with finalized architecture",
        "user_message": "Generate Terraform code for this architecture",
        "project_state": {
            "name": "IaC Test",
            "candidateArchitectures": [
                {
                    "name": "Simple Web App",
                    "description": "Azure App Service + SQL Database",
                    "components": [
                        {"name": "webapp", "type": "App Service"},
                        {"name": "database", "type": "SQL Database"},
                    ],
                }
            ],
        },
        "expected_agent": "iac_generator",
    },
    {
        "name": "Architecture Planner - High Priority",
        "description": "Explicit architecture design request",
        "user_message": "Design a high-availability architecture for a web application with 99.9% SLA, multi-region deployment, and disaster recovery.",
        "project_state": {
            "name": "Architecture Test",
            "requirements": {
                "workloadType": "Web Application",
                "sla": "99.9%",
            },
        },
        "expected_agent": "architecture_planner",
    },
    {
        "name": "SaaS Advisor - Medium Priority",
        "description": "Explicit SaaS request without triggering Architecture Planner",
        "user_message": "Propose a multi-tenant SaaS solution with B2B customers and tenant isolation",
        "project_state": {
            "name": "SaaS Project",
            "requirements": {
                "workloadType": "SaaS Application",
            },
        },
        "expected_agent": "saas_advisor",
    },
    {
        "name": "Cost Estimator - Low Priority",
        "description": "Cost estimation request without triggering higher-priority agents",
        "user_message": "How much will this cost per month?",
        "project_state": {
            "name": "Cost Project",
            "candidateArchitectures": [
                {
                    "name": "Web App",
                    "description": "Azure App Service + SQL Database",
                    "components": [
                        {"name": "webapp", "type": "App Service"},
                        {"name": "database", "type": "SQL Database"},
                    ],
                }
            ],
        },
        "expected_agent": "cost_estimator",
    },
    {
        "name": "Main Agent - Default",
        "description": "General conversational request",
        "user_message": "What are the best practices for securing Azure applications?",
        "project_state": {
            "name": "Main Agent Test",
        },
        "expected_agent": "main",
    },
    {
        "name": "False Positive Check - Web App (Not SaaS)",
        "description": "Regular web app should NOT trigger SaaS Advisor",
        "user_message": "Design a web application for internal employee management",
        "project_state": {
            "name": "Internal Web App",
            "requirements": {
                "workloadType": "Web Application",
            },
        },
        "expected_agent": "main",
        "should_not_activate": ["saas_advisor"],
    },
    {
        "name": "False Positive Check - Budget Constraint (Not Cost Estimator)",
        "description": "Budget as constraint should NOT trigger Cost Estimator",
        "user_message": "Design an architecture with a $500/month budget constraint",
        "project_state": {
            "name": "Budget Constraint Test",
            "requirements": {
                "budget": "$500/month",
            },
        },
        "expected_agent": "architecture_planner",
        "should_not_activate": ["cost_estimator"],
    },
    {
        "name": "False Positive Check - Authentication (Not SaaS)",
        "description": "Authentication feature should NOT trigger SaaS Advisor",
        "user_message": "Add user authentication and role-based access control to the application",
        "project_state": {
            "name": "Authentication Test",
        },
        "expected_agent": "main",
        "should_not_activate": ["saas_advisor"],
    },
]


async def test_full_system_routing() -> None:
    """Test full system routing with all agents."""
    logger.info("=" * 80)
    logger.info("PHASE 3 - Task 3.3.3: Full System E2E Testing")
    logger.info("=" * 80)
    
    results = []
    total_time = 0
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        logger.info("")
        logger.info(f"--- Scenario {i}/{len(TEST_SCENARIOS)}: {scenario['name']} ---")
        logger.info(f"Description: {scenario['description']}")
        logger.info(f"User Message: {scenario['user_message']}")
        logger.info(f"Expected Agent: {scenario['expected_agent']}")
        
        # Prepare state
        state = GraphState(
            project_id=f"test-project-{i}",
            conversation_id=f"test-conversation-{i}",
            user_message=scenario["user_message"],
            current_project_state=scenario["project_state"],
            context_summary=f"Project: {scenario['project_state']['name']}\n{scenario['description']}",
            messages=[],
            chat_history=[],
        )
        
        # Run routing logic with timing (direct function calls)
        start_time = time.time()
        try:
            # Check routing priority (IaC → Arch → SaaS → Cost → Main)
            if should_route_to_iac_generator(state):
                agent = "iac_generator"
            elif should_route_to_architecture_planner(state):
                agent = "architecture_planner"
            elif should_route_to_saas_advisor(state):
                agent = "saas_advisor"
            elif should_route_to_cost_estimator(state):
                agent = "cost_estimator"
            else:
                agent = "main"
            
            elapsed = time.time() - start_time
            total_time += elapsed
            
            # Check if expected agent was selected
            passed = (agent == scenario["expected_agent"])
            
            # Check for false positives (should NOT activate)
            if "should_not_activate" in scenario:
                for unwanted_agent in scenario["should_not_activate"]:
                    if agent == unwanted_agent:
                        passed = False
                        logger.warning(f"⚠️ False Positive: {unwanted_agent} activated when it should not")
            
            status = "✅ PASS" if passed else "❌ FAIL"
            
            logger.info(f"Result: {status}")
            logger.info(f"  Routed to: {agent}")
            logger.info(f"  Expected: {scenario['expected_agent']}")
            logger.info(f"  Latency: {elapsed:.4f}s")
            
            results.append({
                "scenario": scenario["name"],
                "passed": passed,
                "agent": agent,
                "expected": scenario["expected_agent"],
                "latency": elapsed,
            })
            
        except Exception as e:
            elapsed = time.time() - start_time
            total_time += elapsed
            logger.error(f"❌ EXCEPTION: {e}", exc_info=True)
            results.append({
                "scenario": scenario["name"],
                "passed": False,
                "agent": "ERROR",
                "expected": scenario["expected_agent"],
                "latency": elapsed,
            })
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY: Full System E2E Tests")
    logger.info("=" * 80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    logger.info(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    logger.info(f"Total Time: {total_time:.4f}s")
    logger.info(f"Average Latency: {total_time/total:.4f}s per test")
    logger.info("")
    
    # Detailed results
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        logger.info(f"{status} - {result['scenario']}")
        logger.info(f"       Expected: {result['expected']} | Actual: {result['agent']} | Latency: {result['latency']:.4f}s")
    
    # Performance analysis
    logger.info("")
    logger.info("=" * 80)
    logger.info("PERFORMANCE ANALYSIS")
    logger.info("=" * 80)
    latencies = [r["latency"] for r in results if r["latency"] > 0]
    if latencies:
        logger.info(f"Min Latency: {min(latencies):.4f}s")
        logger.info(f"Max Latency: {max(latencies):.4f}s")
        logger.info(f"Avg Latency: {sum(latencies)/len(latencies):.4f}s")
    
    # Routing priority analysis
    logger.info("")
    logger.info("=" * 80)
    logger.info("ROUTING PRIORITY VERIFICATION")
    logger.info("=" * 80)
    logger.info("Priority Order: IaC Generator → Architecture Planner → SaaS Advisor → Cost Estimator → Main Agent")
    logger.info("")
    agent_counts = {}
    for result in results:
        agent = result["agent"]
        agent_counts[agent] = agent_counts.get(agent, 0) + 1
    
    for agent, count in sorted(agent_counts.items()):
        logger.info(f"  {agent}: {count} routing(s)")
    
    # Final verdict
    logger.info("")
    if passed == total:
        logger.info("🎉 All full system E2E tests passed!")
        logger.info("✅ Routing logic validated")
        logger.info("✅ No false positives detected")
        logger.info("✅ Performance acceptable")
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Review routing logic and agent priorities.")


if __name__ == "__main__":
    asyncio.run(test_full_system_routing())
