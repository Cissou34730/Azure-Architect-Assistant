import { Upload, Zap, FileText, Download } from "lucide-react";
import { Button } from "../../../components/common/Button";

interface ProjectHeaderActionsProps {
  onUploadClick?: () => void;
  onGenerateClick?: () => void;
  onAdrClick?: () => void;
  onExportClick?: () => void;
  exportDisabled?: boolean;
}

export function ProjectHeaderActions({
  onUploadClick,
  onGenerateClick,
  onAdrClick,
  onExportClick,
  exportDisabled = false,
}: ProjectHeaderActionsProps) {
  return (
    <div className="ui-header-actions">
      {onUploadClick !== undefined && (
        <Button
          onClick={onUploadClick}
          variant="secondary"
          size="sm"
          title="Upload documents (⌘U)"
        >
          <Upload className="h-4 w-4" />
          <span className="label">Upload</span>
        </Button>
      )}

      {onGenerateClick !== undefined && (
        <Button
          onClick={onGenerateClick}
          variant="primary"
          size="sm"
          title="Generate analysis (⌘G)"
        >
          <Zap className="h-4 w-4" />
          <span className="label">Generate Analysis</span>
        </Button>
      )}

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
