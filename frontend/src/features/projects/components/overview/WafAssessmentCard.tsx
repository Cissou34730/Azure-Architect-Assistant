import { Card, CardHeader, CardTitle, CardContent, Badge } from "../../../../components/common";
import { Shield, Zap, DollarSign, Settings, Gauge } from "lucide-react";

interface Finding {
  readonly id?: string;
  readonly title?: string;
  readonly severity?: string;
  readonly wafPillar?: string;
}

interface WafAssessmentCardProps {
  readonly findings: readonly Finding[];
}

interface SeverityCounts {
  readonly critical: number;
  readonly high: number;
  readonly medium: number;
  readonly low: number;
}

const PILLARS = [
  {
    key: "reliability",
    label: "Reliability",
    icon: Shield,
    color: "text-blue-600",
  },
  { key: "security", label: "Security", icon: Shield, color: "text-red-600" },
  { key: "cost", label: "Cost", icon: DollarSign, color: "text-green-600" },
  {
    key: "operationalexcellence",
    label: "Operations",
    icon: Settings,
    color: "text-purple-600",
  },
  {
    key: "performanceefficiency",
    label: "Performance",
    icon: Zap,
    color: "text-amber-600",
  },
];

interface PillarListProps {
  readonly findingsByPillar: Record<string, Finding[]>;
}

function PillarList({ findingsByPillar }: PillarListProps) {
  return (
    <div className="pt-4 border-t border-gray-200 space-y-3">
      {PILLARS.map((pillar) => {
        const pillarKey = pillar.key;
        const pillarFindings = findingsByPillar[pillarKey] ?? [];
        // eslint-disable-next-line @typescript-eslint/naming-convention
        const IconComp = pillar.icon;

        return (
          <div key={pillarKey} className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <IconComp className={`h-4 w-4 ${pillar.color}`} />
              <span className="text-sm font-medium text-gray-700">
                {pillar.label}
              </span>
            </div>
            <Badge
              variant={pillarFindings.length === 0 ? "success" : "warning"}
              size="sm"
            >
              {pillarFindings.length === 0 ? "✓" : `${pillarFindings.length} issues`}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}

interface SeverityBadgesProps {
  readonly counts: SeverityCounts;
}

function SeverityBadges({ counts }: SeverityBadgesProps) {
  return (
    <div className="pt-4 border-t border-gray-200">
      <div className="flex flex-wrap gap-2 justify-center">
        {counts.critical > 0 && (
          <Badge variant="error" size="sm">
            {counts.critical} Critical
          </Badge>
        )}
        {counts.high > 0 && (
          <Badge variant="warning" size="sm">
            {counts.high} High
          </Badge>
        )}
        {counts.medium > 0 && (
          <Badge variant="info" size="sm">
            {counts.medium} Medium
          </Badge>
        )}
        {counts.low > 0 && (
          <Badge variant="default" size="sm">
            {counts.low} Low
          </Badge>
        )}
      </div>
    </div>
  );
}

function useWafAssessmentData(findings: readonly Finding[]) {
  const findingsByPillar: Record<string, Finding[]> = {};
  const severityCounts = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };

  for (const finding of findings) {
    const rawPillar = finding.wafPillar ?? "";
    const pillarName = rawPillar.toLowerCase().replace(/[^a-z]/g, "");
    
    findingsByPillar[pillarName] ??= [];
    findingsByPillar[pillarName].push(finding);

    const rawSeverity = finding.severity ?? "medium";
    const severityName = rawSeverity.toLowerCase();
    if (severityName === "critical") severityCounts.critical += 1;
    else if (severityName === "high") severityCounts.high += 1;
    else if (severityName === "medium") severityCounts.medium += 1;
    else if (severityName === "low") severityCounts.low += 1;
  }

  return { findingsByPillar, severityCounts };
}

export function WafAssessmentCard({ findings }: WafAssessmentCardProps) {
  const { findingsByPillar, severityCounts } = useWafAssessmentData(findings);

  const totalFindings = findings.length;
  const criticalOrHigh = severityCounts.critical + severityCounts.high;

  return (
    <Card>
      <CardHeader>
        <CardTitle>WAF Assessment</CardTitle>
      </CardHeader>
      <CardContent>
        {totalFindings === 0 ? (
          <div className="text-center text-gray-500 py-8">
            <Gauge className="h-12 w-12 mx-auto mb-2 text-gray-300" />
            <p>No findings yet</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-center gap-4">
              <div className="text-center">
                <div className="text-3xl font-bold text-gray-900">
                  {totalFindings}
                </div>
                <div className="text-xs text-gray-600">Total Findings</div>
              </div>
              {criticalOrHigh > 0 && (
                <div className="text-center">
                  <div className="text-3xl font-bold text-red-600">
                    {criticalOrHigh}
                  </div>
                  <div className="text-xs text-gray-600">Critical/High</div>
                </div>
              )}
            </div>

            <PillarList findingsByPillar={findingsByPillar} />

            <SeverityBadges counts={severityCounts} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
