"""
Test Cost Estimator routing and accuracy (Task 3.3.2).

Test Scenarios:
1. Architecture with 5 services → accurate cost estimate
2. Cost estimate with optimization recommendations
3. Error handling (no architecture, invalid services)
4. Regional pricing differences

Usage:
    uv python scripts/test_phase3_cost_estimator.py
"""

import asyncio
import logging
from pathlib import Path

# Add backend to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.agents_system.langgraph.graph_factory import build_project_chat_graph
from app.agents_system.langgraph.state import GraphState

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Test Scenarios
TEST_SCENARIOS = [
    {
        "name": "Cost Estimate - 5 Service Architecture",
        "description": "Standard web application with 5 Azure services",
        "user_message": "How much will this architecture cost per month?",
        "project_state": {
            "name": "E-Commerce Platform",
            "requirements": {
                "workloadType": "Web Application",
                "expectedUsers": "10,000",
                "allowedRegions": ["eastus"],
            },
            "candidateArchitectures": [
                {
                    "name": "Azure Web App with SQL Database",
                    "description": """
                    Architecture:
                    - Azure App Service (P1v3 tier)
                    - Azure SQL Database (S3 tier, 100GB storage)
                    - Azure Storage Account (Standard GRS, 500GB)
                    - Azure Redis Cache (Standard C1)
                    - Application Insights (Standard)
                    """,
                    "components": [
                        {"name": "webapp", "type": "App Service"},
                        {"name": "database", "type": "SQL Database"},
                        {"name": "storage", "type": "Storage Account"},
                        {"name": "cache", "type": "Redis Cache"},
                        {"name": "monitoring", "type": "Application Insights"},
                    ],
                }
            ],
        },
        "expected_activation": True,
        "expected_cost_range": (200, 800),  # USD per month (rough estimate)
    },
    {
        "name": "Cost with Optimization Recommendations",
        "description": "Request cost with optimization suggestions",
        "user_message": "Estimate the cost of this architecture and suggest cost optimization strategies.",
        "project_state": {
            "name": "Data Analytics Platform",
            "requirements": {
                "workloadType": "Data Processing",
                "expectedUsers": "500",
                "allowedRegions": ["eastus2"],
            },
            "candidateArchitectures": [
                {
                    "name": "Analytics with Databricks",
                    "description": """
                    Architecture:
                    - Azure Databricks (Standard tier, 8 nodes)
                    - Azure Data Lake Storage Gen2 (1TB hot storage)
                    - Azure Synapse Analytics (DW100c)
                    - Azure Key Vault
                    """,
                    "components": [
                        {"name": "databricks", "type": "Databricks"},
                        {"name": "datalake", "type": "Data Lake Storage"},
                        {"name": "synapse", "type": "Synapse Analytics"},
                        {"name": "keyvault", "type": "Key Vault"},
                    ],
                }
            ],
        },
        "expected_activation": True,
        "expected_optimizations": ["reserved instances", "right-sizing", "spot instances"],
    },
    {
        "name": "Error Handling - No Architecture",
        "description": "Cost request without finalized architecture",
        "user_message": "How much will my application cost on Azure?",
        "project_state": {
            "name": "Undefined Project",
            "requirements": {
                "workloadType": "Web Application",
            },
            # NO candidateArchitectures
        },
        "expected_activation": False,  # Should NOT route to Cost Estimator
    },
    {
        "name": "Regional Pricing - West Europe",
        "description": "Cost estimate for West Europe region (higher pricing)",
        "user_message": "What's the estimated monthly cost for this architecture in West Europe?",
        "project_state": {
            "name": "European Web App",
            "requirements": {
                "workloadType": "Web Application",
                "allowedRegions": ["westeurope"],
            },
            "candidateArchitectures": [
                {
                    "name": "Simple Web App",
                    "description": """
                    Architecture:
                    - Azure App Service (B2 tier)
                    - Azure SQL Database (Basic tier, 2GB)
                    """,
                    "components": [
                        {"name": "webapp", "type": "App Service"},
                        {"name": "database", "type": "SQL Database"},
                    ],
                }
            ],
        },
        "expected_activation": True,
        "expected_region": "westeurope",
    },
]


async def test_cost_estimator_routing() -> None:
    """Test Cost Estimator routing for all scenarios."""
    logger.info("=" * 80)
    logger.info("PHASE 3 - Task 3.3.2: Testing Cost Estimator Routing and Accuracy")
    logger.info("=" * 80)
    
    # Build graph without database connection (routing test only)
    graph = build_project_chat_graph(db=None)
    
    results = []
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        logger.info("")
        logger.info(f"--- Scenario {i}/{len(TEST_SCENARIOS)}: {scenario['name']} ---")
        logger.info(f"Description: {scenario['description']}")
        logger.info(f"User Message: {scenario['user_message']}")
        logger.info(f"Expected Activation: {scenario['expected_activation']}")
        
        # Prepare state
        state = GraphState(
            project_id="test-project-cost",
            conversation_id="test-conversation-cost",
            user_message=scenario["user_message"],
            current_project_state=scenario["project_state"],
            context_summary=f"Project: {scenario['project_state']['name']}\n{scenario['description']}",
            messages=[],
            chat_history=[],
        )
        
        # Run routing logic
        try:
            result = await graph.ainvoke(state, config={"recursion_limit": 5})
            
            routing_decision = result.get("routing_decision", {})
            agent = routing_decision.get("agent", "main")
            reason = routing_decision.get("reason", "")
            
            # Check if Cost Estimator was selected
            actual_activation = (agent == "cost_estimator")
            
            # Determine test result
            passed = (actual_activation == scenario["expected_activation"])
            status = "✅ PASS" if passed else "❌ FAIL"
            
            logger.info(f"Result: {status}")
            logger.info(f"  Routed to: {agent}")
            logger.info(f"  Reason: {reason}")
            logger.info(f"  Expected Activation: {scenario['expected_activation']}")
            logger.info(f"  Actual Activation: {actual_activation}")
            
            # Check cost estimate if Cost Estimator was activated
            if actual_activation:
                cost_estimate = result.get("cost_estimate", {})
                monthly_cost = cost_estimate.get("monthly_cost")
                annual_cost = cost_estimate.get("annual_cost")
                tco_3_year = cost_estimate.get("tco_3_year")
                region = cost_estimate.get("region", "unknown")
                
                logger.info(f"  Cost Estimate:")
                logger.info(f"    Monthly: ${monthly_cost:,.2f}" if monthly_cost else "    Monthly: Not extracted")
                logger.info(f"    Annual: ${annual_cost:,.2f}" if annual_cost else "    Annual: Not extracted")
                logger.info(f"    3-Year TCO: ${tco_3_year:,.2f}" if tco_3_year else "    3-Year TCO: Not extracted")
                logger.info(f"    Region: {region}")
                
                # Validate cost range if provided
                if "expected_cost_range" in scenario and monthly_cost:
                    min_cost, max_cost = scenario["expected_cost_range"]
                    in_range = min_cost <= monthly_cost <= max_cost
                    range_status = "✅" if in_range else "⚠️"
                    logger.info(f"  Cost Range Check: {range_status} (Expected: ${min_cost}-${max_cost})")
                
                # Validate region if provided
                if "expected_region" in scenario:
                    region_match = region == scenario["expected_region"]
                    region_status = "✅" if region_match else "⚠️"
                    logger.info(f"  Region Check: {region_status} (Expected: {scenario['expected_region']})")
            
            results.append({
                "scenario": scenario["name"],
                "passed": passed,
                "agent": agent,
                "reason": reason,
            })
            
        except Exception as e:
            logger.error(f"❌ EXCEPTION: {e}", exc_info=True)
            results.append({
                "scenario": scenario["name"],
                "passed": False,
                "agent": "ERROR",
                "reason": str(e),
            })
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("SUMMARY: Cost Estimator Routing Tests")
    logger.info("=" * 80)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    logger.info(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    logger.info("")
    
    for result in results:
        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        logger.info(f"{status} - {result['scenario']}")
        logger.info(f"       Routed to: {result['agent']} - {result['reason']}")
    
    if passed == total:
        logger.info("")
        logger.info("🎉 All Cost Estimator routing tests passed!")
        logger.info("")
        logger.info("⚠️ Note: Cost accuracy validation requires manual comparison with Azure Pricing Calculator:")
        logger.info("   https://azure.microsoft.com/en-us/pricing/calculator/")
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Review routing logic.")


if __name__ == "__main__":
    asyncio.run(test_cost_estimator_routing())
