import { ProjectState } from "../../../types/agent";
import { StateSection, StateField } from "./StateShared";

interface NfrSectionProps {
  readonly nfrs: NonNullable<ProjectState["nfrs"]>;
}

export function NfrSection({ nfrs }: NfrSectionProps) {
  return (
    <StateSection icon="🎯" title="Non-Functional Requirements">
      {nfrs.availability !== undefined && nfrs.availability !== "" && (
        <StateField label="Availability">
          <p className="text-secondary mt-1">{nfrs.availability}</p>
        </StateField>
      )}
      
      {nfrs.security !== undefined && nfrs.security !== "" && (
        <StateField label="Security">
          <p className="text-secondary mt-1">{nfrs.security}</p>
        </StateField>
      )}
      
      {nfrs.performance !== undefined && nfrs.performance !== "" && (
        <StateField label="Performance">
          <p className="text-secondary mt-1">{nfrs.performance}</p>
        </StateField>
      )}
      
      {nfrs.costConstraints !== undefined && nfrs.costConstraints !== "" && (
        <StateField label="Cost">
          <p className="text-secondary mt-1">{nfrs.costConstraints}</p>
        </StateField>
      )}
    </StateSection>
  );
}

