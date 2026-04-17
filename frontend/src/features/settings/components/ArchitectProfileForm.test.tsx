import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ArchitectProfileForm } from "./ArchitectProfileForm";
import { settingsApi } from "../api/settingsService";

vi.mock("../api/settingsService", () => ({
  settingsApi: {
    fetchArchitectProfile: vi.fn(),
    updateArchitectProfile: vi.fn(),
  },
}));

describe("ArchitectProfileForm", () => {
  it("loads and saves the architect profile", async () => {
    const fetchArchitectProfile = vi.mocked(settingsApi.fetchArchitectProfile);
    const updateArchitectProfile = vi.mocked(settingsApi.updateArchitectProfile);

    fetchArchitectProfile.mockResolvedValue({
      profile: {
        defaultRegionPrimary: "eastus",
        defaultRegionSecondary: null,
        defaultIacFlavor: "bicep",
        complianceBaseline: [],
        monthlyCostCeiling: null,
        preferredVmSeries: [],
        teamDevopsMaturity: "basic",
        notes: "",
      },
      updatedAt: null,
    });
    updateArchitectProfile.mockResolvedValue({
      profile: {
        defaultRegionPrimary: "westeurope",
        defaultRegionSecondary: null,
        defaultIacFlavor: "terraform",
        complianceBaseline: ["GDPR", "SOC2"],
        monthlyCostCeiling: 5000,
        preferredVmSeries: ["D", "E"],
        teamDevopsMaturity: "advanced",
        notes: "Prefer managed services first.",
      },
      updatedAt: "2026-04-17T10:00:00Z",
    });

    render(<ArchitectProfileForm onClose={() => {}} />);

    const primaryRegion = await screen.findByLabelText(/primary region/i);
    await userEvent.clear(primaryRegion);
    await userEvent.type(primaryRegion, "westeurope");
    await userEvent.selectOptions(screen.getByLabelText(/iac flavor/i), "terraform");
    await userEvent.type(screen.getByLabelText(/compliance baseline/i), "GDPR, SOC2");
    await userEvent.type(screen.getByLabelText(/monthly cost ceiling/i), "5000");
    await userEvent.type(screen.getByLabelText(/preferred vm series/i), "D, E");
    await userEvent.selectOptions(screen.getByLabelText(/devops maturity/i), "advanced");
    await userEvent.type(screen.getByLabelText(/^notes$/i), "Prefer managed services first.");

    await userEvent.click(screen.getByRole("button", { name: /save profile/i }));

    await waitFor(() => {
      expect(updateArchitectProfile).toHaveBeenCalledWith({
        defaultRegionPrimary: "westeurope",
        defaultRegionSecondary: null,
        defaultIacFlavor: "terraform",
        complianceBaseline: ["GDPR", "SOC2"],
        monthlyCostCeiling: 5000,
        preferredVmSeries: ["D", "E"],
        teamDevopsMaturity: "advanced",
        notes: "Prefer managed services first.",
      });
    });
  });
});
