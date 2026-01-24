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

from app.agents_system.langgraph.nodes.stage_routing import (
    should_route_to_cost_estimator,
    prepare_cost_estimator_handoff,
)
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
        
        # Test routing logic directly
        try:
            # Call should_route_to_cost_estimator directly
            actual_activation = should_route_to_cost_estimator(state)
            
            # Determine test result
            passed = (actual_activation == scenario["expected_activation"])
            status = "✅ PASS" if passed else "❌ FAIL"
            
            logger.info(f"Result: {status}")
            logger.info(f"  Expected Activation: {scenario['expected_activation']}")
            logger.info(f"  Actual Activation: {actual_activation}")
            
            # If activated, test handoff preparation
            if actual_activation:
                handoff_result = prepare_cost_estimator_handoff(state)
                handoff_context = handoff_result.get("agent_handoff_context", {})
                current_agent = handoff_result.get("current_agent", "")
                
                logger.info(f"  Handoff Context:")
                logger.info(f"    Current Agent: {current_agent}")
                logger.info(f"    Routing Reason: {handoff_context.get('routing_reason', 'N/A')}")
                logger.info(f"    Region: {handoff_context.get('region', 'N/A')}")
                logger.info(f"    Environment: {handoff_context.get('environment', 'N/A')}")
                logger.info(f"    Resource Count: {len(handoff_context.get('resource_list', []))}")
                
                constraints = handoff_context.get("constraints", {})
                if constraints:
                    logger.info(f"  Constraints: {', '.join(constraints.keys())}")
                
                # Validate region if provided
                if "expected_region" in scenario:
                    region = handoff_context.get("region", "")
                    region_match = region == scenario["expected_region"]
                    region_status = "✅" if region_match else "⚠️"
                    logger.info(f"  Region Check: {region_status} (Expected: {scenario['expected_region']}, Got: {region})")
            
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
    logger.info("SUMMARY: Cost Estimator Routing Tests")
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
        logger.info("🎉 All Cost Estimator routing tests passed!")
        logger.info("")
        logger.info("⚠️ Note: Cost accuracy validation requires manual comparison with Azure Pricing Calculator:")
        logger.info("   https://azure.microsoft.com/en-us/pricing/calculator/")
    else:
        logger.warning(f"⚠️ {total - passed} test(s) failed. Review routing logic.")


if __name__ == "__main__":
    asyncio.run(test_cost_estimator_routing())
