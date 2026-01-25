import { useNavigate } from "react-router-dom";
import { Upload, Sparkles, FileText, Download, Network } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "../../../../components/common";

interface QuickActionsProps {
  projectId: string;
  onExportProposal?: () => void;
}

export function QuickActions({ projectId, onExportProposal }: QuickActionsProps) {
  const navigate = useNavigate();

  const actions = [
    {
      icon: Upload,
      label: "Analyze Documents",
      description: "Upload and analyze project docs",
      color: "text-blue-600",
      bgColor: "bg-blue-50",
      onClick: () => navigate(`/projects/${projectId}/workspace`),
    },
    {
      icon: Sparkles,
      label: "Generate Candidate",
      description: "Create architecture candidate",
      color: "text-purple-600",
      bgColor: "bg-purple-50",
      onClick: () => navigate(`/projects/${projectId}/workspace?prompt=generate-candidate`),
    },
    {
      icon: FileText,
      label: "Create ADR",
      description: "Document a decision",
      color: "text-green-600",
      bgColor: "bg-green-50",
      onClick: () => navigate(`/projects/${projectId}/workspace?prompt=create-adr`),
    },
    {
      icon: Network,
      label: "View Diagrams",
      description: "See architecture diagrams",
      color: "text-cyan-600",
      bgColor: "bg-cyan-50",
      onClick: () => navigate(`/projects/${projectId}/deliverables?tab=diagrams`),
    },
    {
      icon: Download,
      label: "Export Proposal",
      description: "Generate full proposal doc",
      color: "text-amber-600",
      bgColor: "bg-amber-50",
      onClick: onExportProposal || (() => alert("Export feature coming soon")),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.label}
                onClick={action.onClick}
                className="flex items-center gap-3 p-3 rounded-lg border border-gray-200 hover:border-gray-300 hover:shadow-sm transition-all text-left"
              >
                <div className={`rounded-lg p-2 ${action.bgColor}`}>
                  <Icon className={`h-5 w-5 ${action.color}`} />
                </div>
                <div className="flex-1">
                  <div className="font-medium text-gray-900 text-sm">
                    {action.label}
                  </div>
                  <div className="text-xs text-gray-600">
                    {action.description}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
