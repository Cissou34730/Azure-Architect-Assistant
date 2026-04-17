"""Architect profile domain model."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ArchitectProfile(BaseModel):
    """Single-user architect preferences persisted for installation defaults."""

    model_config = ConfigDict(populate_by_name=True)

    default_region_primary: str = Field(default="eastus", alias="defaultRegionPrimary")
    default_region_secondary: str | None = Field(default=None, alias="defaultRegionSecondary")
    default_iac_flavor: Literal["bicep", "terraform"] = Field(
        default="bicep",
        alias="defaultIacFlavor",
    )
    compliance_baseline: list[str] = Field(default_factory=list, alias="complianceBaseline")
    monthly_cost_ceiling: float | None = Field(default=None, alias="monthlyCostCeiling")
    preferred_vm_series: list[str] = Field(default_factory=list, alias="preferredVmSeries")
    team_devops_maturity: Literal["none", "basic", "advanced"] = Field(
        default="basic",
        alias="teamDevopsMaturity",
    )
    notes: str = ""

