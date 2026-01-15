import { ProjectState } from "../../../../types/api";
import { Section } from "./StateShared";

interface DataComplianceSectionProps {
  readonly dataCompliance: ProjectState["dataCompliance"];
}

export function DataComplianceSection({
  dataCompliance,
}: DataComplianceSectionProps) {
  if (dataCompliance === undefined) return null;

  return (
    <Section title="Data & Compliance">
      <p>
        <strong>Data Types:</strong> {dataCompliance.dataTypes.join(", ")}
      </p>
      <p>
        <strong>Compliance:</strong>{" "}
        {dataCompliance.complianceRequirements.join(", ")}
      </p>
      <p>
        <strong>Data Residency:</strong> {dataCompliance.dataResidency}
      </p>
    </Section>
  );
}
