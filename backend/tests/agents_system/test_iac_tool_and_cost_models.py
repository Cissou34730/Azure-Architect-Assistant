import pytest

from app.agents_system.services.aaa_state_models import AAAProjectState
from app.agents_system.services.state_update_parser import extract_state_updates
from app.agents_system.tools.aaa_iac_tool import AAAGenerateIacTool


def test_iac_tool_emits_state_update_with_iac_artifact() -> None:
    tool = AAAGenerateIacTool()
    response = tool._run(
        iacFiles=[
            {
                "path": "infra/main.bicep",
                "format": "bicep",
                "content": "param location string = resourceGroup().location",
            }
        ],
        validationResults=[{"tool": "bicep build", "status": "skipped"}],
    )

    updates = extract_state_updates(response, user_message="", current_state={})
    assert updates is not None
    assert "iacArtifacts" in updates
    assert updates["iacArtifacts"][0]["files"][0]["path"] == "infra/main.bicep"


def test_iac_tool_computes_cost_from_catalog_without_network() -> None:
    tool = AAAGenerateIacTool()

    pricing_catalog = [
        {
            "serviceName": "Virtual Machines",
            "armRegionName": "westeurope",
            "productName": "Virtual Machines D2 v5",
            "meterName": "Compute",
            "armSkuName": "D2 v5",
            "unitOfMeasure": "1 Hour",
            "retailPrice": 0.1,
            "currencyCode": "EUR",
        }
    ]

    response = tool._run(
        iacFiles=[],
        validationResults=[],
        pricingLines=[
            {
                "name": "VM compute",
                "serviceName": "Virtual Machines",
                "armRegionName": "westeurope",
                "skuName": "D2 v5",
                "monthlyQuantity": 10,
            }
        ],
        pricingCatalog=pricing_catalog,
        baselineReferenceTotalMonthlyCost=1.0,
    )

    updates = extract_state_updates(response, user_message="", current_state={})
    assert updates is not None
    assert "costEstimates" in updates
    est = updates["costEstimates"][0]
    assert est["currencyCode"] == "EUR"
    assert est["totalMonthlyCost"] == pytest.approx(1.0)
    assert est["variancePct"] == pytest.approx(0.0)


def test_project_state_validates_iac_and_cost_artifacts() -> None:
    payload = {
        "iacArtifacts": [
            {
                "id": "iac-1",
                "files": [
                    {
                        "path": "infra/main.tf",
                        "format": "terraform",
                        "content": "resource \"azurerm_resource_group\" \"rg\" {}",
                    }
                ],
                "validationResults": [{"tool": "terraform validate", "status": "pass"}],
            }
        ],
        "costEstimates": [
            {
                "id": "c-1",
                "currencyCode": "USD",
                "totalMonthlyCost": 12.34,
                "lineItems": [
                    {
                        "id": "li-1",
                        "name": "Test",
                        "monthlyQuantity": 1,
                        "unitPrice": 12.34,
                        "monthlyCost": 12.34,
                    }
                ],
            }
        ],
    }

    validated = AAAProjectState.model_validate(payload)
    assert validated.iacArtifacts[0].files[0].format == "terraform"
    assert validated.costEstimates[0].totalMonthlyCost == pytest.approx(12.34)
