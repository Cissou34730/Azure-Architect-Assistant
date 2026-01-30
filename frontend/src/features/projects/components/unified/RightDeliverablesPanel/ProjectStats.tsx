import { Target, Activity, FileCheck } from "lucide-react";

interface StatItemProps {
  readonly label: string;
  readonly value: string | number;
  readonly icon: React.ReactNode;
}

function StatItem({ label, value, icon }: StatItemProps) {
  return (
    <div className="flex flex-col items-center p-2 rounded-lg bg-gray-50/50 border border-gray-100">
      <div className="p-1 rounded-full bg-white text-blue-600 mb-1 shadow-sm">
        {icon}
      </div>
      <span className="text-[10px] text-gray-400 uppercase tracking-tight">{label}</span>
      <span className="text-sm font-semibold text-gray-900">{value}</span>
    </div>
  );
}

interface ProjectStatsProps {
  readonly adrCount: number;
  readonly findingCount: number;
  readonly requirementCount: number;
}

export function ProjectStats({ adrCount, findingCount, requirementCount }: ProjectStatsProps) {
  return (
    <div className="grid grid-cols-3 gap-2 py-4 border-b border-gray-100">
      <StatItem label="ADRs" value={adrCount} icon={<Target className="h-3 w-3" />} />
      <StatItem label="Gaps" value={findingCount} icon={<Activity className="h-3 w-3" />} />
      <StatItem label="Reqs" value={requirementCount} icon={<FileCheck className="h-3 w-3" />} />
    </div>
  );
}
