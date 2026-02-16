import { FileText, Download } from "lucide-react";
import { Button } from "../../../components/common/Button";

interface ProjectHeaderActionsProps {
  onAdrClick?: () => void;
  onExportClick?: () => void;
  exportDisabled?: boolean;
}

export function ProjectHeaderActions({
  onAdrClick,
  onExportClick,
  exportDisabled = false,
}: ProjectHeaderActionsProps) {
  return (
    <div className="ui-header-actions">
      {onAdrClick !== undefined && (
        <Button
          onClick={onAdrClick}
          variant="secondary"
          size="sm"
          title="Create ADR"
        >
          <FileText className="h-4 w-4" />
          <span className="label">ADR</span>
        </Button>
      )}

      {onExportClick !== undefined && (
        <Button
          onClick={onExportClick}
          disabled={exportDisabled}
          variant="secondary"
          size="sm"
          title={exportDisabled ? "Export (coming soon)" : "Export"}
        >
          <Download className="h-4 w-4" />
          <span className="label">Export</span>
        </Button>
      )}
    </div>
  );
}
