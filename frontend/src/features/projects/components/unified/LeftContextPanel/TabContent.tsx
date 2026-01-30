import { RequirementsTab } from "./RequirementsTab";
import { AssumptionsTab } from "./AssumptionsTab";
import { QuestionsTab } from "./QuestionsTab";
import { DocumentsTab } from "./DocumentsTab";
import { type TabType } from "./TabHeader";
import { type Requirement, type Assumption, type ClarificationQuestion, type ReferenceDocument } from "../../../../../types/api";

interface TabContentProps {
  readonly activeTab: TabType;
  readonly requirements: readonly Requirement[];
  readonly assumptions: readonly Assumption[];
  readonly questions: readonly ClarificationQuestion[];
  readonly documents: readonly ReferenceDocument[];
}

export function TabContent({
  activeTab,
  requirements,
  assumptions,
  questions,
  documents,
}: TabContentProps) {
  switch (activeTab) {
    case "requirements":
      return <RequirementsTab requirements={requirements} />;
    case "assumptions":
      return <AssumptionsTab assumptions={assumptions} />;
    case "questions":
      return <QuestionsTab questions={questions} />;
    case "documents":
      return <DocumentsTab documents={documents} />;
    default:
      return null;
  }
}
